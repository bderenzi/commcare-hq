# -*- coding: utf-8 -*-
# Generated by Django 1.10.7 on 2017-06-28 14:58
from __future__ import unicode_literals

from __future__ import absolute_import
from django.db import migrations

from corehq.sql_db.operations import noop_migration


class Migration(migrations.Migration):

    dependencies = [
        ('sql_accessors', '0045_drop_case_modified_since'),
    ]

    operations = [
        noop_migration()
    ]
