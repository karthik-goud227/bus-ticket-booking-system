from datetime import datetime, time, timedelta
import re

from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import UserCreationForm
from django.contrib.admin.views.decorators import staff_member_required
from django.db import connection
from django.db.models import Exists, OuterRef
from django.db.models import Count
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .models import Booking, Bus, Payment, Seat, Trip, TripSeat, WaitlistEntry
from .services import BookingConflict, cancel_booking, confirm_booking, hold_seats, join_waitlist, leave_waitlist, refresh_trip


@staff_member_required
def staff_overview(request):
    """Operational counts from the project's Oracle-backed tables."""
    status_counts = dict(Booking.objects.values_list("status").annotate(total=Count("id")))
    return render(request, "booking/staff_overview.html", {
        "bus_count": Bus.objects.count(),
        "active_bus_count": Bus.objects.filter(is_active=True).count(),
        "trip_count": Trip.objects.count(),
        "upcoming_trip_count": Trip.objects.filter(is_cancelled=False, departure_at__gt=timezone.now()).count(),
        "seat_count": Seat.objects.count(),
        "trip_seat_count": TripSeat.objects.count(),
        "passenger_count": get_user_model().objects.filter(is_staff=False).count(),
        "booking_count": Booking.objects.count(),
        "held_count": status_counts.get(Booking.Status.HELD, 0),
        "confirmed_count": status_counts.get(Booking.Status.CONFIRMED, 0),
        "cancelled_count": status_counts.get(Booking.Status.CANCELLED, 0),
        "expired_count": status_counts.get(Booking.Status.EXPIRED, 0),
        "queue_count": WaitlistEntry.objects.filter(status__in=[WaitlistEntry.Status.WAITING, WaitlistEntry.Status.OFFERED]).count(),
    })


@staff_member_required
def staff_revenue(request):
    """Simulated financial totals calculated by the Oracle revenue view."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT r.trip_id, r.origin, r.destination, r.captured_amount,
                   r.refunded_amount, r.net_amount, o.booked_seats
            FROM v_trip_revenue r
            JOIN v_trip_occupancy o ON o.trip_id = r.trip_id
            ORDER BY r.net_amount DESC, r.trip_id DESC
        """)
        columns = [column[0].lower() for column in cursor.description]
        trips = [dict(zip(columns, row)) for row in cursor.fetchall()]
    from decimal import Decimal
    zero = Decimal("0.00")
    return render(request, "booking/staff_revenue.html", {
        "trips": trips,
        "captured_amount": sum((row["captured_amount"] for row in trips), zero),
        "refunded_amount": sum((row["refunded_amount"] for row in trips), zero),
        "net_amount": sum((row["net_amount"] for row in trips), zero),
        "captured_count": Payment.objects.filter(status=Payment.Status.CAPTURED).count(),
        "refunded_count": Payment.objects.filter(status=Payment.Status.REFUNDED).count(),
    })


