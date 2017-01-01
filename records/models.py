from __future__ import unicode_literals
from django.contrib.gis.db import models
from django.contrib.auth.models import User

class DatasetSeries(models.Model):
	name = models.CharField("name", max_length=200)
	description = models.TextField("description")
	license = models.CharField("license", max_length=200)

	def __str__(self):
		return "DatasetSeries "+self.name

class Record(models.Model):
	currentName = models.TextField("current_name")
	currentPosition = models.PointField("current_position")
	datasetSeries = models.ForeignKey(DatasetSeries, on_delete=models.CASCADE)
	externalId = models.CharField("license", max_length=200, default="")

	def __str__(self):
		return "Record "+self.currentName

class DatasetSnapshot(models.Model):
	name = models.CharField("name", max_length=200)
	description = models.TextField("description")
	datasetSeries = models.ForeignKey(DatasetSeries, on_delete=models.CASCADE)

	def __str__(self):
		return "DatasetSnapshot " + self.name

class DatasetRecord(models.Model):
	externalId = models.CharField("name", max_length=200, default="")
	dataJson = models.TextField("data_json")
	datasetSnapshot = models.ForeignKey(DatasetSnapshot, on_delete=models.CASCADE)

	def __str__(self):
		return "DatasetRecord "+self.externalId

class AttributeType(models.Model):
	name = models.CharField("name", max_length=200)
	attribType = models.CharField("attrib_type", max_length=200)
	datasetSeries = models.ForeignKey(DatasetSeries, on_delete=models.CASCADE)

	def __str__(self):
		return "AttributeType "+self.name

class RecordTextAttribute(models.Model):
	record = models.ForeignKey(Record, on_delete=models.CASCADE)
	attrib = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
	data = models.TextField("data")
	timestamp = models.DateTimeField('timestamp')	
	user = models.ForeignKey(User)

	def __str__(self):
		return "RecordTextAttribute "+self.record.currentName + "," + self.attrib.name


