from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^record/(?P<record_id>[0-9]+)/$', views.record, name='record'),
	url(r'^$', views.index, name='index'),
]
