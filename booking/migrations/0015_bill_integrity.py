from django.db import migrations, models
from django.db.models import F, Q


class Migration(migrations.Migration):
    dependencies = [("booking", "0014_account_profile")]
    operations = [
        migrations.AddConstraint(model_name="booking", constraint=models.CheckConstraint(
            condition=Q(base_fare__gte=0, platform_fee__gte=0, service_fee__gte=0, gst_amount__gte=0),
            name="ck_bill_parts_nonnegative")),
        migrations.AddConstraint(model_name="booking", constraint=models.CheckConstraint(
            condition=Q(total_fare=F("base_fare") + F("platform_fee") + F("service_fee") + F("gst_amount")),
            name="ck_bill_total_matches_parts")),
    ]
