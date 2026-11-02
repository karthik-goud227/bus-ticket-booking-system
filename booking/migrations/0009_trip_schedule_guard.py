"""Serialize schedules per bus and reject overlapping active trips in Oracle."""
from django.db import migrations


TRIGGER = """
CREATE OR REPLACE TRIGGER trg_trip_no_overlap
FOR INSERT OR UPDATE OF bus_id, departure_at, arrival_at, is_cancelled ON booking_trip
COMPOUND TRIGGER
    TYPE id_list IS TABLE OF booking_trip.id%TYPE INDEX BY PLS_INTEGER;
    changed_ids id_list;
    changed_count PLS_INTEGER := 0;
    locked_bus_id booking_bus.id%TYPE;

    BEFORE EACH ROW IS
    BEGIN
        IF :NEW.is_cancelled = 0 THEN
            SELECT id INTO locked_bus_id FROM booking_bus
            WHERE id = :NEW.bus_id FOR UPDATE;
        END IF;
    END BEFORE EACH ROW;

    AFTER EACH ROW IS
    BEGIN
        changed_count := changed_count + 1;
        changed_ids(changed_count) := :NEW.id;
    END AFTER EACH ROW;

    AFTER STATEMENT IS
        conflict_count NUMBER;
    BEGIN
        FOR i IN 1 .. changed_count LOOP
            SELECT COUNT(*) INTO conflict_count
            FROM booking_trip candidate
            JOIN booking_trip other_trip
              ON other_trip.bus_id = candidate.bus_id
             AND other_trip.id <> candidate.id
             AND other_trip.is_cancelled = 0
             AND other_trip.departure_at < candidate.arrival_at
             AND other_trip.arrival_at > candidate.departure_at
            WHERE candidate.id = changed_ids(i)
              AND candidate.is_cancelled = 0;
            IF conflict_count > 0 THEN
                raise_application_error(-20011, 'Bus has an overlapping trip');
            END IF;
        END LOOP;
    END AFTER STATEMENT;
END trg_trip_no_overlap;
"""


class Migration(migrations.Migration):
    dependencies = [("booking", "0008_waitlist_offer_rules")]
    operations = [migrations.RunSQL(
        sql=[(TRIGGER, None)],
        reverse_sql=[("DROP TRIGGER trg_trip_no_overlap", None)],
    )]
