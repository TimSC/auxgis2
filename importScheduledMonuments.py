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

import bz2, json, os
import xml.parsers.expat
from shapely.geometry import Polygon, LineString, LinearRing, Point, MultiPolygon, MultiPoint
from shapely.geometry.collection import GeometryCollection
import shapely.wkt
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
		self.importTime = datetime.datetime.now()
		self.importUser = User.objects.get(username='tim')
		try:
			self.ds = DatasetSeries.objects.get(name="Scheduled Monuments (England)")
		except dex.ObjectDoesNotExist:
			self.ds = DatasetSeries(name="Scheduled Monuments (England)",
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
		del extendedData["NGR"]
		del extendedData["Easting"]
		del extendedData["Northing"]
		del extendedData["AREA_HA"]
		rec = DatasetRecord(externalId = externalId, 
			dataJson = json.dumps(extendedData),
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

			if True: 
				#Can't do this on spatialite 
				#https://code.djangoproject.com/ticket/27672
				if not shape.is_valid:
					shape = shape.buffer(0.0)
				shape2 = GeometryCollection([shape])
				shape3 = GEOSGeometry(buffer(shape2.wkb), srid=4326)

				newAnnot = RecordShapeEdit(record = rec2,
					data = shape3, 
					timestamp = self.importTime,
					user = self.importUser)
				newAnnot.save()
			
class ParseKml(object):
	def __init__(self):
		self.depth = 0
		self.count = 0
		self.dataBuffer = []
		self.extendedData = {}
		self.lastAttr = None
		self.placeName = None
		self.shapePoints = []
		self.shapeLineStrings = []
		self.shapeLinearRings = []
		self.shapeOuterPolys = []
		self.shapeInnerPolys = []
		self.shapeType = None
		self.shapeSubType = None
		self.db = None
		self.kmlGeoms = ["Point","LineString","LinearRing",
			"Polygon","MultiGeometry","Model",
			"gx:Track"]
		self.geomDepth = 0

	def StartEl(self, name, attrs):
		#print self.depth, name, attrs
		if name in ["SimpleData", "coordinates", "name"]:
			self.dataBuffer = []

		if name == "ExtendedData":
			self.extendedData = {}

		if name in self.kmlGeoms:
			if self.geomDepth == 0:
				self.shapeType = name
			self.geomDepth += 1

		if name in ["outerBoundaryIs", "innerBoundaryIs"]:
			self.shapeSubType = name

		if name == "Placemark":
			self.count += 1
			if self.count % 1000 == 0:
				print self.count

		self.depth += 1
		self.lastAttr = attrs

	def EndEl(self, name):
		if name == "SimpleData":
			txt = "".join(self.dataBuffer)
			self.dataBuffer = []
			self.extendedData[self.lastAttr["name"]] = txt

		if name == "coordinates":
			txt = "".join(self.dataBuffer)

			txtSp1 = txt.split(" ")
			ptList = []
			for pttxt in txtSp1:

				txtSp2 = pttxt.split(",")
				nums = tuple(map(float, txtSp2))
				ptList.append(nums)

			if self.shapeType == "Point":
				self.shapePoints.extend(ptList)
			if self.shapeType == "LineString":
				self.shapeLineStrings.append(ptList)
			if self.shapeType == "LinearRing":
				self.shapeLinearRings.append(ptList)
			if self.shapeSubType == "outerBoundaryIs":
				self.shapeOuterPolys.append(ptList)
			if self.shapeSubType == "innerBoundaryIs":
				self.shapeInnerPolys.append(ptList)

			self.dataBuffer = []

		if name == "name":
			txt = "".join(self.dataBuffer)
			self.placeName = txt
			self.dataBuffer = []

		if name == "Placemark":
			pn = None
			if self.placeName is not None:
				pn = TitleCase(self.placeName)
				pn = pn.replace("\n", "")
				pn = pn.replace("\r", "")

			shape = None
	
			if self.shapeType in ["Polygon"]:
				#print self.shapeType, len(self.shapeOuterPolys), len(self.shapeInnerPolys)
				shape = Polygon(self.shapeOuterPolys[0], self.shapeInnerPolys)

			if self.shapeType in ["MultiGeometry"]:
				outer = map(Polygon, self.shapeOuterPolys)
				inner = map(Polygon, self.shapeInnerPolys)

				poly = []
				for o in outer:
					ihit = []
					for i in inner:
						if o.intersects(i):
							ihit.append(i.exterior.coords)
					poly.append(Polygon(o.exterior.coords, ihit))
				shape = MultiPolygon(poly)

			if self.shapeType == "LineString":
				shape = LineString(self.shapeLineStrings[0])

			if self.shapeType == "LinearRing":
				shape = LinearRing(self.shapeLinearRings[0])

			if self.shapeType == "Point":
				if len(self.shapePoints) == 1:
					shape = Point(self.shapePoints[0])
				else:
					shape = MultiPoint(self.shapePoints)

			if shape is None:
				raise RuntimeError("Unknown shape type: "+str(self.shapeType))

			#print self.placeName, self.shape, self.extendedData
			self.extendedData["name"] = pn
			self.db.HandlePlacemark(pn, shape, self.extendedData)
			self.extendedData = {}
			self.placeName = None
			self.shapePoints = []
			self.shapeOuterPolys = []
			self.shapeInnerPolys = []
			self.shapeLineStrings = []
			self.shapeLinearRings = []
			self.shapeType = None

		if name in self.kmlGeoms:
			self.geomDepth -= 1

		if name in ["outerBoundaryIs", "innerBoundaryIs"]:
			self.shapeSubType = None

		self.depth -= 1

	def CharData(self, data):
		self.dataBuffer.append(data)
		#print data

	def ParseFile(self, ha):
		parser = xml.parsers.expat.ParserCreate()

		parser.StartElementHandler = self.StartEl
		parser.EndElementHandler = self.EndEl
		parser.CharacterDataHandler = self.CharData

		parser.ParseFile(ha)


if __name__=="__main__":
	

	inFi = bz2.BZ2File("SM.kml.bz2", "r")
	db = Db()

	ep = ParseKml()
	ep.db = db
	with transaction.atomic():
		ep.ParseFile(inFi)

	ep.db = None
	del db


