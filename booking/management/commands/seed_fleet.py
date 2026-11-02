"""Populate a varied, repeatable future schedule without clearing user data."""
from datetime import datetime, time, timedelta

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from booking.models import Bus, Seat, Trip, TripSeat


FLEET = (
    ("DEMO-AC-01", "Deccan Travels", "AC Seater", 32,
     (("Hyderabad", "Kurnool", 8, 4, 499), ("Kurnool", "Hyderabad", 14, 4, 499))),
    ("DEMO-SLP-02", "Night Rider", "AC Sleeper Double Decker", 32,
     (("Hyderabad", "Bengaluru", 21, 9, 1299), ("Bengaluru", "Hyderabad", 8, 9, 1299))),
    ("DEMO-EXP-03", "Rayalaseema Express", "Non-AC Seater", 24,
     (("Kurnool", "Vijayawada", 7, 6, 649), ("Vijayawada", "Kurnool", 16, 6, 649))),
    ("DEMO-MINI-04", "Campus Connect", "Mini Bus", 24,
     (("Kurnool", "Nandyal", 9, 2, 199), ("Nandyal", "Kurnool", 13, 2, 199))),
    ("DEMO-COACH-05", "Southern Trails", "Luxury Double Decker", 40,
     (("Hyderabad", "Tirupati", 20, 11, 1499),
      ("Tirupati", "Chennai", 10, 4, 599),
      ("Chennai", "Hyderabad", 19, 12, 1599))),
    ("DEMO-ELEC-06", "Green Mile", "Electric Seater", 28,
     (("Kurnool", "Anantapur", 8, 4, 449),
      ("Anantapur", "Bengaluru", 9, 5, 699),
      ("Bengaluru", "Kurnool", 7, 9, 999))),
    ("DEMO-SEMI-07", "Krishna Roadways", "Semi Sleeper", 30,
     (("Vijayawada", "Guntur", 7, 2, 249),
      ("Guntur", "Nellore", 9, 5, 649),
      ("Nellore", "Vijayawada", 10, 6, 749))),
    ("DEMO-TOUR-08", "Heritage Wheels", "Tourist Coach", 32,
     (("Bengaluru", "Mysuru", 8, 4, 549),
      ("Mysuru", "Chittoor", 9, 7, 899),
      ("Chittoor", "Bengaluru", 11, 5, 749))),
    ("DEMO-EXP-09", "Telangana Connect", "Express Seater", 24,
     (("Hyderabad", "Warangal", 6, 4, 399),
      ("Warangal", "Karimnagar", 8, 3, 299),
      ("Karimnagar", "Hyderabad", 10, 4, 399))),
    ("DEMO-SLP-10", "Rayalaseema Nights", "Non-AC Sleeper", 30,
     (("Kurnool", "Kadapa", 21, 5, 649),
      ("Kadapa", "Tirupati", 22, 5, 699),
      ("Tirupati", "Kurnool", 20, 8, 899))),
    ("DEMO-PREM-11", "Coastal Star", "Premium Sleeper Double Decker", 36,
     (("Vijayawada", "Visakhapatnam", 21, 8, 1199),
      ("Visakhapatnam", "Rajahmundry", 9, 4, 549),
      ("Rajahmundry", "Vijayawada", 10, 4, 499))),
    ("DEMO-MINI-12", "District Hopper", "Mini Bus", 24,
     (("Kurnool", "Adoni", 7, 3, 299),
      ("Adoni", "Ballari", 8, 3, 349),
      ("Ballari", "Kurnool", 10, 4, 449))),
)

LAYOUTS = {
    "DEMO-SLP-02": (3, True, "BED"),
    "DEMO-COACH-05": (4, True, "SEAT"),
    "DEMO-PREM-11": (3, True, "MIXED"),
    "DEMO-TOUR-08": (3, False, "SEAT"),
    "DEMO-MINI-04": (3, False, "SEAT"),
    "DEMO-MINI-12": (3, False, "SEAT"),
    "DEMO-SLP-10": (3, False, "BED"),
}


class Command(BaseCommand):
    help = "Add a mixed demo fleet and future non-overlapping trips without clearing data."

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
            # Existing buses are expanded below; their booked seat numbers stay unchanged.
            for index, (origin, destination, hour, duration, fare) in enumerate(journeys):
                day = base_day + timedelta(days=index * 2)
                departure = timezone.make_aware(datetime.combine(day, time(hour)))
                trip, created = Trip.objects.get_or_create(
                    bus=bus, departure_at=departure,
                    defaults={"origin": origin, "destination": destination,
                              "arrival_at": departure + timedelta(hours=duration), "fare": fare},
                )
                trip_count += created
        for bus in Bus.objects.all():
            capacity = next((entry[3] for entry in FLEET if entry[0] == bus.registration_number), 24)
            columns, upper, kind = LAYOUTS.get(bus.registration_number, (4, False, "SEAT"))
            bus.seats_per_row, bus.has_upper_deck = columns, upper
            if bus.registration_number in ("DEMO-SLP-02", "DEMO-COACH-05", "DEMO-PREM-11"):
                bus.bus_type = {
                    "DEMO-SLP-02": "AC Sleeper Double Decker",
                    "DEMO-COACH-05": "Luxury Double Decker",
                    "DEMO-PREM-11": "Premium Sleeper Double Decker",
                }[bus.registration_number]
            bus.save(update_fields=["seats_per_row", "has_upper_deck", "bus_type"])
            split = capacity // 2 if upper else capacity
            for number in range(1, capacity + 1):
                deck = "UPPER" if number > split else "LOWER"
                seat_type = "BED" if kind == "BED" or (kind == "MIXED" and deck == "UPPER") else "STANDARD"
                seat, _ = Seat.objects.get_or_create(bus=bus, number=str(number), defaults={"deck": deck, "seat_type": seat_type})
                if seat.deck != deck or seat.seat_type != seat_type:
                    seat.deck, seat.seat_type = deck, seat_type
                    seat.save(update_fields=["deck", "seat_type"])
            for trip in bus.trips.all():
                for seat in bus.seats.all():
                    _, created = TripSeat.objects.get_or_create(trip=trip, seat=seat)
                    seat_count += created
        self.stdout.write(self.style.SUCCESS(
            f"Created {bus_count} buses, {trip_count} trips and {seat_count} trip seats. "
            "Existing bookings were not changed."
        ))
