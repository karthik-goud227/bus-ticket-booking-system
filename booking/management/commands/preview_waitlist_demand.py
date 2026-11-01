"""Temporarily show a nonempty waiting-list chart on the staff dashboard."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import connection
from django.utils import timezone

from booking.models import Booking, Bus, Payment, Seat, Trip, TripSeat, WaitlistEntry
from booking.services import cancel_booking, confirm_booking, hold_seats, join_waitlist


class Command(BaseCommand):
    help = "Create an isolated 1-waiting/1-offered trip until Enter is pressed."

    def handle(self, *args, **options):
        marker = uuid4().hex[:10].upper()
        users = []
        bus = trip = None
        try:
            for suffix in ("owner", "first", "second"):
                users.append(get_user_model().objects.create(
                    username=f"queue_preview_{suffix}_{marker.lower()}"
                ))
            owner, first, second = users
            bus = Bus.objects.create(
                registration_number=f"QPREV{marker}",
                operator_name="DBMS Queue Preview", bus_type="Demo",
            )
            seat = Seat.objects.create(bus=bus, number="Q1")
            departure = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Queue Demo A", destination="Queue Demo B",
                departure_at=departure, arrival_at=departure + timedelta(hours=2), fare=100,
            )
            inventory = TripSeat.objects.create(trip=trip, seat=seat)
            booking = hold_seats(user=owner, trip=trip, seat_ids=[inventory.id])
            confirm_booking(user=owner, booking_id=booking.id)
            first_entry = join_waitlist(user=first, trip=trip)
            second_entry = join_waitlist(user=second, trip=trip)
            cancel_booking(user=owner, booking_id=booking.id)
            first_entry.refresh_from_db()
            second_entry.refresh_from_db()
            if (first_entry.status != WaitlistEntry.Status.OFFERED
                    or second_entry.status != WaitlistEntry.Status.WAITING):
                raise CommandError("The temporary queue was not created as expected.")
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT status, queue_position FROM v_waitlist_queue "
                    "WHERE trip_id = %s ORDER BY queue_position", [trip.id]
                )
                positions = cursor.fetchall()
            if positions != [("OFFERED", 1), ("WAITING", 2)]:
                raise CommandError(f"Unexpected Oracle queue positions: {positions}")
            self.stdout.write(self.style.SUCCESS(
                f"Preview trip #{trip.id}: 1 waiting passenger and 1 open offer."
            ))
            self.stdout.write("Open http://127.0.0.1:8000/insights/ as staff and refresh the page.")
            self.stdout.write("The offer lasts 10 minutes. Capture the chart before it expires.")
            input("Press Enter here to remove the temporary preview data... ")
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
            self.stdout.write("Temporary queue preview data removed.")
