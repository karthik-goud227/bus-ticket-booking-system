from decimal import Decimal

from django.db import migrations, models
from django.db.models import Q
from django.db.models.functions import Round


class Migration(migrations.Migration):
    dependencies = [("booking", "0015_bill_integrity")]

    operations = [
        migrations.AddField(
            model_name="booking",
            name="fare_policy_version",
            field=models.PositiveSmallIntegerField(default=1, editable=False),
        ),
        migrations.AddConstraint(
            model_name="booking",
            constraint=models.CheckConstraint(
                condition=Q(fare_policy_version=1) | (
                    Q(fare_policy_version=2, platform_fee=20)
                    & Q(service_fee=Round(models.F("base_fare") * models.Value(Decimal("0.02")), precision=2))
                    & Q(gst_amount=Round((models.F("platform_fee") + models.F("service_fee")) * models.Value(Decimal("0.18")), precision=2))
                ),
                name="ck_bill_policy_versioned",
            ),
        ),
    ]
