from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, HttpResponseBadRequest, JsonResponse
from django.template import loader
from django.contrib.gis.geos import GEOSGeometry
from .models import Record, DatasetSnapshot, DatasetRecord
import json

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

	template = loader.get_template('records/record.html')
	return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 'snapshots': snapshots}, request))

def record_edit(request, record_id):
	rec = get_object_or_404(Record, id=record_id)
	ds = rec.datasetSeries

	try:
		#Update record
		rec.currentName = request.POST["name"]
		rec.currentPosition = GEOSGeometry("POINT ({} {})".format(request.POST["lon"], request.POST["lat"]), srid=4326)
		rec.save()		

		template = loader.get_template('records/record_edit.html')
		return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 'action_msg': "Record updated"}, request))

	except KeyError:
		template = loader.get_template('records/record_edit.html')
		return HttpResponse(template.render({"record": rec, 'datasetSeries': ds, 'action_msg': None}, request))

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
	except ValueError:
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

