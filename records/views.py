from django.shortcuts import render
from django.http import HttpResponse
from .models import Record

def index(request):
	return HttpResponse("Hello, world. You're at the index.")

def record(request, record_id):
	rec = Record.objects.get(id=record_id)

	return HttpResponse("Record %s." % rec.currentName)

