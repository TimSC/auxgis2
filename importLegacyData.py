
import os, sqlite3, json, importScheduledMonuments, datetime
from django.db import transaction
from django.contrib.auth.models import User
from django.db import IntegrityError
from records.models import *
import django.core.exceptions as dex

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auxgis2.settings")
import django
django.setup()

def GetOrCreateAttr(name, attribType, datasetSeries):
	try:
		attr = AttributeType.objects.get(name=name, attribType=attribType, datasetSeries=datasetSeries)
	except dex.ObjectDoesNotExist:
		attr = AttributeType(name=name, attribType=attribType, datasetSeries=datasetSeries)
		attr.save()
	return attr

class Db(object):
	def __init__(self):
		self.importUser = User.objects.get(username='tim')
		
		self.dsLB = DatasetSeries.objects.get(name="Listed Buildings (England)")
		self.dsSM = DatasetSeries.objects.get(name="Scheduled Monuments (England)")

		self.smDescription = GetOrCreateAttr("description", "text", self.dsSM)
		self.smWikipedia = GetOrCreateAttr("wikipedia", "text", self.dsSM)
		self.smFlickr = GetOrCreateAttr("flickr", "text", self.dsSM)
		self.smFields = {"description": self.smDescription, "wikipedia": self.smWikipedia, "flickr": self.smFlickr}

		self.lbDescription = GetOrCreateAttr("description", "text", self.dsLB)
		self.lbWikipedia = GetOrCreateAttr("wikipedia", "text", self.dsLB)
		self.lbFlickr = GetOrCreateAttr("flickr", "text", self.dsLB)
		self.lbFields = {"description": self.lbDescription, "wikipedia": self.lbWikipedia, "flickr": self.lbFlickr}

	def StoreEdit(self, listEntry, dataset, ts, key, value):
		#print listEntry, key, value
		ds = None
		fields = None
		if dataset == "ListedBuildings":
			ds = self.dsLB
			fields = self.lbFields
		if dataset == "ScheduledMonuments":
			ds = self.dsSM
			fields = self.smFields

		rec = Record.objects.get(datasetSeries = ds, externalId = listEntry)

		if key == "name":
			try:
				nameRec = RecordNameEdit.objects.get(record=rec, data=value, timestamp = ts)
			except dex.ObjectDoesNotExist:
				nameRec = RecordNameEdit(record=rec, data=value, timestamp = ts, user = self.importUser)
				nameRec.save()

			nameRecs = RecordNameEdit.objects.filter(record=rec).order_by("timestamp")
			latest = nameRecs[len(nameRecs)-1]
			rec.currentName = latest.data
			rec.save()
			print "update name in rec", rec.id
		
		if key in fields:
			try:
				nameRec = RecordTextAttribute.objects.get(record = rec, attrib = fields[key], data = value, timestamp = ts)
			except dex.ObjectDoesNotExist:
				nameRec = RecordTextAttribute(record = rec, attrib = fields[key], data = value, timestamp = ts, user = self.importUser)
				nameRec.save()
			print "update",key,"in rec", rec.id
			
def ImportLegacy():
	db = Db()

	conn = sqlite3.connect('auxgis.db')
	c = conn.cursor()
	result = c.execute('SELECT * FROM data')

	for row in result:

		rowId = row[0]
		currentName = row[1]
		dataset = row[2]
		lat = row[3]
		lon = row[4]
		extended = json.loads(row[5])
		if row[6] is not None:
			edits = json.loads(row[6])

			listEntry = int(extended["ListEntry"])
			print rowId, dataset, listEntry

			for (editUser, editTime), editData in edits:
				ts = datetime.datetime.fromtimestamp(editTime, importScheduledMonuments.UTC())
				for key in editData:
					#print key, ts, editData[key]
					db.StoreEdit(listEntry, dataset, ts, key, editData[key])
if __name__=="__main__":
	with transaction.atomic():
		ImportLegacy()

