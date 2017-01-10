from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, HttpResponseRedirect, StreamingHttpResponse
from django.template import loader
from django.contrib.gis.geos import GEOSGeometry, Point, Polygon, MultiPolygon
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import login_required
from django.utils.datastructures import MultiValueDictKeyError
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db.models.functions import Length
from django.core.exceptions import ObjectDoesNotExist
from .models import *
import json
import re
import datetime
import copy
from cStringIO import StringIO
from pyo5m import OsmData

def index(request):
	recs = Record.objects.all()[:100]

	output = []
	for rec in recs:
		jrec = {}
		jrec["id"] = rec.id		
		jrec["name"] = rec.currentName		
		jrec["lat"] = rec.currentPosition.y
		jrec["lon"] = rec.currentPosition.x
		output.append(jrec)

	template = loader.get_template('records/index.html')
	return HttpResponse(template.render({"records": recs, "recordsJson": json.dumps(output)}, request))

def record(request, record_id):
	rec = get_object_or_404(Record, id=record_id)
	ds = rec.datasetSeries
	snapshots = DatasetSnapshot.objects.filter(datasetSeries = ds)
	annotations = RecordTextAttribute.objects.filter(record = rec).order_by('timestamp')
	attribs = AttributeType.objects.filter(datasetSeries = ds)

	#Consolidate annotations
	latestAttribs = {}
	for attrib in attribs:
		latestAttribs[attrib.name] = None
	for annotation in annotations:
		latestAttribs[annotation.attrib.name] = annotation

	template = loader.get_template('records/record.html')
	return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 
		'snapshots': snapshots, 'annotations': latestAttribs}, request))

@login_required
def record_edit(request, record_id):
	rec = get_object_or_404(Record, id=record_id)
	ds = rec.datasetSeries
	annotations = RecordTextAttribute.objects.filter(record = rec).order_by('timestamp')
	attribs = AttributeType.objects.filter(datasetSeries = ds)
	attribsById = {}
	for attrib in attribs:
		attribsById[attrib.id] = attrib

	#Consolidate annotations
	latestAttribs = {}
	for attrib in attribs:
		latestAttribs[attrib.name] = (None, attrib)
	for annotation in annotations:
		latestAttribs[annotation.attrib.name] = (annotation, annotation.attrib)

	try:
		#Update record
		changed = False
		actionMessage = "No change to record"
		timeNow = datetime.datetime.now()

		if request.POST["name"] != rec.currentName:
			rec.currentName = request.POST["name"]
			changed = True
			newAnnot = RecordNameEdit(record = rec,
				data = request.POST["name"], 
				timestamp = timeNow,
				user = request.user)
			newAnnot.save()

		dx = abs(float(request.POST["lon"]) - rec.currentPosition.x)
		dy = abs(float(request.POST["lat"]) - rec.currentPosition.y)
		if dx >= 1e-7 or dy >= 1e-7:
			pos = GEOSGeometry("POINT ({} {})".format(request.POST["lon"], request.POST["lat"]), srid=4326)
			rec.currentPosition = pos
			changed = True
			newAnnot = RecordPositionEdit(record = rec,
				data = pos, 
				timestamp = timeNow,
				user = request.user)
			newAnnot.save()

		for k in request.POST:
			if k[:6] != "attrib": continue
			attribId = int(k[6:])
			formAttrib = attribsById[attribId]
			kAttrib = latestAttribs[formAttrib.name][0]

			if (kAttrib is None and len(request.POST[k]) > 0) or \
				(kAttrib is not None and request.POST[k] != kAttrib.data):

				changed = True
				newAnnot = RecordTextAttribute(record = rec,
					attrib = formAttrib,
					data = request.POST[k],
					timestamp = timeNow,	
					user = request.user)
				newAnnot.save()
				latestAttribs[formAttrib.name] = (newAnnot, formAttrib)

		if changed:
			rchange = RecentChange(record = rec, timestamp = timeNow, user = request.user)
			rchange.save()

			rec.save()		
			actionMessage = "Record updated"

		template = loader.get_template('records/record_edit.html')
		return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 
			'action_msg': actionMessage, 'annotations': latestAttribs}, request))

	except KeyError:

		template = loader.get_template('records/record_edit.html')
		return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 
			'action_msg': None, 'annotations': latestAttribs}, request))

