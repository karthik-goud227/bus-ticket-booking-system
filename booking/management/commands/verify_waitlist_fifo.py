"""Verify two-person FIFO offers and expiry without touching demo data."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from booking.models import Booking, Bus, Payment, Seat, Trip, TripSeat, WaitlistEntry
from booking.services import cancel_booking, confirm_booking, hold_seats, join_waitlist, refresh_trip


class Command(BaseCommand):
    help = "Verify first-in-first-out offer order and promotion after offer expiry."

    def handle(self, *args, **options):
        marker = uuid4().hex[:10].upper()
        users = []
        bus = trip = None
        try:
            for suffix in ("owner", "first", "second"):
                users.append(get_user_model().objects.create(username=f"fifo_{suffix}_{marker.lower()}"))
            owner, first, second = users
            bus = Bus.objects.create(
                registration_number=f"FIFO{marker}", operator_name="Queue test", bus_type="Test"
            )
            seat = Seat.objects.create(bus=bus, number="Q1")
            departure = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Queue A", destination="Queue B",
                departure_at=departure, arrival_at=departure + timedelta(hours=2), fare=100,
            )
            inventory = TripSeat.objects.create(trip=trip, seat=seat)
            owner_booking = hold_seats(user=owner, trip=trip, seat_ids=[inventory.id])
            confirm_booking(user=owner, booking_id=owner_booking.id)

            first_entry = join_waitlist(user=first, trip=trip)
            second_entry = join_waitlist(user=second, trip=trip)
            cancel_booking(user=owner, booking_id=owner_booking.id)
            first_entry.refresh_from_db()
            second_entry.refresh_from_db()
            if (first_entry.status != WaitlistEntry.Status.OFFERED
                    or first_entry.offered_seat_id != inventory.id
                    or second_entry.status != WaitlistEntry.Status.WAITING):
                raise CommandError("Cancellation did not offer the seat to the first passenger only.")
            self.stdout.write(self.style.SUCCESS("PASS: first passenger received the cancelled seat."))

            WaitlistEntry.objects.filter(id=first_entry.id).update(
                offer_expires_at=timezone.now() - timedelta(seconds=1)
            )
            refresh_trip(trip.id)
            first_entry.refresh_from_db()
            second_entry.refresh_from_db()
            if (first_entry.status != WaitlistEntry.Status.EXPIRED
                    or second_entry.status != WaitlistEntry.Status.OFFERED
                    or second_entry.offered_seat_id != inventory.id):
                raise CommandError("Expired offer was not passed to the second passenger.")
            self.stdout.write(self.style.SUCCESS("PASS: expired offer moved to the second passenger."))

            second_booking = hold_seats(
                user=second, trip=trip, seat_ids=[inventory.id], waitlist_entry=second_entry
            )
            confirm_booking(user=second, booking_id=second_booking.id)
            second_entry.refresh_from_db()
            inventory.refresh_from_db()
            if (second_entry.status != WaitlistEntry.Status.ACCEPTED
                    or inventory.status != TripSeat.Status.BOOKED
                    or inventory.booking_id != second_booking.id):
                raise CommandError("Second passenger did not finish the offered booking.")
            self.stdout.write(self.style.SUCCESS("PASS: second passenger accepted and confirmed the seat."))
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
            self.stdout.write("FIFO test data removed.")