@staff_member_required
def insights(request):
    """Read-only dashboard sourced from the Oracle reporting views."""
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT o.trip_id, o.origin, o.destination, o.total_seats,
                   o.booked_seats, o.available_seats, o.occupancy_pct,
                   r.captured_amount, r.refunded_amount, r.net_amount
            FROM v_trip_occupancy o
            JOIN v_trip_revenue r ON r.trip_id = o.trip_id
            ORDER BY o.trip_id DESC
        """)
        columns = [column[0].lower() for column in cursor.description]
        trips = [dict(zip(columns, row)) for row in cursor.fetchall()]
        cursor.execute("""
            SELECT trip_id,
                   SUM(CASE WHEN status = 'WAITING' THEN 1 ELSE 0 END) AS waiting_count,
                   SUM(CASE WHEN status = 'OFFERED' AND offer_expires_at > %s
                            THEN 1 ELSE 0 END) AS offered_count
            FROM v_waitlist_queue
            GROUP BY trip_id
        """, [timezone.now()])
        queue_by_trip = {
            trip_id: (int(waiting or 0), int(offered or 0))
            for trip_id, waiting, offered in cursor.fetchall()
        }
    for trip in trips:
        trip["waiting_count"], trip["offered_count"] = queue_by_trip.get(trip["trip_id"], (0, 0))
        trip["queue_count"] = trip["waiting_count"] + trip["offered_count"]
    max_queue = max((trip["queue_count"] for trip in trips), default=0)
    for trip in trips:
        trip["queue_pct"] = round(100 * trip["queue_count"] / max_queue) if max_queue else 0
    return render(request, "booking/insights.html", {
        "trips": trips,
        "queued_trips": [trip for trip in trips if trip["queue_count"]],
        "trip_count": len(trips),
        "total_seats": sum(row["total_seats"] for row in trips),
        "booked_seats": sum(row["booked_seats"] for row in trips),
        "net_amount": sum(row["net_amount"] for row in trips),
        "waiting_count": sum(row["waiting_count"] for row in trips),
        "offered_count": sum(row["offered_count"] for row in trips),
    })


def home(request):
    now = timezone.now()
    trips = Trip.objects.select_related("bus").filter(
        is_cancelled=False, bus__is_active=True, departure_at__gt=now
    )
    origin = request.GET.get("origin", "").strip()
    destination = request.GET.get("destination", "").strip()
    date = request.GET.get("date", "").strip()
    sort = request.GET.get("sort", "departure")
    sort_fields = {
        "departure": ("departure_at", "id"),
        "fare_low": ("fare", "departure_at", "id"),
        "fare_high": ("-fare", "departure_at", "id"),
    }
    if sort not in sort_fields:
        sort = "departure"
    only_available = request.GET.get("available") == "1"
    if origin:
        trips = trips.filter(origin__icontains=origin)
    if destination:
        trips = trips.filter(destination__icontains=destination)
    if date:
        try:
            chosen = datetime.strptime(date, "%Y-%m-%d").date()
            start = timezone.make_aware(datetime.combine(chosen, time.min))
            trips = trips.filter(departure_at__gte=start, departure_at__lt=start + timedelta(days=1))
        except ValueError:
            messages.error(request, "Enter a valid travel date.")
    if only_available:
        active_offer_seats = WaitlistEntry.objects.filter(
            status=WaitlistEntry.Status.OFFERED,
            offer_expires_at__gt=now,
            offered_seat_id__isnull=False,
        ).values("offered_seat_id")
        bookable_seats = TripSeat.objects.filter(
            trip_id=OuterRef("pk"), status=TripSeat.Status.AVAILABLE
        ).exclude(pk__in=active_offer_seats)
        trips = trips.filter(Exists(bookable_seats))
    trip_list = list(trips.order_by(*sort_fields[sort])[:50])
    if trip_list:
        placeholders = ", ".join(["%s"] * len(trip_list))
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT o.trip_id, "
                "(SELECT COUNT(*) FROM booking_tripseat ts "
                " WHERE ts.trip_id = o.trip_id AND ts.status = 'AVAILABLE' "
                " AND NOT EXISTS (SELECT 1 FROM booking_waitlistentry w "
                " WHERE w.offered_seat_id = ts.id AND w.status = 'OFFERED' "
                " AND w.offer_expires_at > %s)) AS bookable_seats "
                f"FROM v_trip_occupancy o WHERE o.trip_id IN ({placeholders})",
                [timezone.now(), *[trip.id for trip in trip_list]],
            )
            availability = dict(cursor.fetchall())
        for trip in trip_list:
            trip.bookable_seats = availability.get(trip.id, 0)
    return render(request, "booking/home.html", {
        "trips": trip_list, "origin": origin, "destination": destination, "date": date,
        "sort": sort, "only_available": only_available,
    })


def signup(request):
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("home")
    return render(request, "booking/signup.html", {"form": form})


def trip_detail(request, trip_id):
    trip = get_object_or_404(Trip.objects.select_related("bus"), id=trip_id)
    refresh_trip(trip.id)
    trip_open = not trip.is_cancelled and trip.bus.is_active and trip.departure_at > timezone.now()
    seats = list(TripSeat.objects.filter(trip=trip).select_related("seat"))
    seats.sort(key=lambda inventory: [
        (0, int(part)) if part.isdigit() else (1, part.lower())
        for part in re.split(r"(\d+)", inventory.seat.number)
    ])
    offered_ids = set(WaitlistEntry.objects.filter(
        trip=trip, status=WaitlistEntry.Status.OFFERED,
        offer_expires_at__gt=timezone.now(),
    ).values_list("offered_seat_id", flat=True))
    for seat in seats:
        seat.can_select = trip_open and seat.status == TripSeat.Status.AVAILABLE and seat.id not in offered_ids
    available_count = sum(seat.can_select for seat in seats)
    return render(request, "booking/trip.html", {
        "trip": trip, "seat_rows": [seats[i:i + 4] for i in range(0, len(seats), 4)],
        "available_count": available_count, "trip_open": trip_open,
    })


@login_required
@require_POST
def create_hold(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    try:
        booking = hold_seats(user=request.user, trip=trip, seat_ids=request.POST.getlist("seats"))
        return redirect("booking_detail", booking_id=booking.id)
    except (BookingConflict, ValueError) as error:
        messages.error(request, str(error))
        return redirect("trip_detail", trip_id=trip_id)


@login_required
@require_POST
def waitlist_join(request, trip_id):
    trip = get_object_or_404(Trip, id=trip_id)
    try:
        join_waitlist(user=request.user, trip=trip)
        messages.success(request, "You joined the waiting list. Check My bookings for offers.")
    except BookingConflict as error:
        messages.error(request, str(error))
    return redirect("trip_detail", trip_id=trip_id)


@login_required
@require_POST
def waitlist_leave(request, entry_id):
    entry = get_object_or_404(WaitlistEntry, id=entry_id, user=request.user)
    try:
        leave_waitlist(user=request.user, entry_id=entry.id)
        messages.success(request, "You left the waiting list.")
    except BookingConflict as error:
        messages.error(request, str(error))
    return redirect("my_bookings")


@login_required
@require_POST
def accept_offer(request, entry_id):
    entry = get_object_or_404(WaitlistEntry.objects.select_related("trip"), id=entry_id, user=request.user)
    try:
        booking = hold_seats(
            user=request.user, trip=entry.trip, seat_ids=[entry.offered_seat_id], waitlist_entry=entry,
        )
        return redirect("booking_detail", booking_id=booking.id)
    except (BookingConflict, ValueError, TypeError) as error:
        messages.error(request, str(error))
        return redirect("my_bookings")


@login_required
def my_bookings(request):
    bookings = Booking.objects.filter(user=request.user).select_related("trip", "trip__bus").order_by("-created_at")
    active_statuses = [WaitlistEntry.Status.WAITING, WaitlistEntry.Status.OFFERED]
    trip_ids = WaitlistEntry.objects.filter(
        user=request.user, status__in=active_statuses
    ).values_list("trip_id", flat=True).distinct()
    held_trip_ids = Booking.objects.filter(
        user=request.user, status=Booking.Status.HELD
    ).values_list("trip_id", flat=True).distinct()
    for trip_id in sorted(set(trip_ids) | set(held_trip_ids)):
        refresh_trip(trip_id)
    waitlist_entries = list(WaitlistEntry.objects.filter(
        user=request.user, status__in=active_statuses
    ).select_related("trip", "offered_seat__seat").order_by("joined_at", "id"))
    with connection.cursor() as cursor:
        cursor.execute(
            "SELECT entry_id, queue_position FROM v_waitlist_queue WHERE user_id = %s",
            [request.user.id],
        )
        positions = dict(cursor.fetchall())
    for entry in waitlist_entries:
        entry.queue_position = positions.get(entry.id)
    return render(request, "booking/my_bookings.html", {
        "bookings": bookings, "waitlist_entries": waitlist_entries,
    })


@login_required
def booking_detail(request, booking_id):
    booking = get_object_or_404(
        Booking.objects.select_related("trip", "trip__bus", "user"), id=booking_id, user=request.user,
    )
    if booking.status == Booking.Status.HELD and booking.hold_expires_at <= timezone.now():
        refresh_trip(booking.trip_id)
        booking.refresh_from_db()
    seats = booking.allocated_seats.select_related("seat").order_by("seat__number")
    payment = Payment.objects.filter(booking=booking).first()
    return render(request, "booking/booking_detail.html", {
        "booking": booking, "seats": seats, "payment": payment,
    })


@login_required
@require_POST
def confirm(request, booking_id):
    try:
        booking = confirm_booking(user=request.user, booking_id=booking_id)
        messages.success(request, "Simulated payment successful. Your seats are confirmed.")
    except BookingConflict as error:
        messages.error(request, str(error))
    return redirect("booking_detail", booking_id=booking_id)


@login_required
@require_POST
def cancel(request, booking_id):
    try:
        cancel_booking(user=request.user, booking_id=booking_id)
        messages.success(request, "Booking cancelled. A simulated full refund was recorded if you had paid.")
    except BookingConflict as error:
        messages.error(request, str(error))
    return redirect("booking_detail", booking_id=booking_id)
