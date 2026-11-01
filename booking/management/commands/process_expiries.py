"""Release expired holds and pass expired offers to the next waiting passenger."""
from django.core.management.base import BaseCommand
from django.utils import timezone

from booking.models import Booking, WaitlistEntry
from booking.services import refresh_trip


class Command(BaseCommand):
    help = "Process expired seat holds and waiting-list offers. Safe to repeat."

    def handle(self, *args, **options):
        now = timezone.now()
        held_trip_ids = Booking.objects.filter(
            status=Booking.Status.HELD, hold_expires_at__lte=now
        ).values_list("trip_id", flat=True)
        offer_trip_ids = WaitlistEntry.objects.filter(
            status=WaitlistEntry.Status.OFFERED, offer_expires_at__lte=now
        ).values_list("trip_id", flat=True)
        trip_ids = sorted(set(held_trip_ids) | set(offer_trip_ids))
        for trip_id in trip_ids:
            refresh_trip(trip_id)
        self.stdout.write(self.style.SUCCESS(f"Processed {len(trip_ids)} trip(s)."))
