# -*- coding: utf-8 -*-
# Generated by Django 1.10.4 on 2017-01-11 10:03
from __future__ import unicode_literals

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('records', '0008_auto_20170106_2222'),
    ]

    operations = [
        migrations.AddField(
            model_name='datasetsnapshot',
            name='timestamp',
            field=models.DateTimeField(default=datetime.datetime.now, verbose_name='timestamp'),
        ),
    ]
