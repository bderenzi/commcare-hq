from __future__ import absolute_import
from __future__ import unicode_literals
from collections import namedtuple
from tastypie.models import ApiKey
from corehq.apps.accounting.models import BillingAccount, DefaultProductPlan, SoftwarePlanEdition, Subscription
from corehq.apps.domain.models import Domain
from corehq.apps.users.models import WebUser
from corehq.apps.zapier.consts import CASE_TYPE_REPEATER_CLASS_MAP
from corehq.motech.repeaters.models import FormRepeater, RepeatRecord


ZapierDomainConfig = namedtuple('ZapierDomainConfig', 'domain web_user api_key')


def bootrap_domain_for_zapier(domain_name):
    domain_object = Domain.get_or_create_with_name(domain_name, is_active=True)

    account = BillingAccount.get_or_create_account_by_domain(domain_name, created_by="automated-test")[0]
    plan = DefaultProductPlan.get_default_plan_version(edition=SoftwarePlanEdition.STANDARD)
    subscription = Subscription.new_domain_subscription(account, domain_name, plan)
    subscription.is_active = True
    subscription.save()

    web_user = WebUser.create(domain_name, 'test', '******')
    api_key_object, _ = ApiKey.objects.get_or_create(user=web_user.get_django_user())
    return ZapierDomainConfig(domain_object, web_user, api_key_object.key)


def cleanup_repeaters_for_domain(domain):
    for repeater in FormRepeater.by_domain(domain):
            repeater.delete()
    for case_repeater_class in CASE_TYPE_REPEATER_CLASS_MAP.values():
        for repeater in case_repeater_class.by_domain(domain):
            repeater.delete()


def cleanup_repeat_records_for_domain(domain):
    for repeat_record in RepeatRecord.all(domain=domain):
        repeat_record.delete()
