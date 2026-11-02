"""Exercise Oracle's bus schedule guard without changing project data."""
from datetime import timedelta
from uuid import uuid4

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection, transaction
from django.utils import timezone

from booking.models import Bus, Trip


class Command(BaseCommand):
    help = "Verify overlapping trips are rejected, while adjacent and other-bus trips work."

    def handle(self, *args, **options):
        if connection.vendor != "oracle":
            raise CommandError("This verification requires Oracle.")
        marker = uuid4().hex[:10].upper()
        departure = timezone.now() + timedelta(days=5)
        with transaction.atomic():
            first_bus = Bus.objects.create(
                registration_number=f"SCH{marker}", operator_name="Schedule test", bus_type="Test"
            )
            second_bus = Bus.objects.create(
                registration_number=f"SCB{marker}", operator_name="Schedule test", bus_type="Test"
            )
            Trip.objects.create(
                bus=first_bus, origin="A", destination="B",
                departure_at=departure, arrival_at=departure + timedelta(hours=3), fare=100,
            )
            try:
                with transaction.atomic():
                    Trip.objects.create(
                        bus=first_bus, origin="C", destination="D",
                        departure_at=departure + timedelta(hours=1),
                        arrival_at=departure + timedelta(hours=4), fare=100,
                    )
            except DatabaseError as error:
                if "ORA-20011" not in str(error):
                    raise CommandError(f"Unexpected Oracle error: {error}") from error
            else:
                raise CommandError("Oracle accepted overlapping trips for one bus.")
            self.stdout.write(self.style.SUCCESS("PASS: Oracle rejected an overlapping trip."))
            Trip.objects.create(
                bus=first_bus, origin="B", destination="A",
                departure_at=departure + timedelta(hours=3),
                arrival_at=departure + timedelta(hours=6), fare=100,
            )
            Trip.objects.create(
                bus=second_bus, origin="C", destination="D",
                departure_at=departure + timedelta(hours=1),
                arrival_at=departure + timedelta(hours=4), fare=100,
            )
            self.stdout.write(self.style.SUCCESS("PASS: adjacent and different-bus trips worked."))
            transaction.set_rollback(True)
        if Bus.objects.filter(registration_number=f"SCH{marker}").exists():
            raise CommandError("Schedule verification rows were not rolled back.")
        self.stdout.write("Schedule test data rolled back.")
