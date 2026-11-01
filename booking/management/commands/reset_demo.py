"""Clear project data and passenger accounts while keeping the database schema."""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction

from booking.models import Booking, Bus, Payment, Seat, Trip, TripSeat, WaitlistEntry


class Command(BaseCommand):
    help = "Delete all booking data and non-staff test accounts; preserve schema and admin users."

    @transaction.atomic
    def handle(self, *args, **options):
        counts = {
            "payments": Payment.objects.count(),
            "waiting entries": WaitlistEntry.objects.count(),
            "seat inventory": TripSeat.objects.count(),
            "bookings": Booking.objects.count(),
            "trips": Trip.objects.count(),
            "seats": Seat.objects.count(),
            "buses": Bus.objects.count(),
        }
        Payment.objects.all().delete()
        WaitlistEntry.objects.all().delete()
        TripSeat.objects.all().delete()
        Booking.objects.all().delete()
        Trip.objects.all().delete()
        Seat.objects.all().delete()
        Bus.objects.all().delete()
        passengers = get_user_model().objects.filter(is_staff=False, is_superuser=False)
        counts["passenger accounts"] = passengers.count()
        passengers.delete()
        for label, count in counts.items():
            self.stdout.write(f"Deleted {count} {label}.")
        self.stdout.write(self.style.SUCCESS("Project data cleared. Database tables and admin accounts remain."))
