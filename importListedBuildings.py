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

class DbOld(object):
	def __init__(self):
		self.conn = sqlite3.connect('auxgis.db')
		self.cursor = self.conn.cursor()
		self.source = "ListedBuildings"

	def __del__(self):
		self.conn.commit()

	def HandlePlacemark(self, placeName, shape, extendedData):
		#print placeName, shape
		#print extendedData
		
		#Remove unnecessary info
		del extendedData["Easting"]
		del extendedData["Northing"]
		del extendedData["NGR"]

		repPoint = None
		if shape is not None:
			tmp = shape.representative_point()
			repPoint = tuple(tmp.coords[0])

		extendedData["lat"] = repPoint[1]
		extendedData["lon"] = repPoint[0]
		extendedJson = json.dumps(extendedData)

		sql = "INSERT INTO data (name, source, lat, lon, extended) VALUES (?,?,?,?,?);"
		self.cursor.execute(sql, (placeName, self.source, repPoint[1], repPoint[0], extendedJson))

		lid = self.cursor.lastrowid
		sql = "INSERT INTO pos (id, minLat, maxLat, minLon, maxLon) VALUES (?,?,?,?,?);"
		self.cursor.execute(sql, (lid, repPoint[1], repPoint[1], repPoint[0], repPoint[0]))

class Db(object):
	def __init__(self):
		self.importTime = datetime.datetime.now()
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
		extendedDataFiltered["CaptureSca"] = extendedData["CaptureSca"]
		extendedDataFiltered["ListDate"] = extendedData["ListDate"]
		extendedDataFiltered["LegacyUID"] = extendedData["LegacyUID"]
		if "AmendDate" in extendedData:
			extendedDataFiltered["AmendDate"] = extendedData["AmendDate"]	

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


