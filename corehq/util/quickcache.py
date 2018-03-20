from __future__ import absolute_import
from __future__ import unicode_literals
import warnings
from quickcache.django_quickcache import get_django_quickcache
from celery._state import get_current_task
from corehq.util.global_request import get_request

from corehq.util.soft_assert import soft_assert

quickcache_soft_assert = soft_assert(
    notify_admins=True,
    fail_if_debug=False,
    skip_frames=5,
)


def get_session_key():
    """
    returns a 7 character string that varies with the current "session" (task or request)
    """
    session = get_current_task() or get_request()
    if session:
        return hex(id(session))[2:9]
    else:
        # arbitrary 7-letter that is clearly not from a session
        return 'xxxxxxx'


quickcache = get_django_quickcache(timeout=5 * 60, memoize_timeout=10,
                                   assert_function=quickcache_soft_assert,
                                   session_function=get_session_key)


def skippable_quickcache(*args, **kwargs):
    warnings.warn(
        "skippable_quickcache is deprecated. Use quickcache with skip_arg instead.",
        DeprecationWarning
    )
    return quickcache(*args, **kwargs)


__all__ = ['quickcache', 'skippable_quickcache']
