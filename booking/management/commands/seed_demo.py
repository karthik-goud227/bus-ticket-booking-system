"""Create a small, repeatable sample trip for the local demo."""
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from booking.models import Bus, Seat, Trip, TripSeat


class Command(BaseCommand):
    help = "Create a bus, twelve seats, and one upcoming demo trip."

    @transaction.atomic
    def handle(self, *args, **options):
        bus, _ = Bus.objects.update_or_create(
            registration_number="DEMO-101",
            defaults={"operator_name": "Campus Express", "bus_type": "AC Seater", "is_active": True},
        )
        seats = []
        for number in range(1, 13):
            seat, _ = Seat.objects.get_or_create(bus=bus, number=f"A{number:02d}")
            seats.append(seat)
        departure = timezone.now().replace(minute=0, second=0, microsecond=0) + timedelta(days=1)
        trip, _ = Trip.objects.get_or_create(
            bus=bus, departure_at=departure,
            defaults={
                "origin": "Hyderabad", "destination": "Bengaluru",
                "arrival_at": departure + timedelta(hours=9), "fare": 799,
            },
        )
        for seat in seats:
            TripSeat.objects.get_or_create(trip=trip, seat=seat)
        wait_bus, _ = Bus.objects.update_or_create(
            registration_number="DEMO-WAIT-1",
            defaults={"operator_name": "Campus Express", "bus_type": "Mini Seater", "is_active": True},
        )
        wait_seat, _ = Seat.objects.get_or_create(bus=wait_bus, number="W01")
        wait_trip, _ = Trip.objects.get_or_create(
            bus=wait_bus, departure_at=departure + timedelta(hours=2),
            defaults={
                "origin": "Hyderabad", "destination": "Chennai",
                "arrival_at": departure + timedelta(hours=11), "fare": 499,
            },
        )
        TripSeat.objects.get_or_create(trip=wait_trip, seat=wait_seat)
        self.stdout.write(self.style.SUCCESS(
            f"Demo trips: {trip.id} Hyderabad–Bengaluru (12 seats); "
            f"{wait_trip.id} Hyderabad–Chennai (1 seat for waiting-list test)."
        ))
