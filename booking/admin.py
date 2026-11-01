from django.contrib import admin

from .models import Booking, Bus, Seat, Trip, TripSeat, WaitlistEntry


@admin.register(Bus)
class BusAdmin(admin.ModelAdmin):
    list_display = ("registration_number", "operator_name", "bus_type", "is_active")
    search_fields = ("registration_number", "operator_name")


@admin.register(Seat)
class SeatAdmin(admin.ModelAdmin):
    list_display = ("number", "bus", "seat_type")
    list_filter = ("bus",)


@admin.register(Trip)
class TripAdmin(admin.ModelAdmin):
    list_display = ("origin", "destination", "departure_at", "bus", "fare", "is_cancelled")
    list_filter = ("is_cancelled", "departure_at")


@admin.register(TripSeat)
class TripSeatAdmin(admin.ModelAdmin):
    list_display = ("trip", "seat", "status", "booking")
    list_filter = ("status",)


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = ("reference", "user", "trip", "status", "total_fare", "created_at")
    list_filter = ("status",)


@admin.register(WaitlistEntry)
class WaitlistEntryAdmin(admin.ModelAdmin):
    list_display = ("trip", "user", "status", "joined_at", "offer_expires_at")
    list_filter = ("status",)
