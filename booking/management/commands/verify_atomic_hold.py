"""Force a failure halfway through a two-seat hold and verify rollback."""
from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from booking.models import Booking, Bus, Seat, Trip, TripSeat
from booking.services import hold_seats


class Command(BaseCommand):
    help = "Verify that an exception during a group hold leaves no claimed seats or booking."

    def handle(self, *args, **options):
        marker = uuid4().hex[:10].upper()
        user = bus = trip = None
        try:
            user = get_user_model().objects.create_user(
                username=f"atomic_{marker.lower()}", password=uuid4().hex
            )
            bus = Bus.objects.create(
                registration_number=f"ATOMIC{marker}", operator_name="Rollback test", bus_type="Test"
            )
            seat_a = Seat.objects.create(bus=bus, number="A1")
            seat_b = Seat.objects.create(bus=bus, number="A2")
            depart = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Atomic A", destination="Atomic B",
                departure_at=depart, arrival_at=depart + timedelta(hours=2), fare=100,
            )
            inventory_a = TripSeat.objects.create(trip=trip, seat=seat_a)
            inventory_b = TripSeat.objects.create(trip=trip, seat=seat_b)

            original_save = TripSeat.save
            held_updates = 0

            def fail_on_second_hold(instance, *args, **kwargs):
                nonlocal held_updates
                if instance.status == TripSeat.Status.HELD:
                    held_updates += 1
                    if held_updates == 2:
                        raise RuntimeError("Injected failure on second seat")
                return original_save(instance, *args, **kwargs)

            try:
                with patch.object(TripSeat, "save", fail_on_second_hold):
                    hold_seats(
                        user=user, trip=trip,
                        seat_ids=[inventory_a.id, inventory_b.id],
                    )
            except RuntimeError as error:
                if str(error) != "Injected failure on second seat":
                    raise
            else:
                raise CommandError("The injected failure did not occur.")

            inventory = list(TripSeat.objects.filter(trip=trip).order_by("id"))
            booking_count = Booking.objects.filter(trip=trip).count()
            if (held_updates != 2 or booking_count != 0
                    or len(inventory) != 2
                    or any(seat.status != TripSeat.Status.AVAILABLE or seat.booking_id is not None
                           for seat in inventory)):
                raise CommandError(
                    f"Rollback failed: {held_updates} updates attempted, "
                    f"{booking_count} bookings, states {[seat.status for seat in inventory]}"
                )
            self.stdout.write(self.style.SUCCESS(
                "PASS: failure on second seat rolled back the first seat and booking."
            ))
        finally:
            if trip is not None:
                TripSeat.objects.filter(trip=trip).delete()
                Booking.objects.filter(trip=trip).delete()
                Trip.objects.filter(id=trip.id).delete()
            if bus is not None:
                Seat.objects.filter(bus=bus).delete()
                Bus.objects.filter(id=bus.id).delete()
            if user is not None:
                get_user_model().objects.filter(id=user.id).delete()
            self.stdout.write("Rollback test data removed.")
