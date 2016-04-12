from casexml.apps.case.models import CommCareCase
from corehq.apps.change_feed import data_sources
from corehq.apps.change_feed.connection import get_kafka_client_or_none
from corehq.apps.change_feed.document_types import get_doc_meta_object_from_document, \
    change_meta_from_doc_meta_and_document
from corehq.apps.change_feed.exceptions import MissingMetaInformationError
from corehq.apps.change_feed.producer import ChangeProducer
from corehq.apps.change_feed.topics import get_topic
from corehq.apps.domain.models import Domain
from corehq.apps.users.models import CommCareUser
from corehq.util.couchdb_management import couch_config
from pillowtop.checkpoints.manager import PillowCheckpoint, PillowCheckpointEventHandler
from pillowtop.couchdb import CachedCouchDB
from pillowtop.feed.couch import CouchChangeFeed
from pillowtop.listener import PythonPillow
from pillowtop.pillow.interface import ConstructedPillow
from pillowtop.processors import PillowProcessor


class KafkaProcessor(PillowProcessor):
    """
    Processor that pushes changes to Kafka
    """
    def __init__(self, kafka, data_source_type, data_source_name):
        self._kafka = kafka
        self._producer = ChangeProducer(self._kafka)
        self._data_source_type = data_source_type
        self._data_source_name = data_source_name

    def process_change(self, pillow_instance, change, do_set_checkpoint=False):
        try:
            doc_meta = get_doc_meta_object_from_document(change.document)
            change_meta = change_meta_from_doc_meta_and_document(
                doc_meta=doc_meta,
                document=change.document,
                data_source_type=self._data_source_type,
                data_source_name=self._data_source_name,
                doc_id=change.id,
            )
        except MissingMetaInformationError:
            pass
        else:
            assert not change.deleted
            self._producer.send_change(get_topic(doc_meta), change_meta)


class ChangeFeedPillow(PythonPillow):
    """
    This pillow takes changes from a CouchDB and republishes them to Kafka.
    It is used as an intermediary to convert couch-based change listeners
    to kafka-based ones.
    """

    def __init__(self, pillow_id, couch_db, kafka, checkpoint):
        super(ChangeFeedPillow, self).__init__(couch_db=couch_db, checkpoint=checkpoint, chunk_size=10)
        self._pillow_id = pillow_id
        self._processor = KafkaProcessor(
            kafka, data_source_type=data_sources.COUCH, data_source_name=self.get_db_name()
        )

    @property
    def pillow_id(self):
        return self._pillow_id

    def get_db_name(self):
        return self.get_couch_db().dbname

    def process_change(self, change, is_retry_attempt=False):
        self._processor.process_change(self, change)


def get_default_couch_db_change_feed_pillow(pillow_id):
    default_couch_db = CachedCouchDB(CommCareCase.get_db().uri, readonly=False)
    kafka_client = get_kafka_client_or_none()
    return ChangeFeedPillow(
        pillow_id=pillow_id,
        couch_db=default_couch_db,
        kafka=kafka_client,
        checkpoint=PillowCheckpoint('default-couch-change-feed')
    )


def get_user_groups_db_kafka_pillow(pillow_id):
    # note: this is temporarily using ConstructedPillow as a test. If it is successful we should
    # flip the main one over as well
    return _get_change_feed_pillow_for_db(pillow_id, couch_config.get_db_for_class(CommCareUser))


def get_domain_db_kafka_pillow(pillow_id):
    return _get_change_feed_pillow_for_db(pillow_id, couch_config.get_db_for_class(Domain))


def _get_change_feed_pillow_for_db(pillow_id, couch_db):
    kafka_client = get_kafka_client_or_none()
    processor = KafkaProcessor(
        kafka_client, data_source_type=data_sources.COUCH, data_source_name=couch_db.dbname
    )
    checkpoint = PillowCheckpoint(pillow_id)
    return ConstructedPillow(
        name=pillow_id,
        document_store=None,  # because we're using include_docs we can be explicit about not using this
        checkpoint=checkpoint,
        change_feed=CouchChangeFeed(couch_db, include_docs=True),
        processor=processor,
        change_processed_event_handler=PillowCheckpointEventHandler(
            checkpoint=checkpoint, checkpoint_frequency=100,
        ),
    )
