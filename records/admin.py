from django.contrib import admin

from .models import *

admin.site.register(DatasetSeries)
admin.site.register(DatasetSnapshot)
admin.site.register(AttributeType)
admin.site.register(RecordTextAttribute)
admin.site.register(Record)
admin.site.register(DatasetRecord)

