
from django.contrib import admin
from .models import UserProfile, Aircraft, FlightRoute, Booking

# added for ops
# from django.contrib import admin
from .models import FlightRecord

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

    # added for flight ops




@admin.register(FlightRecord)
class FlightRecordAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "route",
        "service_number",
        "officer_name_initial",
        "captain_name_initial",
        "actual_takeoff",
        "actual_landing",
        "created_at",
    )

    list_filter = (
        "instrument_flying",
        "approach_aid",
        "created_at",
    )

    search_fields = (
        "service_number",
        "personnel_name",
        "officer_name_initial",
        "captain_name_initial",
        "remarks",
    )

    readonly_fields = (
        "created_by",
        "service_number",
        "rank",
        "personnel_name",
        "created_at",
        "updated_at",
    )

