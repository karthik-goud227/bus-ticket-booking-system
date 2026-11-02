"""Recompile the schedule trigger after 0009 omitted its final semicolon."""
from django.db import migrations
from importlib import import_module

TRIGGER = import_module("booking.migrations.0009_trip_schedule_guard").TRIGGER


class Migration(migrations.Migration):
    dependencies = [("booking", "0009_trip_schedule_guard")]
    operations = [migrations.RunSQL(sql=[(TRIGGER, None)], reverse_sql=migrations.RunSQL.noop)]
