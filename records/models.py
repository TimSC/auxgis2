from __future__ import unicode_literals
from django.contrib.gis.db import models
from django.contrib.auth.models import User

class DatasetSeries(models.Model):
	name = models.CharField("name", max_length=200)
	description = models.TextField("description")
	license = models.CharField("license", max_length=200)

	def __str__(self):
		return "DatasetSeries "+self.name

	def Xml(self):
		return u"<DatasetSeries id=\"{}\" name=\"{}\" description=\"{}\" license=\"{}\" />\n".format(
			self.id, self.name, self.description, self.license)

class Record(models.Model):
	currentName = models.TextField("current_name")
	currentPosition = models.PointField("current_position")
	datasetSeries = models.ForeignKey(DatasetSeries, on_delete=models.CASCADE)
	externalId = models.CharField("license", max_length=200, default="")

	def __str__(self):
		return "Record "+self.currentName

	def Xml(self):
		return u"<Record id=\"{}\" name=\"{}\" dataSeriesId=\"{}\" externalId=\"{}\" lat=\"{}\" lon=\"{}\" />\n".format(
			self.id, self.currentName, self.datasetSeries.id, self.externalId, self.currentPosition.y, self.currentPosition.x)

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

	def Xml(self):
		return "<AttributeType id=\"{}\" name=\"{}\" attribType=\"{}\" datasetSeriesId=\"{}\"/>\n".format(
			self.id, self.name, self.attribType, self.datasetSeries.id)

class RecordTextAttribute(models.Model):
	record = models.ForeignKey(Record, on_delete=models.CASCADE)
	attrib = models.ForeignKey(AttributeType, on_delete=models.CASCADE)
	data = models.TextField("data")
	timestamp = models.DateTimeField('timestamp')	
	user = models.ForeignKey(User)

	def __str__(self):
		return "RecordTextAttribute "+self.record.currentName + "," + self.attrib.name

	def Xml(self):
		return "<RecordTextAttribute id=\"{}\" recordId=\"{}\" attribId=\"{}\" data=\"{}\" timestamp=\"{}\" user=\"{}\" userId=\"{}\"/>\n".format(
			self.id, self.record.id, self.attrib.id, self.data, self.timestamp, self.user.username, self.user.id)

class RecordShapeEdit(models.Model):
	record = models.ForeignKey(Record, on_delete=models.CASCADE)
	data = models.GeometryCollectionField("data")
	timestamp = models.DateTimeField('timestamp')
	user = models.ForeignKey(User)

	def __str__(self):
		return "RecordTextAttribute "+self.record.currentName + "," + self.attrib.name

	def Xml(self):
		return "<RecordShapeEdit id=\"{}\" recordId=\"{}\" data=\"{}\" timestamp=\"{}\" user=\"{}\" userId=\"{}\"/>\n".format(
			self.id, self.record.id, self.data.wkt, self.timestamp, self.user.username, self.user.id)

class RecordNameEdit(models.Model):
	record = models.ForeignKey(Record, on_delete=models.CASCADE)
	data = models.TextField("data")
	timestamp = models.DateTimeField('timestamp')	
	user = models.ForeignKey(User)

	def __str__(self):
		return "RecordNameEdits "+self.data + ", name"

	def Xml(self):
		return "<RecordNameEdits id=\"{}\" recordId=\"{}\" data=\"{}\" timestamp=\"{}\" user=\"{}\" userId=\"{}\"/>\n".format(
			self.id, self.record.id, self.data, self.timestamp, self.user.username, self.user.id)

class RecordPositionEdit(models.Model):
	record = models.ForeignKey(Record, on_delete=models.CASCADE)
	data = models.PointField("data")
	timestamp = models.DateTimeField('timestamp')	
	user = models.ForeignKey(User)

	def __str__(self):
		return "RecordPositionEdit "+self.record.currentName + ", position"

	def Xml(self):
		return "<RecordPositionEdit id=\"{}\" recordId=\"{}\" lat=\"{}\" lon=\"{}\" timestamp=\"{}\" user=\"{}\" userId=\"{}\"/>\n".format(
			self.id, self.record.id, self.data.y, self.data.x, self.timestamp, self.user.username, self.user.id)

