"""Verify Oracle records real booking transitions in the same transaction."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction
from django.utils import timezone

from booking.models import Booking, BookingStatusEvent, Bus, Seat, Trip, TripSeat
from booking.services import cancel_booking, confirm_booking, hold_seats


class Command(BaseCommand):
    help = "Verify Oracle's booking-status audit trigger without retaining test rows."

    def handle(self, *args, **options):
        if connection.vendor != "oracle":
            raise CommandError("This verification requires Oracle.")

        marker = uuid4().hex[:10].lower()
        username = f"audit_{marker}"
        reference = None
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=username, password=uuid4().hex
            )
            bus = Bus.objects.create(
                registration_number=f"AU{marker.upper()}",
                operator_name="Audit test", bus_type="Test",
            )
            seat = Seat.objects.create(bus=bus, number="A1")
            departure = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Audit Test A", destination="Audit Test B",
                departure_at=departure,
                arrival_at=departure + timedelta(hours=2), fare=100,
            )
            inventory = TripSeat.objects.create(trip=trip, seat=seat)
            booking = hold_seats(user=user, trip=trip, seat_ids=[inventory.id])
            reference = booking.reference
            confirm_booking(user=user, booking_id=booking.id)
            cancel_booking(user=user, booking_id=booking.id)

            transitions = list(
                BookingStatusEvent.objects.filter(booking=booking)
                .order_by("id").values_list("old_status", "new_status")
            )
            expected = [
                (None, Booking.Status.HELD),
                (Booking.Status.HELD, Booking.Status.CONFIRMED),
                (Booking.Status.CONFIRMED, Booking.Status.CANCELLED),
            ]
            if transitions and transitions[0][0] == "":
                transitions[0] = (None, transitions[0][1])
            if transitions != expected:
                raise CommandError(f"Unexpected Oracle audit transitions: {transitions}")
            self.stdout.write(self.style.SUCCESS(
                "PASS: Oracle audited HELD, CONFIRMED, and CANCELLED in order."
            ))
            transaction.set_rollback(True)

        if (get_user_model().objects.filter(username=username).exists()
                or Booking.objects.filter(reference=reference).exists()):
            raise CommandError("Audit verification rows were not rolled back.")
        self.stdout.write("Audit and booking test rows rolled back together.")
