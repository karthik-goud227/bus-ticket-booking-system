"""Prove Oracle rejects a booking whose total differs from its stored parts."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import F

from booking.models import Booking
from booking.services import fare_breakdown


class Command(BaseCommand):
    help = "Check saved fare arithmetic and probe Oracle's bill total constraint."

    def handle(self, *args, **options):
        booking = Booking.objects.order_by("id").first()
        if booking is None:
            raise CommandError("Create a booking first, then rerun this verification.")
        mismatches = []
        for row in Booking.objects.all():
            if row.total_fare != row.base_fare + row.platform_fee + row.service_fee + row.gst_amount:
                mismatches.append(row.id)
            elif row.fare_policy_version == 2:
                expected = fare_breakdown(row.base_fare, 1)
                if (row.platform_fee, row.service_fee, row.gst_amount) != (
                    expected["platform"], expected["service"], expected["gst"]
                ):
                    mismatches.append(row.id)
        if mismatches:
            raise CommandError(f"Stored bill mismatch on booking IDs: {mismatches}")
        rejected = False
        with transaction.atomic():
            try:
                with transaction.atomic():
                    Booking.objects.filter(pk=booking.pk).update(total_fare=F("total_fare") + Decimal("0.01"))
            except IntegrityError as error:
                rejected = "ORA-02290" in str(error)
            if not rejected:
                raise CommandError("Oracle did not reject the mismatched bill total.")
        expected = fare_breakdown(booking.base_fare, 1)
        policy_rejected = False
        with transaction.atomic():
            Booking.objects.filter(pk=booking.pk).update(
                fare_policy_version=2, platform_fee=expected["platform"],
                service_fee=expected["service"], gst_amount=expected["gst"],
                total_fare=expected["total"],
            )
            try:
                with transaction.atomic():
                    Booking.objects.filter(pk=booking.pk).update(
                        service_fee=F("service_fee") + Decimal("0.01"),
                        total_fare=F("total_fare") + Decimal("0.01"),
                    )
            except IntegrityError as error:
                policy_rejected = "ORA-02290" in str(error)
            if not policy_rejected:
                raise CommandError("Oracle did not reject the incorrect dynamic service fee.")
            transaction.set_rollback(True)
        self.stdout.write(self.style.SUCCESS(
            f"PASS: all {Booking.objects.count()} bills balance; Oracle rejected an invalid total and an incorrect dynamic service fee (ORA-02290). No booking was changed."
        ))
