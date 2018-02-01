from django.http import JsonResponse, Http404, HttpResponseForbidden

from corehq.apps.app_manager.dbaccessors import get_latest_released_app, get_app
from corehq.apps.domain.decorators import api_key_auth
from corehq.apps.linked_domain.decorators import require_linked_domain
from corehq.apps.linked_domain.local_accessors import get_toggles_previews, get_custom_data_models
from corehq.apps.linked_domain.util import _clean_json, convert_app_for_remote_linking
from corehq.apps.users.models import UserRole


@api_key_auth
@require_linked_domain
def toggles_and_previews(request, domain):
    return JsonResponse(get_toggles_previews(domain))


@api_key_auth
@require_linked_domain
def custom_data_models(request, domain):
    return JsonResponse(get_custom_data_models(domain))


@api_key_auth
@require_linked_domain
def user_roles(request, domain):
    def _to_json(role):
        return _clean_json(role.to_json())

    roles = map(_to_json, UserRole.by_domain(domain))
    return JsonResponse({'user_roles': roles})


@api_key_auth
# @require_linked_domain  # need to migrate whitelist before we can put this here
def get_latest_released_app_source(request, domain, app_id):
    master_app = get_app(None, app_id)
    if master_app.domain != domain:
        raise Http404

    requester = request.GET.get('requester')
    if requester not in master_app.linked_whitelist:
        return HttpResponseForbidden()

    latest_master_build = get_latest_released_app(domain, app_id)
    if not latest_master_build:
        raise Http404

    return JsonResponse(convert_app_for_remote_linking(latest_master_build))
