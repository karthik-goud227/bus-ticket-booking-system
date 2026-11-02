"""Verify Oracle's active seat-offer uniqueness and queue-state checks."""
from datetime import timedelta
from uuid import uuid4

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, connection, transaction
from django.utils import timezone

from booking.models import Bus, Seat, Trip, TripSeat, WaitlistEntry


def expect_oracle_error(code, action):
    try:
        with transaction.atomic():
            action()
    except IntegrityError as error:
        if code not in str(error):
            raise
    else:
        raise CommandError(f"Oracle did not reject invalid data with {code}.")


class Command(BaseCommand):
    help = "Verify one active offer per seat and complete active queue states."

    def handle(self, *args, **options):
        if connection.vendor != "oracle":
            raise CommandError("This verification requires Oracle.")

        marker = uuid4().hex[:10].lower()
        first_name = f"offer_a_{marker}"
        second_name = f"offer_b_{marker}"
        with transaction.atomic():
            first_user = get_user_model().objects.create_user(
                username=first_name, password=uuid4().hex
            )
            second_user = get_user_model().objects.create_user(
                username=second_name, password=uuid4().hex
            )
            bus = Bus.objects.create(
                registration_number=f"OF{marker.upper()}",
                operator_name="Offer rule test", bus_type="Test",
            )
            seat = Seat.objects.create(bus=bus, number="A1")
            departure = timezone.now() + timedelta(days=3)
            trip = Trip.objects.create(
                bus=bus, origin="Offer Test A", destination="Offer Test B",
                departure_at=departure,
                arrival_at=departure + timedelta(hours=2), fare=100,
            )
            inventory = TripSeat.objects.create(trip=trip, seat=seat)
            deadline = timezone.now() + timedelta(minutes=10)
            first_offer = WaitlistEntry.objects.create(
                user=first_user, trip=trip, status=WaitlistEntry.Status.OFFERED,
                offered_seat=inventory, offer_expires_at=deadline,
            )

            expect_oracle_error("ORA-00001", lambda: WaitlistEntry.objects.create(
                user=second_user, trip=trip, status=WaitlistEntry.Status.OFFERED,
                offered_seat=inventory, offer_expires_at=deadline,
            ))
            self.stdout.write(self.style.SUCCESS(
                "PASS: Oracle rejected a second active offer for the same seat."
            ))

            expect_oracle_error("ORA-02290", lambda: WaitlistEntry.objects.create(
                user=second_user, trip=trip, status=WaitlistEntry.Status.OFFERED,
            ))
            expect_oracle_error("ORA-02290", lambda: WaitlistEntry.objects.create(
                user=second_user, trip=trip, status=WaitlistEntry.Status.WAITING,
                offered_seat=inventory, offer_expires_at=deadline,
            ))
            self.stdout.write(self.style.SUCCESS(
                "PASS: Oracle rejected incomplete OFFERED and invalid WAITING rows."
            ))

            first_offer.status = WaitlistEntry.Status.CANCELLED
            first_offer.offered_seat = None
            first_offer.offer_expires_at = None
            first_offer.save(update_fields=["status", "offered_seat", "offer_expires_at"])
            WaitlistEntry.objects.create(
                user=second_user, trip=trip, status=WaitlistEntry.Status.OFFERED,
                offered_seat=inventory, offer_expires_at=deadline,
            )
            self.stdout.write(self.style.SUCCESS(
                "PASS: the seat could be offered to the next passenger after cancellation."
            ))
            transaction.set_rollback(True)

        if get_user_model().objects.filter(username__in=[first_name, second_name]).exists():
            raise CommandError("Offer verification rows were not rolled back.")
        self.stdout.write("Offer-rule test rows rolled back; project data is unchanged.")
