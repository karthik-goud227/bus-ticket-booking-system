"""Core relational model. Seat inventory is one row per seat per trip."""
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q


class Bus(models.Model):
    registration_number = models.CharField(max_length=20, unique=True)
    operator_name = models.CharField(max_length=100)
    bus_type = models.CharField(max_length=50)
    is_active = models.BooleanField(default=True)
    seats_per_row = models.PositiveSmallIntegerField(default=4, choices=[(3, "Three seats"), (4, "Four seats")])
    has_upper_deck = models.BooleanField(default=False)

    def __str__(self):
        return self.registration_number


class Seat(models.Model):
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="seats")
    number = models.CharField(max_length=8)
    seat_type = models.CharField(max_length=20, default="STANDARD")
    deck = models.CharField(max_length=5, default="LOWER", choices=[("LOWER", "Lower"), ("UPPER", "Upper")])

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
    schedule = models.ForeignKey("RecurringTrip", on_delete=models.SET_NULL, null=True, blank=True, related_name="generated_trips")

    class Meta:
        indexes = [models.Index(fields=["origin", "destination", "departure_at"], name="idx_trip_search")]
        constraints = [
            models.CheckConstraint(condition=Q(arrival_at__gt=models.F("departure_at")), name="ck_trip_times"),
            models.CheckConstraint(condition=Q(fare__gte=0), name="ck_trip_fare"),
            models.CheckConstraint(condition=~Q(origin=models.F("destination")), name="ck_trip_route"),
        ]

    def __str__(self):
        return f"{self.origin} → {self.destination} ({self.departure_at:%Y-%m-%d %H:%M})"

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        TripPoint.objects.get_or_create(trip=self, kind=TripPoint.Kind.BOARDING, name=f"{self.origin} Bus Stand", defaults={"scheduled_at": self.departure_at})
        TripPoint.objects.get_or_create(trip=self, kind=TripPoint.Kind.DROPOFF, name=f"{self.destination} Bus Stand", defaults={"scheduled_at": self.arrival_at})

    @property
    def duration_label(self):
        minutes = int((self.arrival_at - self.departure_at).total_seconds() // 60)
        hours, remainder = divmod(minutes, 60)
        return f"{hours} hr {remainder} min" if remainder else f"{hours} hr"

    def clean(self):
        super().clean()
        if not self.bus_id or not self.departure_at or not self.arrival_at or self.is_cancelled:
            return
        if self.arrival_at <= self.departure_at:
            raise ValidationError({"arrival_at": "Arrival must be after departure."})
        overlap = Trip.objects.filter(
            bus_id=self.bus_id, is_cancelled=False,
            departure_at__lt=self.arrival_at, arrival_at__gt=self.departure_at,
        )
        if self.pk:
            overlap = overlap.exclude(pk=self.pk)
        if overlap.exists():
            raise ValidationError({"bus": "This bus already has a trip during that time."})


class TripPoint(models.Model):
    class Kind(models.TextChoices):
        BOARDING = "BOARDING", "Boarding"
        DROPOFF = "DROPOFF", "Drop-off"

    trip = models.ForeignKey(Trip, on_delete=models.CASCADE, related_name="points")
    kind = models.CharField(max_length=8, choices=Kind.choices)
    name = models.CharField(max_length=120)
    scheduled_at = models.DateTimeField()

    class Meta:
        constraints = [models.UniqueConstraint(fields=["trip", "kind", "name"], name="uq_trip_point")]

    def __str__(self):
        return f"{self.name} ({self.get_kind_display()})"

    def clean(self):
        super().clean()
        if self.trip_id and self.scheduled_at and not self.trip.departure_at <= self.scheduled_at <= self.trip.arrival_at:
            raise ValidationError({"scheduled_at": "Point time must fall within the trip's schedule."})


class RecurringTrip(models.Model):
    """Daily template; generated Trip rows retain their own seat inventory and booking history."""
    bus = models.ForeignKey(Bus, on_delete=models.PROTECT, related_name="daily_schedules")
    origin = models.CharField(max_length=100)
    destination = models.CharField(max_length=100)
    departure_time = models.TimeField()
    duration_minutes = models.PositiveIntegerField()
    fare = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["bus", "departure_time"], name="uq_daily_bus_time"),
            models.CheckConstraint(condition=Q(duration_minutes__gt=0), name="ck_daily_duration"),
            models.CheckConstraint(condition=Q(fare__gte=0), name="ck_daily_fare"),
            models.CheckConstraint(condition=~Q(origin=models.F("destination")), name="ck_daily_route"),
        ]

    def __str__(self):
        return f"Daily {self.origin} → {self.destination} at {self.departure_time:%H:%M}"


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
    passenger_name = models.CharField(max_length=100, blank=True)
    passenger_phone = models.CharField(max_length=20, blank=True)
    boarding_point = models.ForeignKey(TripPoint, on_delete=models.PROTECT, related_name="boardings", null=True, blank=True)
    dropoff_point = models.ForeignKey(TripPoint, on_delete=models.PROTECT, related_name="dropoffs", null=True, blank=True)
    base_fare = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    platform_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    service_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    gst_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    class Meta:
        indexes = [models.Index(fields=["user", "created_at"], name="idx_booking_user_created")]
        constraints = [
            models.CheckConstraint(condition=Q(total_fare__gte=0), name="ck_booking_fare"),
            models.CheckConstraint(condition=Q(status__in=["HELD", "CONFIRMED", "CANCELLED", "EXPIRED"]), name="ck_booking_status"),
            models.CheckConstraint(condition=Q(base_fare__gte=0, platform_fee__gte=0, service_fee__gte=0, gst_amount__gte=0), name="ck_bill_parts_nonnegative"),
            models.CheckConstraint(condition=Q(total_fare=models.F("base_fare") + models.F("platform_fee") + models.F("service_fee") + models.F("gst_amount")), name="ck_bill_total_matches_parts"),
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
    # Oracle migration 0005 adds a function-based unique index for active rows.
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
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=["WAITING", "OFFERED", "ACCEPTED", "EXPIRED", "CANCELLED"]),
                name="ck_waitlist_status",
            ),
            models.CheckConstraint(
                condition=~Q(status="OFFERED") | (
                    Q(offered_seat__isnull=False) & Q(offer_expires_at__isnull=False)
                ),
                name="ck_offer_complete",
            ),
            models.CheckConstraint(
                condition=~Q(status="WAITING") | (
                    Q(offered_seat__isnull=True) & Q(offer_expires_at__isnull=True)
                ),
                name="ck_waiting_no_offer",
            ),
        ]


