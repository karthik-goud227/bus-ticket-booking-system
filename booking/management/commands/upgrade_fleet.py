"""Expand all current buses without deleting seats, bookings, or trip history."""
from django.core.management.base import BaseCommand
from django.db import transaction

from booking.management.commands.seed_fleet import FLEET, LAYOUTS
from booking.models import Bus, Seat, TripSeat


class Command(BaseCommand):
    help = "Upgrade existing buses to at least 24 seats and sync every trip's inventory."

    @transaction.atomic
    def handle(self, *args, **options):
        added_seats = added_inventory = 0
        for bus in Bus.objects.all():
            capacity = next((item[3] for item in FLEET if item[0] == bus.registration_number), 24)
            columns, upper, kind = LAYOUTS.get(bus.registration_number, (4, False, "SEAT"))
            bus.seats_per_row, bus.has_upper_deck = columns, upper
            if bus.registration_number == "DEMO-SLP-02":
                bus.bus_type = "AC Sleeper Double Decker"
            elif bus.registration_number == "DEMO-COACH-05":
                bus.bus_type = "Luxury Double Decker"
            elif bus.registration_number == "DEMO-PREM-11":
                bus.bus_type = "Premium Sleeper Double Decker"
            bus.save(update_fields=["seats_per_row", "has_upper_deck", "bus_type"])
            split = capacity // 2 if upper else capacity
            for number in range(1, capacity + 1):
                deck = "UPPER" if number > split else "LOWER"
                seat_type = "BED" if kind == "BED" or (kind == "MIXED" and deck == "UPPER") else "STANDARD"
                seat, created = Seat.objects.get_or_create(
                    bus=bus, number=str(number), defaults={"deck": deck, "seat_type": seat_type},
                )
                added_seats += created
                if seat.deck != deck or seat.seat_type != seat_type:
                    seat.deck, seat.seat_type = deck, seat_type
                    seat.save(update_fields=["deck", "seat_type"])
            seats = list(bus.seats.all())
            for trip in bus.trips.all():
                existing = set(TripSeat.objects.filter(trip=trip).values_list("seat_id", flat=True))
                missing = [TripSeat(trip=trip, seat=seat) for seat in seats if seat.id not in existing]
                TripSeat.objects.bulk_create(missing)
                added_inventory += len(missing)
        self.stdout.write(self.style.SUCCESS(
            f"Expanded {Bus.objects.count()} buses; added {added_seats} physical seats and {added_inventory} trip-seat rows. Existing bookings kept."
        ))
