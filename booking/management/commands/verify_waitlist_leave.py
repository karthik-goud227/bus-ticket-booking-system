"""Verify Oracle FIFO positions and immediate promotion after a passenger leaves."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from booking.models import Booking, Bus, Payment, Seat, Trip, TripSeat, WaitlistEntry
from booking.services import cancel_booking, confirm_booking, hold_seats, join_waitlist, leave_waitlist


class Command(BaseCommand):
    help = "Verify waiting-list queue positions and promotion when an offer is declined."

    def handle(self, *args, **options):
        marker = uuid4().hex[:10].upper()
        users = []
        bus = trip = None
        try:
            for suffix in ("owner", "first", "second"):
                users.append(get_user_model().objects.create(username=f"leave_{suffix}_{marker.lower()}"))
            owner, first, second = users
            bus = Bus.objects.create(
                registration_number=f"LEAVE{marker}", operator_name="Queue test", bus_type="Test"
            )
            seat = Seat.objects.create(bus=bus, number="L1")
            departure = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Leave A", destination="Leave B",
                departure_at=departure, arrival_at=departure + timedelta(hours=2), fare=100,
            )
            inventory = TripSeat.objects.create(trip=trip, seat=seat)
            booking = hold_seats(user=owner, trip=trip, seat_ids=[inventory.id])
            confirm_booking(user=owner, booking_id=booking.id)

            first_entry = join_waitlist(user=first, trip=trip)
            second_entry = join_waitlist(user=second, trip=trip)
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT entry_id, queue_position FROM v_waitlist_queue "
                    "WHERE trip_id = %s ORDER BY queue_position", [trip.id]
                )
                positions = cursor.fetchall()
            if positions != [(first_entry.id, 1), (second_entry.id, 2)]:
                raise CommandError(f"Unexpected FIFO positions: {positions}")
            self.stdout.write(self.style.SUCCESS("PASS: Oracle view assigned FIFO positions 1 and 2."))

            cancel_booking(user=owner, booking_id=booking.id)
            leave_waitlist(user=first, entry_id=first_entry.id)
            first_entry.refresh_from_db()
            second_entry.refresh_from_db()
            if (first_entry.status != WaitlistEntry.Status.CANCELLED
                    or first_entry.offered_seat_id is not None
                    or second_entry.status != WaitlistEntry.Status.OFFERED
                    or second_entry.offered_seat_id != inventory.id):
                raise CommandError("Declined offer was not passed to the next passenger.")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT queue_position FROM v_waitlist_queue WHERE entry_id = %s",
                    [second_entry.id],
                )
                position = cursor.fetchone()
            if position != (1,):
                raise CommandError(f"Second passenger did not move to position 1: {position}")
            self.stdout.write(self.style.SUCCESS("PASS: leaving passed the offer to passenger 2."))
            self.stdout.write(self.style.SUCCESS("PASS: Oracle view updated the active queue position."))
        finally:
            if trip is not None:
                Payment.objects.filter(booking__trip=trip).delete()
                WaitlistEntry.objects.filter(trip=trip).delete()
                TripSeat.objects.filter(trip=trip).delete()
                Booking.objects.filter(trip=trip).delete()
                Trip.objects.filter(id=trip.id).delete()
            if bus is not None:
                Seat.objects.filter(bus=bus).delete()
                Bus.objects.filter(id=bus.id).delete()
            if users:
                get_user_model().objects.filter(id__in=[user.id for user in users]).delete()
            self.stdout.write("Waiting-list test data removed.")