def original_record(request, record_id, snapshot_id):
	rec = get_object_or_404(Record, id=record_id)
	externalId = rec.externalId
	datasetSeries = rec.datasetSeries
	snapshot = get_object_or_404(DatasetSnapshot, id=snapshot_id)
	orig = get_object_or_404(DatasetRecord, externalId = externalId, datasetSnapshot = snapshot)
	original = json.loads(orig.dataJson)

	template = loader.get_template('records/record_snapshot.html')
	return HttpResponse(template.render({"record": rec, "snapshot": snapshot, 
		'datasetSeries': datasetSeries, "original": original}, request))

def records_query(request):
	try:
		bbox = map(float, request.GET["bbox"].split(","))
	except (ValueError, MultiValueDictKeyError):
		return HttpResponseBadRequest("Bad bbox")
	try:
		geomStr = 'POLYGON(( {0} {1}, {0} {3}, {2} {3}, {2} {1}, {0} {1} ))'.format(*bbox)
	except IndexError:
		return HttpResponseBadRequest("Bad bbox length")
	
	geom = GEOSGeometry(geomStr, srid=4326)
	recs = Record.objects.filter(currentPosition__within=geom)[:100]

	output = []
	for rec in recs:
		jrec = {}
		jrec["id"] = rec.id		
		jrec["name"] = rec.currentName		
		jrec["lat"] = rec.currentPosition.y
		jrec["lon"] = rec.currentPosition.x
		output.append(jrec)

	return JsonResponse(output, safe=False)	

def logout_view(request):
	logout(request)
	return HttpResponseRedirect("/")

def register(request):
	actionMessage = None
	reqUsername = ""
	reqEmail = ""
	reqPassword = ""
	registerSuccess = False

	try:
		reqUsername = request.POST["username"]
		reqEmail = request.POST["email"]
		reqPassword = request.POST["password"]

		validate_email(reqEmail)

		if len(reqUsername) > 50:
			raise ValueError("User name too long (limit is 50 characters)")
		if len(reqPassword) > 1000:
			raise ValueError("Password too long (limit is 1000 characters)")
		if len(reqPassword) < 6:
			raise ValueError("Password too short (limit is 6 characters)")

		user = User.objects.create_user(reqUsername, reqEmail, reqPassword)
		user.save()
		login(request, user)
		actionMessage = "New user registered!"
		registerSuccess = True
	except MultiValueDictKeyError:
		pass
	except ValueError as err:
		actionMessage = str(err)
	except IntegrityError as err:
		actionMessage = "User name is not unique"
	except ValidationError as err:
		actionMessage = "Error validating email"
	
	if not registerSuccess:
		logout(request)
	template = loader.get_template('registration/register.html')
	return HttpResponse(template.render({"actionMessage": actionMessage, 
		"reqUsername": reqUsername, "reqEmail": reqEmail, 
		"reqPassword": reqPassword, "registerSuccess": registerSuccess}, request))

def dataset_series(request, dataset_series_id):
	ds = get_object_or_404(DatasetSeries, id=dataset_series_id)
	snapshots = DatasetSnapshot.objects.filter(datasetSeries = ds)
	attribs = AttributeType.objects.filter(datasetSeries = ds)
	
	template = loader.get_template('records/dataset_series.html')
	return HttpResponse(template.render({"datasetSeries": ds, "snapshots": snapshots,
		"attribs": attribs}, request))

