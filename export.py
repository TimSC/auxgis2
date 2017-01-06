
import os, bz2, json, datetime
from django.db import transaction
from django.db import IntegrityError
import django.core.exceptions as dex

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "auxgis2.settings")
import django
django.setup()

from django.contrib.auth.models import User
from records.models import *
from records import views

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

if __name__=="__main__":
	fi = bz2.BZ2File("export.xml.bz2", "w")
	gen = ExportGenerator()
	for i, li in enumerate(gen):
		if i % 1000 ==0:
			print i
		fi.write(li.encode("utf8"))
	fi.close()
	
