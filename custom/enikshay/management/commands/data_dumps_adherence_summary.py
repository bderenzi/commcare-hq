from __future__ import absolute_import
from __future__ import print_function

from corehq.apps.es import queries

from custom.enikshay.case_utils import (
    CASE_TYPE_EPISODE,
    get_person_case_from_episode,
)
from custom.enikshay.const import (
    ENROLLED_IN_PRIVATE,
)
from custom.enikshay.management.commands.base_data_dump import BaseDataDump

DOMAIN = "enikshay"


class Command(BaseDataDump):
    """
    14. Adherence Summary
    https://docs.google.com/spreadsheets/d/1OPp0oFlizDnIyrn7Eiv11vUp8IBmc73hES7qqT-mKKA/edit#gid=1471366670
    """
    TASK_NAME = "14_adherence_summary"
    INPUT_FILE_NAME = "data_dumps_adherence_summary.csv"

    def __init__(self, *args, **kwargs):
        super(Command, self).__init__(*args, **kwargs)
        self.case_type = CASE_TYPE_EPISODE

    def get_case_ids_query(self, case_type):
        """
        All open and closed episode cases whose host/host = a person case (open or closed)
        with person.dataset = 'real' and self.enrolled_in_private != 'true' and
        (self.episode_type = 'confirmed_drtb' OR self.episode_type = 'confirmed_tb')
        """
        return (self.case_search_instance
                .case_type(case_type)
                .case_property_query(ENROLLED_IN_PRIVATE, 'true', clause=queries.MUST_NOT)
                .case_property_filter("episode_type", ["confirmed_tb", "confirmed_drtb"])
                )

    def include_case_in_dump(self, episode):
        person = self.get_person(episode)
        return (
            person and
            person.get_case_property('dataset') == 'real' and
            person.get_case_property(ENROLLED_IN_PRIVATE) != 'true'
        )

    def get_person(self, episode):
        if 'person' not in self.context:
            self.context['person'] = get_person_case_from_episode(DOMAIN, episode.case_id)
        return self.context['person']

    def get_case_reference_value(self, case_reference, episode, calculation):
        if case_reference == 'person':
            return self.get_person(episode).get_case_property(calculation)
        return Exception("unknown case reference %s" % case_reference)