def record_history(request, record_id):
	rec = get_object_or_404(Record, id=record_id)
	ds = rec.datasetSeries
	snapshots = DatasetSnapshot.objects.filter(datasetSeries = ds)
	annotations = RecordTextAttribute.objects.filter(record = rec)
	nameEdits = RecordNameEdit.objects.filter(record = rec)
	positionEdits = RecordPositionEdit.objects.filter(record = rec)
	attribs = AttributeType.objects.filter(datasetSeries = ds)

	#Combine edits and sort by time stamp
	sortableEdits = []
	for edit in annotations:
		edit.attribName = edit.attrib.name
		sortableEdits.append((edit.timestamp, edit))
	for edit in nameEdits:
		edit.attribName = "name"
		sortableEdits.append((edit.timestamp, edit))
	for edit in positionEdits:
		edit.attribName = "position"
		sortableEdits.append((edit.timestamp, edit))
	sortableEdits.sort()
	edits = [tmp[1] for tmp in sortableEdits]

	template = loader.get_template('records/record_history.html')
	return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 
		'snapshots': snapshots, 'edits': edits}, request))

def recent_changes(request):
	timeNow = datetime.datetime.now()
	recentChanges = RecentChange.objects.order_by("-timestamp")[:100]

	template = loader.get_template('records/recent_changes.html')
	return HttpResponse(template.render({"recent_changes": recentChanges}, request))

def dataset_series_list(request):
	ds = DatasetSeries.objects.all()

	template = loader.get_template('records/dataset_series_list.html')
	return HttpResponse(template.render({"dataset_series": ds}, request))
	
def dataset_series_long_names(request, dataset_series_id):
	ds = get_object_or_404(DatasetSeries, id=dataset_series_id)
	try:
		descriptionAttrib = AttributeType.objects.get(datasetSeries = ds, name="description")
	except ObjectDoesNotExist:
		descriptionAttrib = None

	#Process form if necessary
	actionMessage = None
	timeNow = datetime.datetime.now()
	changedRecs = set()
	if request.user.is_authenticated and "action" in request.POST and descriptionAttrib is not None:
		for k in request.POST:
			if k[:4] == "name":
				nameId = int(k[4:])
				#Change if name changed
				rec = get_object_or_404(Record, id=nameId)
				if rec.currentName != request.POST[k]:
					rec.currentName = request.POST[k]
					rec.save()

					#Log name change history
					rne = RecordNameEdit(record = rec, data = request.POST[k], timestamp = timeNow, user = request.user)
					rne.save()

					changedRecs.add(rec)

			if k[:11] == "description":
				descId = int(k[11:])
				rec = get_object_or_404(Record, id=descId)
				try:
					desc = RecordTextAttribute.objects.filter(record=rec, attrib=descriptionAttrib).latest('timestamp')
					descText = desc.data
				except ObjectDoesNotExist:
					descText = ""

				if descText != request.POST[k]:
					descNew = RecordTextAttribute(record = rec, attrib = descriptionAttrib, data = request.POST[k], timestamp = timeNow, user = request.user)
					descNew.save()
			
					changedRecs.add(rec)

	for rec in changedRecs:
		#Log recent change
		rchange = RecentChange(record = rec, timestamp = timeNow, user = request.user)
		rchange.save()
		

	recs = Record.objects.filter(datasetSeries = ds).order_by(Length("currentName").desc())[:100]

	descriptions = []
	for rec in recs:
		try:
			desc = RecordTextAttribute.objects.filter(record=rec, attrib=descriptionAttrib).latest('timestamp')
			descriptions.append(desc.data)
		except ObjectDoesNotExist:
			descriptions.append("")

	recsAndDescsZipped = zip(recs, descriptions)
	template = loader.get_template('records/dataset_series_long_names.html')
	return HttpResponse(template.render({"datasetSeries": ds, "recsAndDescsZipped": recsAndDescsZipped}, request))

