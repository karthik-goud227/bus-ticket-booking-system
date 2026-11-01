"""Exercise Oracle cross-table triggers without leaving test data behind."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction
from django.utils import timezone

from booking.models import Booking, Bus, Seat, Trip, TripSeat, WaitlistEntry


def expect_oracle_error(label, code, action):
    try:
        with transaction.atomic():
            action()
    except DatabaseError as error:
        if code not in str(error):
            raise CommandError(f"{label}: unexpected database error: {error}") from error
        return
    raise CommandError(f"{label}: Oracle accepted invalid data; expected {code}.")


class Command(BaseCommand):
    help = "Verify three Oracle integrity triggers and roll back all probe rows."

    def handle(self, *args, **options):
        marker = uuid4().hex[:10].upper()
        with transaction.atomic():
            user = get_user_model().objects.create_user(username=f"probe_{marker.lower()}", password=uuid4().hex)
            bus_a = Bus.objects.create(registration_number=f"PRA{marker}", operator_name="Probe", bus_type="Test")
            bus_b = Bus.objects.create(registration_number=f"PRB{marker}", operator_name="Probe", bus_type="Test")
            seat_a = Seat.objects.create(bus=bus_a, number="A1")
            seat_b = Seat.objects.create(bus=bus_b, number="B1")
            depart = timezone.now() + timedelta(days=3)
            trip_a = Trip.objects.create(
                bus=bus_a, origin="Probe A", destination="Probe B",
                departure_at=depart, arrival_at=depart + timedelta(hours=2), fare=100,
            )
            trip_b = Trip.objects.create(
                bus=bus_b, origin="Probe C", destination="Probe D",
                departure_at=depart + timedelta(hours=3), arrival_at=depart + timedelta(hours=5), fare=100,
            )
            inventory_a = TripSeat.objects.create(trip=trip_a, seat=seat_a)
            inventory_b = TripSeat.objects.create(trip=trip_b, seat=seat_b)

            expect_oracle_error(
                "Seat/bus rule", "ORA-20001",
                lambda: TripSeat.objects.create(trip=trip_a, seat=seat_b),
            )
            self.stdout.write(self.style.SUCCESS("PASS: seat from another bus rejected (ORA-20001)."))

            wrong_booking = Booking.objects.create(
                reference=f"P{marker}", user=user, trip=trip_b,
                status=Booking.Status.HELD, total_fare=100,
                hold_expires_at=timezone.now() + timedelta(minutes=10),
            )
            expect_oracle_error(
                "Booking/trip rule", "ORA-20002",
                lambda: TripSeat.objects.filter(id=inventory_a.id).update(
                    status=TripSeat.Status.HELD, booking=wrong_booking,
                    hold_expires_at=wrong_booking.hold_expires_at,
                ),
            )
            self.stdout.write(self.style.SUCCESS("PASS: booking from another trip rejected (ORA-20002)."))

            expect_oracle_error(
                "Waiting-list offer rule", "ORA-20003",
                lambda: WaitlistEntry.objects.create(
                    trip=trip_a, user=user, status=WaitlistEntry.Status.OFFERED,
                    offered_seat=inventory_b,
                    offer_expires_at=timezone.now() + timedelta(minutes=10),
                ),
            )
            self.stdout.write(self.style.SUCCESS("PASS: offer from another trip rejected (ORA-20003)."))
            transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS("All probe rows rolled back. Your project data is unchanged."))
