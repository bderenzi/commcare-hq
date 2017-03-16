from django.core.management.base import BaseCommand

from casexml.apps.case.xform import get_case_updates
from corehq.form_processor.interfaces.dbaccessors import CaseAccessors
from corehq.form_processor.interfaces.processor import FormProcessorInterface

domain = "enikshay"


class Command(BaseCommand):

    def handle(self, **options):
        to_archive = []
        episode_case_ids = CaseAccessors(domain).get_case_ids_in_domain("episode")
        for episode_case_id in episode_case_ids:
            nikshay_to_archive = []
            dots_99_to_archvie = []
            case_forms = FormProcessorInterface(domain).get_case_forms(episode_case_id)
            _system_forms_count = 0
            for form in case_forms:
                if form.username == "system":
                    _system_forms_count += 1
                    updates = get_case_updates(form)
                    update_actions = [update.get_update_action() for update in updates if update.id == episode_case_id]
                    for action in update_actions:
                        if set(action.dynamic_properties.keys()) == {"nikshay_registered", "nikshay_error"}:
                            nikshay_to_archive.append(form)
                        elif set(action.dynamic_properties.keys()) == {"dots_99_registered", "dots_99_error"}:
                            dots_99_to_archvie.append(form)

            nikshay_to_archive = nikshay_to_archive[:-1]
            dots_99_to_archvie = dots_99_to_archvie[:-1]

            print "Found {} system forms for case {}".format(_system_forms_count, episode_case_id)
            print "Can archive {}".format(len(nikshay_to_archive) + len(dots_99_to_archvie))

            to_archive.extend(nikshay_to_archive)
            to_archive.extend(dots_99_to_archvie)
