"""Materialize daily templates as ordinary, independently bookable trip rows."""
from datetime import datetime, timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from booking.models import Bus, RecurringTrip, Trip, TripSeat


DEFAULT_ROUTES = (
    ("DEMO-AC-01", "Hyderabad", "Kurnool", "08:00", 240, 499),
    ("DEMO-AC-01", "Kurnool", "Hyderabad", "14:00", 240, 499),
    ("DEMO-MINI-04", "Kurnool", "Nandyal", "09:00", 120, 199),
    ("DEMO-MINI-04", "Nandyal", "Kurnool", "13:00", 120, 199),
    ("DEMO-EXP-09", "Hyderabad", "Warangal", "06:00", 240, 399),
    ("DEMO-EXP-09", "Warangal", "Hyderabad", "12:00", 240, 399),
)


class Command(BaseCommand):
    help = "Create trips for the next N days from active daily schedules, skipping bus conflicts."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=14)

    def handle(self, *args, **options):
        days = options["days"]
        if not 1 <= days <= 31:
            raise CommandError("--days must be between 1 and 31.")
        for registration, origin, destination, departure, duration, fare in DEFAULT_ROUTES:
            bus = Bus.objects.filter(registration_number=registration).first()
            if bus:
                RecurringTrip.objects.get_or_create(
                    bus=bus, origin=origin, destination=destination,
                    departure_time=datetime.strptime(departure, "%H:%M").time(),
                    defaults={"duration_minutes": duration, "fare": fare},
                )
        created = skipped = 0
        today = timezone.localdate()
        for schedule in RecurringTrip.objects.filter(is_active=True, bus__is_active=True).select_related("bus").order_by("bus_id", "departure_time"):
            for offset in range(1, days + 1):
                departure = timezone.make_aware(datetime.combine(today + timedelta(days=offset), schedule.departure_time))
                arrival = departure + timedelta(minutes=schedule.duration_minutes)
                if Trip.objects.filter(bus=schedule.bus, is_cancelled=False,
                                       departure_at__lt=arrival, arrival_at__gt=departure).exists():
                    skipped += 1
                    continue
                with transaction.atomic():
                    trip, added = Trip.objects.get_or_create(
                        bus=schedule.bus, departure_at=departure,
                        defaults={"origin": schedule.origin, "destination": schedule.destination,
                                  "arrival_at": arrival, "fare": schedule.fare, "schedule": schedule},
                    )
                    if added:
                        TripSeat.objects.bulk_create([TripSeat(trip=trip, seat=seat) for seat in schedule.bus.seats.all()])
                        created += 1
        self.stdout.write(self.style.SUCCESS(f"Created {created} trips; skipped {skipped} conflicting or existing slots."))
