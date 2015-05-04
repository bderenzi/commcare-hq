from functools import wraps
from django.http import Http404
from .models import SQLLocation
from corehq.apps.domain.decorators import (login_and_domain_required,
                                           domain_admin_required)


def locations_access_required(view_fn):
    """
    Decorator controlling domain-level access to locations.
    Mostly a placeholder, soon this will also check for standard plan
    """
    return login_and_domain_required(view_fn)


def is_locations_admin(view_fn):
    """
    Decorator controlling write access to locations.
    """
    return locations_access_required(domain_admin_required(view_fn))


def user_can_edit_location(user, location):
    user_loc = user.get_location(location.domain).sql_location
    return user_loc is None or user_loc.is_direct_ancestor_of(location)


def can_edit_location(view_fn):
    """
    Decorator controlling a user's access to a specific location.
    The decorated function must be passed a loc_id arg (eg: from urls.py)
    """
    @wraps(view_fn)
    def _inner(request, domain, loc_id, *args, **kwargs):
        try:
            # pass to view?
            location = SQLLocation.objects.get(location_id=loc_id)
        except SQLLocation.DoesNotExist:
            raise Http404()
        else:
            if user_can_edit_location(request.couch_user, location):
                return view_fn(request, domain, loc_id, *args, **kwargs)
        raise Http404()
    return locations_access_required(_inner)
