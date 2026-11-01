from django.contrib import admin

from .models import Booking, BookingStatusEvent, Bus, Payment, Seat, Trip, TripSeat, WaitlistEntry


class SeatInline(admin.TabularInline):
    model = Seat
    extra = 4


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "operator_name", "bus_type", "is_active")
    search_fields = ("registration_number", "operator_name")
    inlines = (SeatInline,)


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("number", "bus", "seat_type")
    list_filter = ("bus",)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("origin", "destination", "departure_at", "bus", "fare", "is_cancelled")
    list_filter = ("is_cancelled", "departure_at")
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
    list_display = ("reference", "user", "trip", "status", "total_fare", "created_at")
    list_filter = ("status",)
    inlines = (BookingStatusEventInline,)


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("trip", "user", "status", "joined_at", "offer_expires_at")
    list_filter = ("status",)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ("booking", "amount", "status", "captured_at", "refunded_at")
    list_filter = ("status",)
