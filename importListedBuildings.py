#ogr2ogr -f KML output.kml input.shp

#0 kml
#1 Document
#2 Folder
#3 name
#3 Placemark
#4 name
#4 ExtendedData
#5 SchemaData
#6 SimpleData

import sqlite3, bz2, json, importScheduledMonuments, os
import xml.parsers.expat

from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auxgis2.settings")
import django
django.setup()
from records.models import *
import django.core.exceptions as dex
import datetime
from django.contrib.auth.models import User
from django.db import IntegrityError
import shapely.wkt as wkt

def TitleCase(txt):
	txtSpl = txt.split(" ")
	txtSpl = [tmp.capitalize() for tmp in txtSpl]
	return " ".join(txtSpl)

class Db(object):
	def __init__(self):
		self.importTime = datetime.datetime(2013, 10, 30, tzinfo=importScheduledMonuments.UTC())
		self.importUser = User.objects.get(username='tim')
		try:
			self.ds = DatasetSeries.objects.get(name="Listed Buildings (England)")
		except dex.ObjectDoesNotExist:
			self.ds = DatasetSeries(name="Listed Buildings (England)",
				description="",
				license="")
			self.ds.save()

		try:
			oldSnapshot = DatasetSnapshot.objects.get(name="20131030")
			oldSnapshot.delete()
		except dex.ObjectDoesNotExist:
			pass

		self.snapshot = DatasetSnapshot(name="20131030", description="", datasetSeries=self.ds)
		self.snapshot.save()

	def __del__(self):
		pass

	def HandlePlacemark(self, placeName, shape, extendedData):
		#print placeName, shape
		#print extendedData

		externalId = extendedData["ListEntry"]
		del extendedData["ListEntry"]

		extendedDataFiltered = {} 
		extendedDataFiltered["Grade"] = extendedData["Grade"]
		if "CaptureSca" in extendedData:
			extendedDataFiltered["CaptureSca"] = extendedData["CaptureSca"]
		if "ListDate" in extendedData:
			extendedDataFiltered["ListDate"] = extendedData["ListDate"]
		if "LegacyUID" in extendedData:
			extendedDataFiltered["LegacyUID"] = extendedData["LegacyUID"]
		if "AmendDate" in extendedData:
			extendedDataFiltered["AmendDate"] = extendedData["AmendDate"]
		if placeName is None:
			placeName = "Empty"

		rec = DatasetRecord(externalId = externalId, 
			dataJson = json.dumps(extendedDataFiltered),
			datasetSnapshot = self.snapshot)
		rec.save()

		rp = shape.representative_point()

		try:
			rec2 = Record.objects.get(externalId = externalId)
		except dex.ObjectDoesNotExist:
			pos = GEOSGeometry(str(rp), srid=4326)
			rec2 = Record(currentName = placeName, 
				currentPosition = pos,
				datasetSeries = self.ds,
				externalId = externalId)
			rec2.save()

			newAnnot = RecordNameEdit(record = rec2,
				data = placeName, 
				timestamp = self.importTime,
				user = self.importUser)
			newAnnot.save()

			newAnnot = RecordPositionEdit(record = rec2,
				data = pos, 
				timestamp = self.importTime,
				user = self.importUser)
			newAnnot.save()


if __name__=="__main__":
	

	inFi = bz2.BZ2File("LB.kml.bz2", "r")
	db = Db()

	ep = importScheduledMonuments.ParseKml()
	ep.db = db
	with transaction.atomic():
		ep.ParseFile(inFi)

	ep.db = None
	del db


