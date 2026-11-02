from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [("booking", "0011_login_event")]

    operations = [
        migrations.AddField(model_name="bus", name="seats_per_row", field=models.PositiveSmallIntegerField(default=4, choices=[(3, "Three seats"), (4, "Four seats")])),
        migrations.AddField(model_name="bus", name="has_upper_deck", field=models.BooleanField(default=False)),
        migrations.AddField(model_name="seat", name="deck", field=models.CharField(max_length=5, default="LOWER", choices=[("LOWER", "Lower"), ("UPPER", "Upper")])),
        migrations.AddField(model_name="booking", name="passenger_name", field=models.CharField(max_length=100, blank=True)),
        migrations.AddField(model_name="booking", name="passenger_phone", field=models.CharField(max_length=20, blank=True)),
        migrations.CreateModel(
            name="RecurringTrip",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("origin", models.CharField(max_length=100)),
                ("destination", models.CharField(max_length=100)),
                ("departure_time", models.TimeField()),
                ("duration_minutes", models.PositiveIntegerField()),
                ("fare", models.DecimalField(max_digits=10, decimal_places=2)),
                ("is_active", models.BooleanField(default=True)),
                ("bus", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="daily_schedules", to="booking.bus")),
            ],
        ),
        migrations.AddField(
            model_name="trip", name="schedule",
            field=models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, related_name="generated_trips", to="booking.recurringtrip", null=True, blank=True),
        ),
        migrations.AddConstraint(model_name="recurringtrip", constraint=models.UniqueConstraint(fields=["bus", "departure_time"], name="uq_daily_bus_time")),
        migrations.AddConstraint(model_name="recurringtrip", constraint=models.CheckConstraint(condition=Q(duration_minutes__gt=0), name="ck_daily_duration")),
        migrations.AddConstraint(model_name="recurringtrip", constraint=models.CheckConstraint(condition=Q(fare__gte=0), name="ck_daily_fare")),
        migrations.AddConstraint(model_name="recurringtrip", constraint=models.CheckConstraint(condition=~Q(origin=models.F("destination")), name="ck_daily_route")),
    ]