def snapshot(request, snapshot_id):
	snapshot = get_object_or_404(DatasetSnapshot, id=snapshot_id)
	records = DatasetRecord.objects.filter(datasetSnapshot = snapshot)[:20]

	zippedDataRecords = []
	for rec in records:
		zippedDataRecords.append((rec, json.loads(rec.dataJson)))

	template = loader.get_template('records/snapshot.html')
	return HttpResponse(template.render({"snapshot": snapshot, "zippedDataRecords": zippedDataRecords}, request))

def PolygonToOsm(poly, osmData, nextId, tags):
	outerRing = poly[0]
	metaData = (None, None, None, None, None, None)

	if poly.num_interior_rings == 0:
		refs = []
		for pt in outerRing:
			osmData.nodes.append((nextId[0], metaData, {}, (pt[1], pt[0])))
			refs.append(nextId[0])
			nextId[0] -= 1
		refs.append(refs[0])

		osmData.ways.append((nextId[1], metaData, tags, refs))
		nextId[1] -= 1

	else:
		#Create relation
		refs = []
		for pt in outerRing:
			osmData.nodes.append((nextId[0], metaData, {}, (pt[1], pt[0])))
			refs.append(nextId[0])
			nextId[0] -= 1
		refs.append(refs[0])

		osmData.ways.append((nextId[1], metaData, {}, refs))
		outerId = nextId[1]
		nextId[1] -= 1

		innerIds = []
		for holeId in range(1, poly.num_interior_rings+1):
			hole = poly[holeId]
			refs = []
			for pt in hole:
				osmData.nodes.append((nextId[0], metaData, {}, (pt[1], pt[0])))
				refs.append(nextId[0])
				nextId[0] -= 1
			refs.append(refs[0])

			osmData.ways.append((nextId[1], metaData, {}, refs))
			innerIds.append(nextId[1])
			nextId[1] -= 1

		refs = []
		tags2 = copy.copy(tags)
		tags2["type"] = "multipolygon"
		refs.append(("way", outerId, "outer"))
		for iid in innerIds:
			refs.append(("way", iid, "inner"))
		osmData.relations.append((nextId[2], metaData, tags2, refs))
		nextId[2] -= 1

def GeoCollectionToOsm(shapes, osmData, nextId, tags):
	for shp in shapes:
		metaData = (None, None, None, None, None, None)
		if isinstance(shp, Point):
			osmData.nodes.append((nextId[0], metaData, tags, (rec.currentPosition.y, rec.currentPosition.x)))
			nextId[0] -= 1
		if isinstance(shp, Polygon):
			PolygonToOsm(shp, osmData, nextId, tags)
		if isinstance(shp, MultiPolygon):
			for poly in shp:
				PolygonToOsm(poly, osmData, nextId, tags)

def export_view(request):
	try:
		bbox = map(float, request.GET["bbox"].split(","))
	except (ValueError, MultiValueDictKeyError):
		return HttpResponseBadRequest("Bad bbox")
	try:
		geomStr = 'POLYGON(( {0} {1}, {0} {3}, {2} {3}, {2} {1}, {0} {1} ))'.format(*bbox)
	except IndexError:
		return HttpResponseBadRequest("Bad bbox length")
	
	geom = GEOSGeometry(geomStr, srid=4326)
	recs = Record.objects.filter(currentPosition__within=geom)[:100]

	osmData = OsmData.OsmData()

	nextId = [-1, -1, -1]
	for rec in recs:
		tags = {"name": rec.currentName}
		try:
			shape = RecordShapeEdit.objects.filter(record = rec).latest("timestamp")

			#Use specified shape
			shapes = GEOSGeometry(shape.data, srid=4326)
			GeoCollectionToOsm(shapes, osmData, nextId, tags)

		except ObjectDoesNotExist:
			#Use simple node position
			metaData = (None, None, None, None, None, None)
			osmData.nodes.append((nextId[0], metaData, tags, (rec.currentPosition.y, rec.currentPosition.x)))
			nextId[0] -= 1

	xmlStr = StringIO()
	osmData.SaveToOsmXml(xmlStr)
	
	return HttpResponse(xmlStr.getvalue(), content_type='application/xml')

