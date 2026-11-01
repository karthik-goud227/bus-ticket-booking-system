"""Core relational model. Seat inventory is one row per seat per trip."""
from django.conf import settings
from django.db import models
from django.db.models import Q


class Bus(models.Model):
    registration_number = models.CharField(max_length=20, unique=True)
    operator_name = models.CharField(max_length=100)
    bus_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.registration_number


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seats")
    number = models.CharField(max_length=8)
    seat_type = models.CharField(max_length=20, default="STANDARD")

    class Meta:
        constraints = [models.UniqueConstraint(fields=["bus", "number"], name="uq_seat_bus_number")]

    def __str__(self):
        return f"{self.bus.registration_number} / {self.number}"


class Trip(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name="trips")
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_at = models.DateTimeField()
    arrival_at = models.DateTimeField()
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    is_cancelled = models.BooleanField(default=False)

    class Meta:
        indexes = [models.Index(fields=["origin", "destination", "departure_at"], name="idx_trip_search")]
        constraints = [
            models.CheckConstraint(condition=Q(arrival_at__gt=models.F("departure_at")), name="ck_trip_times"),
            models.CheckConstraint(condition=Q(fare__gte=0), name="ck_trip_fare"),
            models.CheckConstraint(condition=~Q(origin=models.F("destination")), name="ck_trip_route"),
        ]

    def __str__(self):
        return f"{self.origin} → {self.destination} ({self.departure_at:%Y-%m-%d %H:%M})"


class Booking(models.Model):
    class Status(models.TextChoices):
        HELD = "HELD", "Held"
        CONFIRMED = "CONFIRMED", "Confirmed"
        CANCELLED = "CANCELLED", "Cancelled"
        EXPIRED = "EXPIRED", "Expired"

    reference = models.CharField(max_length=20, unique=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="bookings")
    trip = models.ForeignKey(Trip, on_delete=models.PROTECT, related_name="bookings")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.HELD)
    total_fare = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    hold_expires_at = models.DateTimeField(null=True, blank=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"], name="idx_booking_user_created")]
        constraints = [
            models.CheckConstraint(condition=Q(total_fare__gte=0), name="ck_booking_fare"),
            models.CheckConstraint(condition=Q(status__in=["HELD", "CONFIRMED", "CANCELLED", "EXPIRED"]), name="ck_booking_status"),
        ]


class TripSeat(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "AVAILABLE", "Available"
        HELD = "HELD", "Held"
        BOOKED = "BOOKED", "Booked"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="inventory")
    seat = models.ForeignKey(Seat, on_delete=models.PROTECT, related_name="trip_inventory")
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.AVAILABLE)
    booking = models.ForeignKey(Booking, on_delete=models.PROTECT, null=True, blank=True, related_name="allocated_seats")
    hold_expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["trip", "seat"], name="uq_trip_seat"),
            models.CheckConstraint(condition=Q(status__in=["AVAILABLE", "HELD", "BOOKED"]), name="ck_inventory_status"),
            models.CheckConstraint(
                condition=(Q(status="AVAILABLE", booking__isnull=True, hold_expires_at__isnull=True)
                           | Q(status="HELD", booking__isnull=False, hold_expires_at__isnull=False)
                           | Q(status="BOOKED", booking__isnull=False, hold_expires_at__isnull=True)),
                name="ck_inventory_state",
            ),
        ]


class WaitlistEntry(models.Model):
    class Status(models.TextChoices):
        WAITING = "WAITING", "Waiting"
        OFFERED = "OFFERED", "Offered"
        ACCEPTED = "ACCEPTED", "Accepted"
        EXPIRED = "EXPIRED", "Expired"
        CANCELLED = "CANCELLED", "Cancelled"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="waitlist")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="waitlist_entries")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.WAITING)
    joined_at = models.DateTimeField(auto_now_add=True)
    offer_expires_at = models.DateTimeField(null=True, blank=True)
    offered_seat = models.ForeignKey(TripSeat, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["trip", "status", "joined_at", "id"], name="idx_waitlist_fifo")]
        constraints = [models.CheckConstraint(condition=Q(status__in=["WAITING", "OFFERED", "ACCEPTED", "EXPIRED", "CANCELLED"]), name="ck_waitlist_status")]
