"""Populate a varied, repeatable future schedule without clearing user data."""
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from booking.models import Bus, Seat, Trip, TripSeat


FLEET = (
    ("DEMO-AC-01", "Deccan Travels", "AC Seater", 20,
     (("Hyderabad", "Kurnool", 8, 4, 499), ("Kurnool", "Hyderabad", 14, 4, 499))),
    ("DEMO-SLP-02", "Night Rider", "AC Sleeper", 16,
     (("Hyderabad", "Bengaluru", 21, 9, 1299), ("Bengaluru", "Hyderabad", 8, 9, 1299))),
    ("DEMO-EXP-03", "Rayalaseema Express", "Non-AC Seater", 24,
     (("Kurnool", "Vijayawada", 7, 6, 649), ("Vijayawada", "Kurnool", 16, 6, 649))),
    ("DEMO-MINI-04", "Campus Connect", "Mini Bus", 12,
     (("Kurnool", "Nandyal", 9, 2, 199), ("Nandyal", "Kurnool", 13, 2, 199))),
)


class Command(BaseCommand):
    help = "Create four demo bus types and eight future non-overlapping trips."

    @transaction.atomic
    def handle(self, *args, **options):
        base_day = timezone.localdate() + timedelta(days=2)
        bus_count = trip_count = seat_count = 0
        for registration, operator, bus_type, capacity, journeys in FLEET:
            bus, created = Bus.objects.get_or_create(
                registration_number=registration,
                defaults={"operator_name": operator, "bus_type": bus_type},
            )
            bus_count += created
            seats = []
            for number in range(1, capacity + 1):
                seat, _ = Seat.objects.get_or_create(bus=bus, number=str(number))
                seats.append(seat)
            for index, (origin, destination, hour, duration, fare) in enumerate(journeys):
                day = base_day + timedelta(days=index * 2)
                departure = timezone.make_aware(datetime.combine(day, time(hour)))
                trip, created = Trip.objects.get_or_create(
                    bus=bus, departure_at=departure,
                    defaults={"origin": origin, "destination": destination,
                              "arrival_at": departure + timedelta(hours=duration), "fare": fare},
                )
                trip_count += created
                for seat in seats:
                    _, created = TripSeat.objects.get_or_create(trip=trip, seat=seat)
                    seat_count += created
        self.stdout.write(self.style.SUCCESS(
            f"Created {bus_count} buses, {trip_count} trips and {seat_count} trip seats. "
            "Existing bookings were not changed."
        ))
