"""Keep active waiting-list offers complete and unique by seat."""
from django.db import migrations, models


OFFER_INDEX = """
CREATE UNIQUE INDEX uq_active_offer_seat
ON booking_waitlistentry (
    CASE WHEN status = 'OFFERED' THEN offered_seat_id END
)
"""


class Migration(migrations.Migration):
    dependencies = [("booking", "0007_recompile_booking_audit")]
    operations = [
        migrations.AddConstraint(
            model_name="waitlistentry",
            constraint=models.CheckConstraint(
                condition=~models.Q(status="OFFERED") | (
                    models.Q(offered_seat__isnull=False)
                    & models.Q(offer_expires_at__isnull=False)
                ),
                name="ck_offer_complete",
            ),
        ),
        migrations.AddConstraint(
            model_name="waitlistentry",
            constraint=models.CheckConstraint(
                condition=~models.Q(status="WAITING") | (
                    models.Q(offered_seat__isnull=True)
                    & models.Q(offer_expires_at__isnull=True)
                ),
                name="ck_waiting_no_offer",
            ),
        ),
        migrations.RunSQL(
            sql=OFFER_INDEX,
            reverse_sql="DROP INDEX uq_active_offer_seat",
        ),
    ]
