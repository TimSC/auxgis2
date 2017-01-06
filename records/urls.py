from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
	#url(r'^login$', views.login, name='login'),
	url(r'^login/$', auth_views.login, name="login"),
	url(r'^logout/$', views.logout_view, name="logout"),
	url(r'^password_reset/$', auth_views.password_reset, name="password_reset"),
	url(r'^password_reset_done/$', auth_views.password_reset_done, name="password_reset_done"),
	url(r'^register/$', views.register, name="register"),
	url(r'^record/(?P<record_id>[0-9]+)/$', views.record, name='record'),
	url(r'^record/(?P<record_id>[0-9]+)/snapshot/(?P<snapshot_id>[0-9]+)$', views.original_record, name='original_record'),
	url(r'^record/(?P<record_id>[0-9]+)/edit$', views.record_edit, name='record_edit'),
	url(r'^record/(?P<record_id>[0-9]+)/history$', views.record_history, name='record_history'),
	url(r'^query', views.records_query, name='records_query'),
	url(r'^dataset_series/(?P<dataset_series_id>[0-9]+)/$', views.dataset_series, name='dataset_series'),
	url(r'^recent_changes/$', views.recent_changes, name='recent_changes'),
	url(r'^dataset_series/$', views.dataset_series_list, name='dataset_series_list'),
	url(r'^$', views.index, name='index'),
]
