"""Prove Oracle rejects duplicate active queue entries and permits rejoining."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from booking.models import Bus, Trip, WaitlistEntry


class Command(BaseCommand):
    help = "Verify Oracle's conditional unique index for active waiting-list entries."

    def handle(self, *args, **options):
        if connection.vendor != "oracle":
            raise CommandError("This verification requires Oracle.")

        marker = uuid4().hex[:10].lower()
        username = f"queue_unique_{marker}"
        with transaction.atomic():
            user = get_user_model().objects.create_user(
                username=username, password=uuid4().hex
            )
            bus = Bus.objects.create(
                registration_number=f"QU{marker.upper()}",
                operator_name="Uniqueness test", bus_type="Test",
            )
            departure = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Queue Test A", destination="Queue Test B",
                departure_at=departure,
                arrival_at=departure + timedelta(hours=2), fare=100,
            )
            first = WaitlistEntry.objects.create(user=user, trip=trip)

            try:
                with transaction.atomic():
                    WaitlistEntry.objects.create(user=user, trip=trip)
            except IntegrityError as error:
                if "ORA-00001" not in str(error):
                    raise
            else:
                raise CommandError("Oracle allowed two active entries for one passenger and trip.")

            first.status = WaitlistEntry.Status.CANCELLED
            first.save(update_fields=["status"])
            second = WaitlistEntry.objects.create(user=user, trip=trip)
            if (WaitlistEntry.objects.filter(
                user=user, trip=trip,
                status__in=[WaitlistEntry.Status.WAITING, WaitlistEntry.Status.OFFERED],
            ).count() != 1 or second.status != WaitlistEntry.Status.WAITING):
                raise CommandError("Rejoining after cancellation did not work.")

            self.stdout.write(self.style.SUCCESS(
                "PASS: Oracle rejected a duplicate active waiting-list entry (ORA-00001)."
            ))
            self.stdout.write(self.style.SUCCESS(
                "PASS: the passenger could rejoin after leaving the queue."
            ))
            transaction.set_rollback(True)

        if get_user_model().objects.filter(username=username).exists():
            raise CommandError("Verification rows were not rolled back.")
        self.stdout.write("Verification rows rolled back; project data is unchanged.")
