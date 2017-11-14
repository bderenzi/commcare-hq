# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-08-08 12:12
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations, models

from corehq.util.django_migrations import AlterFieldCreateIndexIfNotExists


class Migration(migrations.Migration):

    dependencies = [
        ('couchforms', '0002_auto_20170802_1505'),
    ]

    operations = [
        AlterFieldCreateIndexIfNotExists(
            model_name='unfinishedsubmissionstub',
            name='timestamp',
            field=models.DateTimeField(db_index=True),
        ),
    ]
