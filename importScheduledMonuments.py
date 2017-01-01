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

		testOriginal="POLYGON ((0.004585821432403 53.39205655445362, 0.004370524051853 53.39197386424815, 0.003511999412435 53.39224718406162, 0.003334269156126 53.39230564512001, 0.003010761561655 53.39244359770373, 0.002313077441331 53.39273886079805, 0.002153264778766 53.3928494141358, 0.002098473352319 53.39289040220098, 0.001975450131408 53.39301575633081, 0.001571912175901 53.39342627983574, 0.00144845213223 53.39354238985806, 0.001054429533822 53.39382638644516, 0.000660690765872 53.39411654416967, 0.000258658810006 53.3944499832029, -0.000208743564432 53.39485788447784, -0.000230623648264 53.39490287808773, -0.000236528103555 53.39494760407232, -0.000210152629556 53.39499816331232, -0.000134789640903 53.39507021540287, -4.6693090052e-05 53.39512930610134, 8.4189758386e-05 53.39519086239132, 0.000320701021055 53.39528731045475, 0.000440541032034 53.39534108611749, 0.000495476965256 53.39537522708896, 0.000526128004445 53.39540340096636, 0.000552505095391 53.39545396900132, 0.00056354800768 53.39551912431292, 0.000561917344505 53.39565462410584, 0.001403023462806 53.39573616267051, 0.001776075560191 53.39578728279303, 0.002238095515083 53.39585922310508, 0.002415730663242 53.39589449667334, 0.00262892046244 53.39594829555955, 0.002759136797677 53.39599552084307, 0.003148451411336 53.39571166071373, 0.003852256735541 53.39519780287833, 0.004239121351319 53.39491876291179, 0.0048580524367 53.39447166424996, 0.00570113015205 53.39385822744637, 0.006098176439091 53.39356945364467, 0.006789195134597 53.39306853168554, 0.006903507578287 53.39298848546464, 0.006452162455299 53.39282038704182, 0.006147262062949 53.39269606225199, 0.005531717833986 53.39243518140811, 0.005205915002175 53.39230503820097, 0.004585821432403 53.39205655445362))"

		test="POLYGON ((0.004585821432403 53.39205655445362, 0.004370524051853 53.39197386424815, 0.003511999412435 53.39224718406162, 0.003334269156126 53.39230564512001, 0.003010761561655 53.39244359770373, 0.002313077441331 53.39273886079805, 0.002153264778766 53.3928494141358, 0.002098473352319 53.39289040220098, 0.001975450131408 53.39301575633081, 0.001571912175901 53.39342627983574, 0.00144845213223 53.39354238985806, 0.001054429533822 53.39382638644516, 0.000660690765872 53.39411654416967, 0.000258658810006 53.3944499832029, -0.000208743564432 53.39485788447784, -0.000230623648264 53.39490287808773, -0.000236528103555 53.39494760407232, -0.000210152629556 53.39499816331232, -0.000134789640903 53.39507021540287, 0.0000 53.39512930610134, 0.00001 53.39519086239132, 0.000320701021055 53.39528731045475, 0.000440541032034 53.39534108611749, 0.000495476965256 53.39537522708896, 0.000526128004445 53.39540340096636, 0.000552505095391 53.39545396900132, 0.00056354800768 53.39551912431292, 0.000561917344505 53.39565462410584, 0.001403023462806 53.39573616267051, 0.001776075560191 53.39578728279303, 0.002238095515083 53.39585922310508, 0.002415730663242 53.39589449667334, 0.00262892046244 53.39594829555955, 0.002759136797677 53.39599552084307, 0.003148451411336 53.39571166071373, 0.003852256735541 53.39519780287833, 0.004239121351319 53.39491876291179, 0.0048580524367 53.39447166424996, 0.00570113015205 53.39385822744637, 0.006098176439091 53.39356945364467, 0.006789195134597 53.39306853168554, 0.006903507578287 53.39298848546464, 0.006452162455299 53.39282038704182, 0.006147262062949 53.39269606225199, 0.005531717833986 53.39243518140811, 0.005205915002175 53.39230503820097, 0.004585821432403 53.39205655445362))"

		shape = wkt.loads(test)

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

			if not shape.is_valid:
				shape = shape.buffer(0.0)
			shape2 = GeometryCollection([shape])
			shape3 = GEOSGeometry(buffer(shape2.wkb), srid=4326)
			print shape3.valid

			try:
				newAnnot = RecordShapeEdit(record = rec2,
					data = shape3, 
					timestamp = self.importTime,
					user = self.importUser)
				newAnnot.save()
			except Exception as err:
				print err
				print shape3.valid
			
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


