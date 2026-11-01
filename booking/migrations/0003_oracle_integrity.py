"""Oracle triggers for relationships that ordinary foreign keys cannot express."""
from django.db import migrations


TRIP_SEAT_TRIGGER = """
CREATE OR REPLACE TRIGGER trg_tripseat_same_trip_bus
BEFORE INSERT OR UPDATE OF trip_id, seat_id, booking_id ON booking_tripseat
FOR EACH ROW
DECLARE
    trip_bus_id NUMBER;
    seat_bus_id NUMBER;
    booking_trip_id NUMBER;
BEGIN
    SELECT bus_id INTO trip_bus_id FROM booking_trip WHERE id = :NEW.trip_id;
    SELECT bus_id INTO seat_bus_id FROM booking_seat WHERE id = :NEW.seat_id;
    IF trip_bus_id <> seat_bus_id THEN
        raise_application_error(-20001, 'Seat belongs to another bus');
    END IF;
    IF :NEW.booking_id IS NOT NULL THEN
        SELECT trip_id INTO booking_trip_id FROM booking_booking WHERE id = :NEW.booking_id;
        IF booking_trip_id <> :NEW.trip_id THEN
            raise_application_error(-20002, 'Booking belongs to another trip');
        END IF;
    END IF;
END;
"""

WAITLIST_TRIGGER = """
CREATE OR REPLACE TRIGGER trg_waitlist_offer_trip
BEFORE INSERT OR UPDATE OF trip_id, offered_seat_id ON booking_waitlistentry
FOR EACH ROW
DECLARE
    seat_trip_id NUMBER;
BEGIN
    IF :NEW.offered_seat_id IS NOT NULL THEN
        SELECT trip_id INTO seat_trip_id FROM booking_tripseat WHERE id = :NEW.offered_seat_id;
        IF seat_trip_id <> :NEW.trip_id THEN
            raise_application_error(-20003, 'Offered seat belongs to another trip');
        END IF;
    END IF;
END;
"""


class Migration(migrations.Migration):
    dependencies = [("booking", "0002_payment")]
    operations = [
        migrations.RunSQL([(TRIP_SEAT_TRIGGER, None)], [("DROP TRIGGER trg_tripseat_same_trip_bus", None)]),
        migrations.RunSQL([(WAITLIST_TRIGGER, None)], [("DROP TRIGGER trg_waitlist_offer_trip", None)]),
    ]
