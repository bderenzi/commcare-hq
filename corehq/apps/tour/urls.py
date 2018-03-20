from __future__ import absolute_import
from __future__ import unicode_literals
from django.conf.urls import url
from corehq.apps.tour.views import EndTourView

urlpatterns = [
    url(r'^end/(?P<tour_slug>\w+)/$', EndTourView.as_view(), name=EndTourView.urlname),
]
