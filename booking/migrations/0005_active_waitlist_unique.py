"""Enforce one active waiting-list entry per passenger and trip in Oracle."""
from django.db import migrations


CREATE_INDEX = """
CREATE UNIQUE INDEX uq_active_waitlist
ON booking_waitlistentry (
    CASE WHEN status IN ('WAITING', 'OFFERED') THEN trip_id END,
    CASE WHEN status IN ('WAITING', 'OFFERED') THEN user_id END
)
"""


class Migration(migrations.Migration):
    dependencies = [("booking", "0004_reporting_views")]
    operations = [
        migrations.RunSQL(
            sql=CREATE_INDEX,
            reverse_sql="DROP INDEX uq_active_waitlist",
        ),
    ]