class Payment(models.Model):
    """A simulated payment record; no real money is transferred."""
    class Status(models.TextChoices):
        CAPTURED = "CAPTURED", "Captured"
        REFUNDED = "REFUNDED", "Refunded"

    booking = models.OneToOneField(Booking, on_delete=models.PROTECT, related_name="payment")
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.CAPTURED)
    captured_at = models.DateTimeField(auto_now_add=True)
    refunded_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.CheckConstraint(condition=Q(amount__gte=0), name="ck_payment_amount"),
            models.CheckConstraint(condition=Q(status__in=["CAPTURED", "REFUNDED"]), name="ck_payment_status"),
        ]


class BusReview(models.Model):
    booking = models.OneToOneField(Booking, on_delete=models.CASCADE, related_name="review")
    bus = models.ForeignKey(Bus, on_delete=models.CASCADE, related_name="reviews")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="bus_reviews")
    rating = models.PositiveSmallIntegerField()
    comment = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.CheckConstraint(condition=Q(rating__gte=1, rating__lte=5), name="ck_review_rating")]


class SupportRequest(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="support_requests")
    booking = models.ForeignKey(Booking, on_delete=models.SET_NULL, null=True, blank=True)
    subject = models.CharField(max_length=120)
    message = models.TextField(max_length=2000)
    status = models.CharField(max_length=12, choices=[("OPEN", "Open"), ("IN_PROGRESS", "In progress"), ("RESOLVED", "Resolved")], default="OPEN")
    staff_response = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class BookingStatusEvent(models.Model):
    """Status history written by an Oracle trigger in migration 0006."""

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="status_events")
    old_status = models.CharField(max_length=12, null=True, blank=True)
    new_status = models.CharField(max_length=12)
    changed_at = models.DateTimeField(editable=False)

    class Meta:
        ordering = ["changed_at", "id"]
        indexes = [
            models.Index(fields=["booking", "changed_at", "id"], name="idx_booking_event_order")
        ]


class LoginEvent(models.Model):
    """A successful sign-in, retained for optional staff inspection."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="login_events")
    occurred_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=12, choices=[("SITE", "Website"), ("ADMIN", "Admin")])

    class Meta:
        ordering = ["-occurred_at", "-id"]
        indexes = [models.Index(fields=["user", "occurred_at"], name="idx_login_user_time")]


class AccountProfile(models.Model):
    class Theme(models.TextChoices):
        SYSTEM = "SYSTEM", "Use device setting"
        LIGHT = "LIGHT", "Light"
        DARK = "DARK", "Dark"

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="account_profile")
    phone = models.CharField(max_length=20, blank=True)
    theme = models.CharField(max_length=6, choices=Theme.choices, default=Theme.SYSTEM)
