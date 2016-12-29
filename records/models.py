from __future__ import unicode_literals

from django.contrib.gis.db import models

class DatasetSeries(models.Model):
	name = models.CharField("name", max_length=200)
	description = models.TextField("description")
	license = models.CharField("license", max_length=200)

    def __str__(self):
        return self.name

class Record(models.Model):
	currentName = models.TextField("current_name")
	currentPosition = models.PointField("current_position")
	datasetSeries = models.ForeignKey(DatasetSeries, on_delete=models.CASCADE)

    def __str__(self):
        return self.currentName

