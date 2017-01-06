from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse, HttpResponseRedirect, StreamingHttpResponse
from django.template import loader
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.auth import authenticate, logout, login
from django.contrib.auth.decorators import login_required
from django.utils.datastructures import MultiValueDictKeyError
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from .models import Record, DatasetSnapshot, DatasetRecord, DatasetSeries, AttributeType, RecordTextAttribute, RecordNameEdit, RecordPositionEdit, RecordShapeEdit
import json
import re
import datetime

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

		if float(request.POST["lon"]) != rec.currentPosition.x or float(request.POST["lat"]) != rec.currentPosition.y:
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

class ExportGenerator(object):
	def __init__(self):
		self.c = 0
		self.recs = Record.objects.all()
		self.recordTextAttributes = RecordTextAttribute.objects.all()
		self.attributeTypes = AttributeType.objects.all()
		self.recordNameEdits = RecordNameEdit.objects.all()
		self.recordShapeEdits = RecordShapeEdit.objects.all()
		self.recordPositionEdits = RecordPositionEdit.objects.all()
		self.openRootTagSent = False
		self.closeRootTagSent = False
		self.recordsDone = False
		self.attributeTypesDone = False
		self.recordNameEditsDone = False
		self.recordShapeEditsDone = False
		self.recordPositionEditsDone = False
		self.recordTextAttributesDone = False

	def __iter__(self):
		return self

	def __next__(self):
		return self.next()

	def next(self):
		if not self.openRootTagSent:
			self.openRootTagSent = True
			return "<export>\n"
		if self.recordTextAttributesDone:
			raise StopIteration()

		if not self.recordsDone:
			try:
				rec = self.recs[self.c]
				self.c += 1
				return rec.Xml()
			except IndexError:
				self.c = 0
				self.recordsDone = True

		if not self.recordNameEditsDone:
			try:
				rne = self.recordNameEdits[self.c]
				self.c += 1
				return rne.Xml()
			except IndexError:
				self.c = 0
				self.recordNameEditsDone = True

		if not self.recordPositionEditsDone:
			try:
				rne = self.recordPositionEdits[self.c]
				self.c += 1
				return rne.Xml()
			except IndexError:
				self.c = 0
				self.recordPositionEditsDone = True

		if not self.recordShapeEditsDone:
			try:
				rne = self.recordShapeEdits[self.c]
				self.c += 1
				return rne.Xml()
			except IndexError:
				self.c = 0
				self.recordShapeEditsDone = True

		if not self.attributeTypesDone:
			try:
				at = self.attributeTypes[self.c]
				self.c += 1
				return at.Xml()
			except IndexError:
				self.c = 0
				self.attributeTypesDone = True

		if not self.recordTextAttributesDone:
			try:
				rta = self.recordTextAttributes[self.c]
				self.c += 1
				return rta.Xml()
			except IndexError:
				self.c = 0
				self.recordTextAttributesDone = True

		self.closeRootTagSent = True
		return "</export>\n"


def export_view(request):
	gen = ExportGenerator()
	response = StreamingHttpResponse(gen, content_type="text/xml")
	response['Content-Disposition'] = 'inline'
	return response

