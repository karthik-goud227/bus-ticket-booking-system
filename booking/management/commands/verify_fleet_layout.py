"""Read-only verification for expanded fleet and per-trip inventory."""
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Count, F

from booking.models import Bus, Seat, Trip, TripSeat


class Command(BaseCommand):
    help = "Verify capacity, deck assignment, berth types, and trip-seat inventory."

    def handle(self, *args, **options):
        buses = list(Bus.objects.annotate(capacity=Count("seats")))
        small = [bus.registration_number for bus in buses if bus.capacity < 24]
        bad_decks = Seat.objects.filter(deck="UPPER", bus__has_upper_deck=False).count()
        mismatched = TripSeat.objects.exclude(seat__bus_id=F("trip__bus_id")).count()
        incomplete = []
        for trip in Trip.objects.select_related("bus"):
            if trip.inventory.count() != trip.bus.seats.count():
                incomplete.append(trip.id)
        if small or bad_decks or mismatched or incomplete:
            raise CommandError(
                f"Small buses: {small}; upper seats on single-deck buses: {bad_decks}; "
                f"wrong-bus inventory: {mismatched}; incomplete trips: {incomplete}"
            )
        self.stdout.write(self.style.SUCCESS(
            f"PASS: {len(buses)} buses have 24+ seats; {Trip.objects.count()} trips have complete inventory. "
            f"{Bus.objects.filter(has_upper_deck=True).count()} double-decker buses; "
            f"{Seat.objects.filter(seat_type='BED').count()} berths."
        ))
