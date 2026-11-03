from django.conf import settings
from django.db import migrations, models
from django.db.models import Q
import django.db.models.deletion


def seed_points(apps, schema_editor):
    Trip = apps.get_model("booking", "Trip")
    Point = apps.get_model("booking", "TripPoint")
    Booking = apps.get_model("booking", "Booking")
    for trip in Trip.objects.all().iterator():
        Point.objects.get_or_create(trip_id=trip.id, kind="BOARDING", name=f"{trip.origin} Bus Stand", defaults={"scheduled_at": trip.departure_at})
        Point.objects.get_or_create(trip_id=trip.id, kind="DROPOFF", name=f"{trip.destination} Bus Stand", defaults={"scheduled_at": trip.arrival_at})
    for booking in Booking.objects.filter(base_fare=0).iterator():
        booking.base_fare = booking.total_fare
        booking.boarding_point = Point.objects.filter(trip_id=booking.trip_id, kind="BOARDING").first()
        booking.dropoff_point = Point.objects.filter(trip_id=booking.trip_id, kind="DROPOFF").first()
        booking.save(update_fields=["base_fare", "boarding_point", "dropoff_point"])


class Migration(migrations.Migration):
    dependencies = [("booking", "0012_fleet_layout_and_passengers"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="TripPoint", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("kind", models.CharField(max_length=8, choices=[("BOARDING", "Boarding"), ("DROPOFF", "Drop-off")])),
            ("name", models.CharField(max_length=120)),
            ("scheduled_at", models.DateTimeField()),
            ("trip", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="points", to="booking.trip")),
        ]),
        migrations.AddConstraint(model_name="trippoint", constraint=models.UniqueConstraint(fields=["trip", "kind", "name"], name="uq_trip_point")),
        migrations.AddField(model_name="booking", name="boarding_point", field=models.ForeignKey(to="booking.trippoint", related_name="boardings", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        migrations.AddField(model_name="booking", name="dropoff_point", field=models.ForeignKey(to="booking.trippoint", related_name="dropoffs", on_delete=django.db.models.deletion.PROTECT, null=True, blank=True)),
        migrations.AddField(model_name="booking", name="base_fare", field=models.DecimalField(max_digits=10, decimal_places=2, default=0)),
        migrations.AddField(model_name="booking", name="platform_fee", field=models.DecimalField(max_digits=10, decimal_places=2, default=0)),
        migrations.AddField(model_name="booking", name="service_fee", field=models.DecimalField(max_digits=10, decimal_places=2, default=0)),
        migrations.AddField(model_name="booking", name="gst_amount", field=models.DecimalField(max_digits=10, decimal_places=2, default=0)),
        migrations.CreateModel(name="BusReview", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("rating", models.PositiveSmallIntegerField()),
            ("comment", models.CharField(max_length=500, blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("booking", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="review", to="booking.booking")),
            ("bus", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="reviews", to="booking.bus")),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="bus_reviews", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.AddConstraint(model_name="busreview", constraint=models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="ck_review_rating")),
        migrations.CreateModel(name="SupportRequest", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("subject", models.CharField(max_length=120)),
            ("message", models.TextField(max_length=2000)),
            ("status", models.CharField(max_length=12, choices=[("OPEN", "Open"), ("IN_PROGRESS", "In progress"), ("RESOLVED", "Resolved")], default="OPEN")),
            ("staff_response", models.TextField(blank=True)),
            ("created_at", models.DateTimeField(auto_now_add=True)),
            ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="support_requests", to=settings.AUTH_USER_MODEL)),
            ("booking", models.ForeignKey(on_delete=django.db.models.deletion.SET_NULL, to="booking.booking", null=True, blank=True)),
        ]),
        migrations.RunPython(seed_points, migrations.RunPython.noop),
    ]
