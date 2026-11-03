from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.db.models import Count

from .models import Booking, BookingStatusEvent, Bus, BusReview, LoginEvent, Payment, RecurringTrip, Seat, SupportRequest, Trip, TripPoint, TripSeat, WaitlistEntry

admin.site.site_header = "BusBook administration"
admin.site.site_title = "BusBook admin"
admin.site.index_title = "Fleet, passengers and booking activity"


class PassengerBookingInline(admin.TabularInline):
    model = Booking
    extra = 0
    can_delete = False
    fields = ("reference", "trip", "status", "total_fare", "created_at")
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


class PassengerWaitlistInline(admin.TabularInline):
    model = WaitlistEntry
    extra = 0
    can_delete = False
    fields = ("trip", "status", "joined_at", "offer_expires_at")
    readonly_fields = fields
    show_change_link = True

    def has_add_permission(self, request, obj=None):
        return False


User = get_user_model()
admin.site.unregister(User)


@admin.register(User)
class PassengerAdmin(DjangoUserAdmin):
    list_display = ("username", "email", "is_staff", "booking_count", "queue_count", "date_joined")
    list_filter = ("is_staff", "is_active", "date_joined")
    search_fields = ("username", "email", "first_name", "last_name")
    ordering = ("-date_joined",)
    inlines = (PassengerBookingInline, PassengerWaitlistInline)

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(
            _booking_count=Count("bookings", distinct=True),
            _queue_count=Count("waitlist_entries", distinct=True),
        )

    @admin.display(description="Bookings", ordering="_booking_count")
    def booking_count(self, obj):
        return obj._booking_count

    @admin.display(description="Queue entries", ordering="_queue_count")
    def queue_count(self, obj):
        return obj._queue_count


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 4


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "operator_name", "bus_type", "seats_per_row", "has_upper_deck", "is_active")
    search_fields = ("registration_number", "operator_name")
    list_filter = ("bus_type", "is_active")
    inlines = (SeatInline,)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("number", "bus", "deck", "seat_type")
    list_filter = ("bus", "deck", "seat_type")


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("origin", "destination", "departure_at", "arrival_at", "bus", "schedule", "fare", "is_cancelled")
    list_filter = ("is_cancelled", "departure_at", "bus__bus_type")
    search_fields = ("origin", "destination", "bus__registration_number", "bus__operator_name")
    actions = ("sync_seat_inventory",)

    def get_readonly_fields(self, request, obj=None):
        return ("bus",) if obj else ()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if not change:
            for seat in obj.bus.seats.all():
                TripSeat.objects.get_or_create(trip=obj, seat=seat)

    @admin.action(description="Add missing seats to selected trips")
    def sync_seat_inventory(self, request, queryset):
        count = 0
        for trip in queryset.select_related("bus"):
            for seat in trip.bus.seats.all():
                _, created = TripSeat.objects.get_or_create(trip=trip, seat=seat)
                count += created
        self.message_user(request, f"Added {count} missing trip seats.")


@admin.register(TripPoint)
class TripPointAdmin(admin.ModelAdmin):
    list_display = ("trip", "kind", "name", "scheduled_at")
    list_filter = ("kind",)
    search_fields = ("name", "trip__origin", "trip__destination")


@admin.register(RecurringTrip)
class RecurringTripAdmin(admin.ModelAdmin):
    list_display = ("bus", "origin", "destination", "departure_time", "duration_minutes", "fare", "is_active")
    list_filter = ("is_active", "bus")
    search_fields = ("origin", "destination", "bus__registration_number")


@admin.register(TripSeat)
class TripSeatAdmin(admin.ModelAdmin):
    list_display = ("trip", "seat", "status", "booking")
    list_filter = ("status",)


class BookingStatusEventInline(admin.TabularInline):
    model = BookingStatusEvent
    extra = 0
    can_delete = False
    readonly_fields = ("old_status", "new_status", "changed_at")

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "passenger_name", "passenger_phone", "trip", "status", "total_fare", "created_at")
    list_filter = ("status", "trip__departure_at")
    search_fields = ("reference", "user__username", "trip__origin", "trip__destination")
    readonly_fields = ("reference", "user", "passenger_name", "passenger_phone", "trip", "boarding_point", "dropoff_point", "base_fare", "platform_fee", "service_fee", "gst_amount", "status", "total_fare", "created_at", "hold_expires_at", "confirmed_at", "cancelled_at")
    list_select_related = ("user", "trip")
    inlines = (BookingStatusEventInline,)

    def has_add_permission(self, request):
        return False


@admin.register(BusReview)
class BusReviewAdmin(admin.ModelAdmin):
    list_display = ("bus", "user", "rating", "created_at")
    list_filter = ("rating", "bus")
    readonly_fields = ("booking", "bus", "user", "rating", "comment", "created_at")

    def has_add_permission(self, request):
        return False


@admin.register(SupportRequest)
class SupportRequestAdmin(admin.ModelAdmin):
    list_display = ("subject", "user", "booking", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("subject", "user__username", "booking__reference")
    readonly_fields = ("user", "booking", "subject", "message", "created_at")
    list_select_related = ("user", "booking")

    def has_add_permission(self, request):
        return False


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("trip", "user", "status", "joined_at", "offer_expires_at")
    list_filter = ("status",)
    search_fields = ("user__username", "trip__origin", "trip__destination")
    list_select_related = ("trip", "user")


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "amount", "status", "captured_at", "refunded_at")
    list_filter = ("status",)
    search_fields = ("booking__reference", "booking__user__username")
    readonly_fields = ("booking", "amount", "status", "captured_at", "refunded_at")
    list_select_related = ("booking",)

    def has_add_permission(self, request):
        return False


@admin.register(BookingStatusEvent)
class BookingStatusEventAdmin(admin.ModelAdmin):
    list_display = ("booking", "old_status", "new_status", "changed_at")
    list_filter = ("new_status",)
    search_fields = ("booking__reference", "booking__user__username")
    readonly_fields = ("booking", "old_status", "new_status", "changed_at")
    list_select_related = ("booking",)

    def has_add_permission(self, request):
        return False


@admin.register(LoginEvent)
class LoginEventAdmin(admin.ModelAdmin):
    list_display = ("user", "occurred_at", "source")
    list_filter = ("source", "occurred_at")
    search_fields = ("user__username", "user__email")
    readonly_fields = ("user", "occurred_at", "source")
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False
