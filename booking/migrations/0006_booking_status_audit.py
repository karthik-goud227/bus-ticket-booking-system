"""Store booking status transitions with an Oracle row-level trigger."""
import django.db.models.deletion
from django.db import migrations, models


AUDIT_TRIGGER = """
CREATE OR REPLACE TRIGGER trg_booking_status_audit
AFTER INSERT OR UPDATE OF status ON booking_booking
FOR EACH ROW
BEGIN
    IF INSERTING THEN
        INSERT INTO booking_bookingstatusevent
            (booking_id, old_status, new_status, changed_at)
        VALUES (:NEW.id, NULL, :NEW.status, SYSTIMESTAMP);
    ELSIF :OLD.status <> :NEW.status THEN
        INSERT INTO booking_bookingstatusevent
            (booking_id, old_status, new_status, changed_at)
        VALUES (:NEW.id, :OLD.status, :NEW.status, SYSTIMESTAMP);
    END IF;
END;
"""


class Migration(migrations.Migration):
    dependencies = [("booking", "0005_active_waitlist_unique")]
    operations = [
        migrations.CreateModel(
            name="BookingStatusEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("old_status", models.CharField(blank=True, max_length=12, null=True)),
                ("new_status", models.CharField(max_length=12)),
                ("changed_at", models.DateTimeField(editable=False)),
                ("booking", models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name="status_events", to="booking.booking",
                )),
            ],
            options={
                "ordering": ["changed_at", "id"],
                "indexes": [models.Index(
                    fields=["booking", "changed_at", "id"],
                    name="idx_booking_event_order",
                )],
            },
        ),
        # Keep the PL/SQL block as one statement; a plain RunSQL string loses
        # the final END; terminator when Django splits Oracle SQL statements.
        migrations.RunSQL(
            sql=[(AUDIT_TRIGGER, None)],
            reverse_sql=[("DROP TRIGGER trg_booking_status_audit", None)],
        ),
    ]
