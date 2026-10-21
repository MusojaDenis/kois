
from django.urls import path
from . import views

# added for urls ops
# from django.urls import path
# from . import views
# end

app_name = "core"

urlpatterns = [
    path("", views.home, name="home"),
    path("login/", views.module_login, name="module_login"),
    path("signup/", views.signup, name="signup"),
    path("dashboard/<str:module>/", views.dashboard, name="dashboard", ),
    path("logout/", views.logout_view, name="logout"),
    path("user-management/",views.user_management,name="user_management",),
    path("booking-admin/",views.booking_admin_home,name="booking_admin_home",),

    path("booking-admin/aircraft/", views.aircraft_list,name="aircraft_list", ),
    path("booking-admin/aircraft/add/",views.aircraft_create, name="aircraft_create", ),
    path("booking-admin/routes/", views.route_list, name="route_list", ),
    path("booking-admin/routes/add/", views.route_create,name="route_create",),
    
    path("booking-admin/bookings/", views.booking_list, name="booking_list",),
    path("booking-admin/bookings/<int:booking_id>/approve/", views.booking_approve, name="booking_approve", ),
    path("booking-admin/bookings/<int:booking_id>/cancel/", views.booking_cancel, name="booking_cancel", ),
    
    path("manifest/flights/", views.manifest_flights, name="manifest_flights"),
    path("manifest/book/", views.passenger_book, name="passenger_book"),
    path("manifest/my-bookings/", views.my_bookings, name="my_bookings"),

    path(
    "booking-admin/seat-reservations/",
    views.official_seat_reservations,
    name="official_seat_reservations",
),
path(
    "booking-admin/seat-reservations/<int:reservation_id>/release/",
    views.release_official_seat_reservation,
    name="release_official_seat_reservation",
),


# added URL for flight ops




    path(
        "flight-record/new/",
        views.flight_record_create,
        name="flight_record_create",
    ),


]
