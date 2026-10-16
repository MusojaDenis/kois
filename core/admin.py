
from django.contrib import admin
from .models import UserProfile, Aircraft, FlightRoute, Booking


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "rank",
        "first_name",
        "last_name",
        "phone_number",
        "role",
    )

    list_filter = ("rank", "role")

    search_fields = (
        "user__username",
        "user__email",
        "first_name",
        "middle_name",
        "last_name",
        "phone_number",
    )

    list_editable = ("role",)


@admin.register(Aircraft)
class AircraftAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "tail_number",
        "passenger_capacity",
        "maximum_payload_kg",
        "is_active",
    )
    list_filter = ("is_active",)
    search_fields = ("name", "tail_number")


@admin.register(FlightRoute)
class FlightRouteAdmin(admin.ModelAdmin):
    list_display = (
        "aircraft",
        "departure_airport",
        "destination_airport",
        "departure_datetime",
        "arrival_datetime",
        "is_active",
    )
    list_filter = ("is_active", "departure_airport", "destination_airport")
    search_fields = (
        "aircraft__name",
        "aircraft__tail_number",
        "departure_airport",
        "destination_airport",
    )


@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        "ticket_number",
        "service_number",
        "passenger_full_name",
        "route",
        "status",
        "authorizing_staff",
        "created_at",
    )
    list_filter = ("status", "route__departure_airport", "route__destination_airport")
    search_fields = (
        "ticket_number",
        "service_number",
        "first_name",
        "last_name",
    )
    readonly_fields = ("ticket_number", "created_at", "updated_at")
