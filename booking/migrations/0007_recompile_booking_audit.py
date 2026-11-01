"""Replace the incomplete audit trigger created by the first 0006 migration."""
from django.db import migrations


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
    dependencies = [("booking", "0006_booking_status_audit")]
    operations = [
        # 0006 was already applied on the original database with an invalid
        # trigger, so replace it there and preserve the full PL/SQL block.
        migrations.RunSQL(
            sql=[(AUDIT_TRIGGER, None)],
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
