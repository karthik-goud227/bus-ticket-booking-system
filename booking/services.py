"""Short, atomic operations that own seat inventory changes."""
from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from django.db import transaction
from django.utils import timezone

from .models import Booking, Payment, Trip, TripPoint, TripSeat, WaitlistEntry


HOLD_MINUTES = 10
OFFER_MINUTES = 10


class BookingConflict(Exception):
    pass


def fare_breakdown(seat_fare, seat_count):
    base = (Decimal(str(seat_fare)) * seat_count).quantize(Decimal("0.01"))
    platform = Decimal("20.00")
    service = Decimal("10.00")
    gst = ((platform + service) * Decimal("0.18")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    return {"base": base, "platform": platform, "service": service, "gst": gst,
            "total": base + platform + service + gst}


def _release_expired(trip_id, now):
    released = []
    expired = list(
        Booking.objects.select_for_update()
        .filter(trip_id=trip_id, status=Booking.Status.HELD, hold_expires_at__lte=now)
        .order_by("id")
    )
    for booking in expired:
        stale_seats = list(TripSeat.objects.filter(booking=booking, status=TripSeat.Status.HELD))
        TripSeat.objects.filter(booking=booking, status=TripSeat.Status.HELD).update(
            status=TripSeat.Status.AVAILABLE, booking=None, hold_expires_at=None
        )
        for seat in stale_seats:
            seat.status = TripSeat.Status.AVAILABLE
            seat.booking = None
            seat.hold_expires_at = None
        released.extend(stale_seats)
        booking.status = Booking.Status.EXPIRED
        booking.save(update_fields=["status"])
    return released


def _expire_offers(trip_id, now):
    expired = list(WaitlistEntry.objects.filter(
        trip_id=trip_id, status=WaitlistEntry.Status.OFFERED, offer_expires_at__lte=now
    ).select_related("offered_seat"))
    WaitlistEntry.objects.filter(id__in=[entry.id for entry in expired]).update(
        status=WaitlistEntry.Status.EXPIRED, offered_seat=None, offer_expires_at=None
    )
    return [entry.offered_seat for entry in expired if entry.offered_seat is not None]


def _offer_next(trip_id, available_seats, now):
    """Assign available seats to the FIFO queue before direct buyers can use them."""
    if not Trip.objects.filter(
        id=trip_id, is_cancelled=False, bus__is_active=True, departure_at__gt=now
    ).exists():
        return
    for seat in available_seats:
        if seat.status != TripSeat.Status.AVAILABLE:
            continue
        if WaitlistEntry.objects.filter(
            trip_id=trip_id, status=WaitlistEntry.Status.OFFERED,
            offered_seat=seat, offer_expires_at__gt=now,
        ).exists():
            continue
        next_entry = (
            WaitlistEntry.objects.select_for_update()
            .filter(trip_id=trip_id, status=WaitlistEntry.Status.WAITING)
            .order_by("joined_at", "id")
        )
        next_entry = next(iter(next_entry), None)
        if next_entry is None:
            break
        next_entry.status = WaitlistEntry.Status.OFFERED
        next_entry.offered_seat = seat
        next_entry.offer_expires_at = now + timedelta(minutes=OFFER_MINUTES)
        next_entry.save(update_fields=["status", "offered_seat", "offer_expires_at"])


def _offer_all_waiting(trip_id, now):
    """Preserve FIFO priority when new trip seats are added to an existing bus."""
    if WaitlistEntry.objects.filter(trip_id=trip_id, status=WaitlistEntry.Status.WAITING).exists():
        available = TripSeat.objects.filter(trip_id=trip_id, status=TripSeat.Status.AVAILABLE).order_by("id")
        _offer_next(trip_id, available, now)


@transaction.atomic
def refresh_trip(trip_id):
    """Expire stale state and promote waiting passengers on every seat-map visit."""
    Trip.objects.select_for_update().get(id=trip_id)
    now = timezone.now()
    released = _release_expired(trip_id, now)
    released.extend(_expire_offers(trip_id, now))
    _offer_next(trip_id, released, now)
    _offer_all_waiting(trip_id, now)


@transaction.atomic
def hold_seats(*, user, trip, seat_ids, waitlist_entry=None, passenger_name="", passenger_phone="", boarding_point_id=None, dropoff_point_id=None):
    """Lock selected inventory rows and claim all requested seats or none."""
    now = timezone.now()
    ids = sorted(set(int(value) for value in seat_ids))
    if not ids:
        raise BookingConflict("Choose at least one seat.")
    trip = Trip.objects.select_for_update().get(id=trip.id)
    if trip.is_cancelled or not trip.bus.is_active or trip.departure_at <= now:
        raise BookingConflict("This trip is no longer open for booking.")
    boarding = TripPoint.objects.filter(trip=trip, kind=TripPoint.Kind.BOARDING, id=boarding_point_id).first() if boarding_point_id else TripPoint.objects.filter(trip=trip, kind=TripPoint.Kind.BOARDING).order_by("scheduled_at", "id").first()
    dropoff = TripPoint.objects.filter(trip=trip, kind=TripPoint.Kind.DROPOFF, id=dropoff_point_id).first() if dropoff_point_id else TripPoint.objects.filter(trip=trip, kind=TripPoint.Kind.DROPOFF).order_by("scheduled_at", "id").first()
    if (not boarding or not dropoff or boarding.scheduled_at >= dropoff.scheduled_at
            or boarding.scheduled_at < trip.departure_at or dropoff.scheduled_at > trip.arrival_at):
        raise BookingConflict("Choose valid boarding and drop-off points for this trip.")
    released = _release_expired(trip.id, now)
    released.extend(_expire_offers(trip.id, now))
    _offer_next(trip.id, released, now)
    _offer_all_waiting(trip.id, now)
    seats = list(
        TripSeat.objects.select_for_update()
        .filter(trip=trip, id__in=ids).order_by("id")
    )
    if len(seats) != len(ids) or any(seat.status != TripSeat.Status.AVAILABLE for seat in seats):
        raise BookingConflict("A selected seat is no longer available. Refresh the seat map.")
    if waitlist_entry is not None:
        waitlist_entry = WaitlistEntry.objects.select_for_update().get(id=waitlist_entry.id)
        if len(seats) != 1 or waitlist_entry.user_id != user.id or waitlist_entry.trip_id != trip.id:
            raise BookingConflict("This offer cannot be used for these seats.")
        if (waitlist_entry.status != WaitlistEntry.Status.OFFERED
                or waitlist_entry.offered_seat_id != seats[0].id
                or waitlist_entry.offer_expires_at <= now):
            raise BookingConflict("This waiting-list offer has expired.")
    for seat in seats:
        offer = WaitlistEntry.objects.filter(
            trip=trip, offered_seat=seat, status=WaitlistEntry.Status.OFFERED,
            offer_expires_at__gt=now,
        ).first()
        if offer is not None and (waitlist_entry is None or offer.id != waitlist_entry.id):
            raise BookingConflict("A selected seat is reserved for the waiting list.")
    deadline = now + timedelta(minutes=HOLD_MINUTES)
    charges = fare_breakdown(trip.fare, len(seats))
    booking = Booking.objects.create(
        reference=uuid4().hex[:12].upper(), user=user, trip=trip,
        total_fare=charges["total"], hold_expires_at=deadline,
        passenger_name=passenger_name or user.get_full_name() or user.username,
        passenger_phone=passenger_phone,
        boarding_point=boarding, dropoff_point=dropoff, base_fare=charges["base"],
        platform_fee=charges["platform"], service_fee=charges["service"], gst_amount=charges["gst"],
    )
    for seat in seats:
        seat.status = TripSeat.Status.HELD
        seat.booking = booking
        seat.hold_expires_at = deadline
        seat.save(update_fields=["status", "booking", "hold_expires_at"])
    if waitlist_entry is not None:
        waitlist_entry.status = WaitlistEntry.Status.ACCEPTED
        waitlist_entry.save(update_fields=["status"])
    return booking


@transaction.atomic
def confirm_booking(*, user, booking_id):
    """Idempotent simulated capture and confirmation."""
    booking = Booking.objects.select_for_update().get(id=booking_id, user=user)
    if booking.status == Booking.Status.CONFIRMED:
        return booking
    if booking.status != Booking.Status.HELD or booking.hold_expires_at <= timezone.now():
        raise BookingConflict("The seat hold has expired.")
    if not booking.allocated_seats.filter(status=TripSeat.Status.HELD).exists():
        raise BookingConflict("No seats remain in this hold.")
    Payment.objects.create(booking=booking, amount=booking.total_fare)
    booking.allocated_seats.update(status=TripSeat.Status.BOOKED, hold_expires_at=None)
    booking.status = Booking.Status.CONFIRMED
    booking.confirmed_at = timezone.now()
    booking.save(update_fields=["status", "confirmed_at"])
    return booking


@transaction.atomic
def cancel_booking(*, user, booking_id):
    """Idempotent whole-booking cancellation and simulated full refund."""
    trip_id = Booking.objects.only("trip_id").get(id=booking_id, user=user).trip_id
    Trip.objects.select_for_update().get(id=trip_id)
    booking = Booking.objects.select_for_update().get(id=booking_id, user=user)
    if booking.status == Booking.Status.CANCELLED:
        return booking
    if booking.status not in (Booking.Status.HELD, Booking.Status.CONFIRMED):
        raise BookingConflict("This booking cannot be cancelled.")
    if booking.trip.departure_at <= timezone.now():
        raise BookingConflict("This trip has already departed.")
    seats = list(TripSeat.objects.select_for_update().filter(booking=booking).order_by("id"))
    for seat in seats:
        seat.status = TripSeat.Status.AVAILABLE
        seat.booking = None
        seat.hold_expires_at = None
        seat.save(update_fields=["status", "booking", "hold_expires_at"])
    now = timezone.now()
    if booking.status == Booking.Status.CONFIRMED:
        payment = booking.payment
        payment.status = Payment.Status.REFUNDED
        payment.refunded_at = now
        payment.save(update_fields=["status", "refunded_at"])
    booking.status = Booking.Status.CANCELLED
    booking.cancelled_at = now
    booking.save(update_fields=["status", "cancelled_at"])
    expired_offer_seats = _expire_offers(booking.trip_id, now)
    _offer_next(booking.trip_id, seats + expired_offer_seats, now)
    return booking


@transaction.atomic
def join_waitlist(*, user, trip):
    trip = Trip.objects.select_for_update().get(id=trip.id)
    if trip.is_cancelled or not trip.bus.is_active or trip.departure_at <= timezone.now():
        raise BookingConflict("This trip is no longer open.")
    now = timezone.now()
    released = _release_expired(trip.id, now)
    released.extend(_expire_offers(trip.id, now))
    _offer_next(trip.id, released, now)
    existing_entries = WaitlistEntry.objects.select_for_update().filter(
        user=user, trip=trip, status__in=[WaitlistEntry.Status.WAITING, WaitlistEntry.Status.OFFERED]
    )
    existing = next(iter(existing_entries), None)
    if existing:
        return existing
    available_ids = TripSeat.objects.filter(trip=trip, status=TripSeat.Status.AVAILABLE).values_list("id", flat=True)
    offered_ids = WaitlistEntry.objects.filter(
        trip=trip, status=WaitlistEntry.Status.OFFERED, offer_expires_at__gt=now
    ).values_list("offered_seat_id", flat=True)
    if set(available_ids) - set(offered_ids):
        raise BookingConflict("Seats are available now. Please book one directly.")
    return WaitlistEntry.objects.create(user=user, trip=trip)


@transaction.atomic
def leave_waitlist(*, user, entry_id):
    """Remove a passenger and immediately pass any active offer to the FIFO queue."""
    trip_id = WaitlistEntry.objects.only("trip_id").get(id=entry_id, user=user).trip_id
    Trip.objects.select_for_update().get(id=trip_id)
    now = timezone.now()
    released = _release_expired(trip_id, now)
    released.extend(_expire_offers(trip_id, now))
    entry = WaitlistEntry.objects.select_for_update().get(id=entry_id, user=user)
    if entry.status == WaitlistEntry.Status.CANCELLED:
        _offer_next(trip_id, released, now)
        return entry
    if entry.status not in (WaitlistEntry.Status.WAITING, WaitlistEntry.Status.OFFERED):
        raise BookingConflict("This waiting-list entry is no longer active.")
    if entry.status == WaitlistEntry.Status.OFFERED and entry.offered_seat_id:
        released.append(entry.offered_seat)
    entry.status = WaitlistEntry.Status.CANCELLED
    entry.offered_seat = None
    entry.offer_expires_at = None
    entry.save(update_fields=["status", "offered_seat", "offer_expires_at"])
    _offer_next(trip_id, released, now)
    return entry
