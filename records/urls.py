from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^record/(?P<record_id>[0-9]+)/$', views.record, name='record'),
    url(r'^record/(?P<record_id>[0-9]+)/snapshot/(?P<snapshot_id>[0-9]+)$', views.original_record, name='original_record'),
    url(r'^record/(?P<record_id>[0-9]+)/edit$', views.record_edit, name='record_edit'),
    url(r'^query', views.records_query, name='records_query'),
	url(r'^$', views.index, name='index'),
]
