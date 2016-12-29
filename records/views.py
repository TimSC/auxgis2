from django.shortcuts import render
from django.http import HttpResponse
from django.template import loader
from .models import Record, DatasetSnapshot, DatasetRecord
import json

def index(request):
	return HttpResponse("Hello, world. You're at the index.")

def record(request, record_id):
	rec = Record.objects.get(id=record_id)
	datasetSeries = rec.datasetSeries
	snapshots = DatasetSnapshot.objects.filter(datasetSeries = datasetSeries)

	template = loader.get_template('records/record.html')
	return HttpResponse(template.render({"record": rec, 'snapshots': snapshots}, request))

def original_record(request, record_id, snapshot_id):
	rec = Record.objects.get(id=record_id)
	externalId = rec.externalId
	datasetSeries = rec.datasetSeries
	snapshot = DatasetSnapshot.objects.get(id=snapshot_id)
	orig = DatasetRecord.objects.get(externalId = externalId, datasetSnapshot = snapshot)
	original = json.loads(orig.dataJson)

	template = loader.get_template('records/record_snapshot.html')
	return HttpResponse(template.render({"record": rec, "snapshot": snapshot, "original": original}, request))

