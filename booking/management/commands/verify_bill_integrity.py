"""Prove Oracle rejects a booking whose total differs from its stored parts."""
from decimal import Decimal

from django.core.management.base import BaseCommand, CommandError
from django.db import IntegrityError, transaction
from django.db.models import F

from booking.models import Booking


class Command(BaseCommand):
    help = "Check saved fare arithmetic and probe Oracle's bill total constraint."

    def handle(self, *args, **options):
        booking = Booking.objects.order_by("id").first()
        if booking is None:
            raise CommandError("Create a booking first, then rerun this verification.")
        mismatches = [row.id for row in Booking.objects.all() if row.total_fare != row.base_fare + row.platform_fee + row.service_fee + row.gst_amount]
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
        self.stdout.write(self.style.SUCCESS(
            f"PASS: all {Booking.objects.count()} bills balance; Oracle rejected an invalid total (ORA-02290). No booking was changed."
        ))
