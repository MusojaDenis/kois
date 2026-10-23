from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.views.decorators.http import require_POST
from django.utils import timezone
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from .models import Booking, FlightRoute, UserProfile,Aircraft,OfficialSeatReservation
from .forms import KOISLoginForm, KOISSignUpForm

# added forms 
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.utils import timezone

from .models import (
    FlightRecord,
    FlightRoute,
    UserProfile,
)
from .forms import FlightRecordForm
# end of forms
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Count, Q,Sum
from django.contrib.auth import get_user_model
from django import forms
from decimal import Decimal, InvalidOperation



MODULES = {
    "manifest": {
        "name": "Flight Booking & Manifest",
        "role": UserProfile.Role.MANIFEST,
        "template": "core/manifest_dashboard.html",
    },
    "flightops": {
        "name": "Flight Authorization & Hours",
        "role": UserProfile.Role.FLIGHTOPS,
        "template": "core/flightops_dashboard.html",
    },
    "maintenance": {
        "name": "Aircraft Maintenance",
        "role": UserProfile.Role.MAINTENANCE,
        "template": "core/maintenance_dashboard.html",
    },
    "booking_admin": {
    "name": "Booking Administration",
    "role": UserProfile.Role.BOOKING_ADMIN,
    "template": "core/booking_admin_dashboard.html",
    },
}


def is_kois_admin(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    try:
        return user.kois_profile.role == UserProfile.Role.ADMIN
    except UserProfile.DoesNotExist:
        return False

def home(request):
    return render(request, "core/home.html")


def get_profile(user):
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def module_login(request):
    module = request.POST.get("module") or request.GET.get(
        "module", "manifest"
    )

    if module not in MODULES:
        module = "manifest"

    if request.user.is_authenticated:
        if module == "booking_admin":
            return redirect("core:booking_admin_home")
        return redirect("core:dashboard", module=module)

    form = KOISLoginForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]

        user = authenticate(
            request,
            username=username,
            password=password,
        )

        if user is not None:
            profile = get_profile(user)
            requested_role = MODULES[module]["role"]

            allowed = (
                user.is_superuser
                or profile.role == UserProfile.Role.ADMIN
                or profile.role == requested_role
            )

            if allowed:
                login(request, user)
                if module == "booking_admin":
                    return redirect("core:booking_admin_home")
                return redirect("core:dashboard", module=module)

            messages.error(
                request,
                "Your account does not have access to this module. "
                "Please contact the KOIS administrator."
            )
        else:
            messages.error(
                request,
                "Invalid username or password."
            )

    return render(
        request,
        "core/module_login.html",
        {
            "form": form,
            "module": module,
            "module_name": MODULES[module]["name"],
        },
    )


def signup(request):
    module = request.GET.get("module", "manifest")

    if module not in MODULES:
        module = "manifest"

    if request.user.is_authenticated:
        return redirect("core:home")

    form = KOISSignUpForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(
            request,
            "Account created successfully. "
            "An administrator must assign your module access."
        )
        return redirect(
            f"/login/?module={module}"
        )

    return render(
        request,
        "core/signup.html",
        {
            "form": form,
            "module": module,
        },
    )


@login_required
def dashboard(request, module):
    if module not in MODULES:
        messages.error(request, "Unknown KOIS module.")
        return redirect("core:home")

    profile = get_profile(request.user)
    requested_role = MODULES[module]["role"]

    allowed = (
        request.user.is_superuser
        or profile.role == UserProfile.Role.ADMIN
        or profile.role == requested_role
    )

    if not allowed:
        messages.error(
            request,
            "You are not authorised to access this dashboard."
        )
        return redirect("core:home")

    return render(
        request,
        MODULES[module]["template"],
        {
            "module": module,
            "module_name": MODULES[module]["name"],
            "profile": profile,
        },
    )


@require_POST
@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have logged out successfully.")
    return redirect("core:home")


User = get_user_model()


@login_required
def user_management(request):
    if not is_kois_admin(request.user):
        messages.error(
            request,
            "You are not authorised to manage KOIS personnel."
        )
        return redirect("core:home")

    profiles = UserProfile.objects.select_related("user").all()

    search_query = request.GET.get("q", "").strip()
    selected_role = request.GET.get("role", "").strip()
    selected_rank = request.GET.get("rank", "").strip()

    if search_query:
        profiles = profiles.filter(
            Q(user__username__icontains=search_query)
            | Q(user__email__icontains=search_query)
            | Q(first_name__icontains=search_query)
            | Q(middle_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(phone_number__icontains=search_query)
        )

    valid_roles = {value for value, label in UserProfile.Role.choices}
    valid_ranks = {value for value, label in UserProfile.Rank.choices}

    if selected_role in valid_roles:
        profiles = profiles.filter(role=selected_role)
    else:
        selected_role = ""

    if selected_rank in valid_ranks:
        profiles = profiles.filter(rank=selected_rank)
    else:
        selected_rank = ""

    profiles = profiles.order_by("user__username")

    return render(
        request,
        "core/user_management.html",
        {
            "profiles": profiles,
            "search_query": search_query,
            "selected_role": selected_role,
            "selected_rank": selected_rank,
            "role_choices": UserProfile.Role.choices,
            "rank_choices": UserProfile.Rank.choices,
            "total_users": UserProfile.objects.count(),
        },
    )

@login_required
def booking_admin_home(request):
    profile = get_profile(request.user)

    allowed = (
        request.user.is_superuser
        or profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.BOOKING_ADMIN,
        ]
    )

    if not allowed:
        messages.error(
            request,
            "You are not authorised to access Booking Administration."
        )
        return redirect("core:home")

    active_aircraft = Aircraft.objects.filter(is_active=True).count()

    upcoming_routes = FlightRoute.objects.filter(
        is_active=True,
        departure_datetime__gte=timezone.now(),
    ).select_related("aircraft").order_by("departure_datetime")

    pending_bookings = Booking.objects.filter(
        status=Booking.Status.PENDING
    ).count()

    approved_bookings = Booking.objects.filter(
        status=Booking.Status.APPROVED
    ).count()

    cancelled_bookings = Booking.objects.filter(
        status=Booking.Status.CANCELLED
    ).count()

    return render(
        request,
        "core/booking_admin_dashboard.html",
        {
            "profile": profile,
            "active_aircraft": active_aircraft,
            "upcoming_routes": upcoming_routes[:10],
            "pending_bookings": pending_bookings,
            "approved_bookings": approved_bookings,
            "cancelled_bookings": cancelled_bookings,
        },
    )


def can_manage_flights(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    try:
        return user.kois_profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.BOOKING_ADMIN,
        ]
    except UserProfile.DoesNotExist:
        return False


@login_required
def aircraft_list(request):
    if not can_manage_flights(request.user):
        messages.error(request, "You cannot manage aircraft.")
        return redirect("core:home")

    aircraft = Aircraft.objects.all()

    return render(
        request,
        "core/aircraft_list.html",
        {"aircraft": aircraft},
    )


@login_required
def aircraft_create(request):
    if not can_manage_flights(request.user):
        messages.error(request, "You cannot register aircraft.")
        return redirect("core:home")

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        tail_number = request.POST.get("tail_number", "").strip().upper()
        capacity = request.POST.get("passenger_capacity", "").strip()
        payload = request.POST.get("maximum_payload_kg", "0").strip()

        errors = []

        if not name or not tail_number:
            errors.append("Aircraft name and tail number are required.")

        try:
            capacity = int(capacity)
            if capacity < 1:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Passenger capacity must be at least 1.")

        try:
            payload = float(payload)
            if payload < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Maximum payload cannot be negative.")

        if tail_number and Aircraft.objects.filter(
            tail_number__iexact=tail_number
        ).exists():
            errors.append("That tail number is already registered.")

        if errors:
            for error in errors:
                messages.error(request, error)
        else:
            Aircraft.objects.create(
                name=name,
                tail_number=tail_number,
                passenger_capacity=capacity,
                maximum_payload_kg=payload,
            )
            messages.success(request, "Aircraft registered successfully.")
            return redirect("core:aircraft_list")

    return render(request, "core/aircraft_form.html")



def can_manage_bookings(user):
    if not user.is_authenticated:
        return False

    if user.is_superuser:
        return True

    try:
        return user.kois_profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.BOOKING_ADMIN,
        ]
    except UserProfile.DoesNotExist:
        return False


@login_required
def booking_list(request):
    if not can_manage_bookings(request.user):
        messages.error(request, "You are not authorised to manage bookings.")
        return redirect("core:home")

    selected_status = request.GET.get("status", "PENDING")

    valid_statuses = [
        Booking.Status.PENDING,
        Booking.Status.APPROVED,
        Booking.Status.CANCELLED,
    ]

    bookings = Booking.objects.select_related(
        "passenger",
        "route",
        "route__aircraft",
        "authorizing_staff",
    ).all()

    if selected_status in valid_statuses:
        bookings = bookings.filter(status=selected_status)
    else:
        selected_status = "ALL"

    return render(request, "core/manage_bookings.html", {
        "bookings": bookings,
        "selected_status": selected_status,
        "pending_count": Booking.objects.filter(
            status=Booking.Status.PENDING
        ).count(),
        "approved_count": Booking.objects.filter(
            status=Booking.Status.APPROVED
        ).count(),
        "cancelled_count": Booking.objects.filter(
            status=Booking.Status.CANCELLED
        ).count(),
    })


@login_required
@require_POST
def booking_approve(request, booking_id):
    if not can_manage_bookings(request.user):
        messages.error(request, "You are not authorised to approve bookings.")
        return redirect("core:home")

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update().select_related("route"),
            pk=booking_id,
        )

        # Lock the route so concurrent approvals cannot overbook it.
        route = get_object_or_404(
            FlightRoute.objects.select_for_update().select_related("aircraft"),
            pk=booking.route_id,
        )

        if booking.status != Booking.Status.PENDING:
            messages.warning(
                request,
                "Only pending bookings can be approved."
            )
        elif not route.is_active:
            messages.error(
                request,
                "This flight route is inactive. The booking was not approved."
            )
        elif route.departure_datetime <= timezone.now():
            messages.error(
                request,
                "This flight has already reached its departure time."
            )
        else:
            occupied = Booking.objects.filter(
                route=route,
                status__in=[
                    Booking.Status.PENDING,
                    Booking.Status.APPROVED,
                ],
            ).count()

            if occupied > route.aircraft.passenger_capacity:
                messages.error(
                    request,
                    "The flight booking count exceeds its capacity. "
                    "Please review the bookings."
                )
            elif occupied == 0:
                messages.error(
                    request,
                    "No active seat reservation was found for this booking."
                )
            else:
                booking.status = Booking.Status.APPROVED
                booking.authorizing_staff = request.user
                booking.save(
                    update_fields=[
                        "status",
                        "authorizing_staff",
                        "updated_at",
                    ]
                )
                messages.success(
                    request,
                    f"Booking {booking.ticket_number} approved successfully."
                )

    return redirect("core:booking_list")


@login_required
@require_POST
def booking_cancel(request, booking_id):
    if not can_manage_bookings(request.user):
        messages.error(request, "You are not authorised to cancel bookings.")
        return redirect("core:home")

    with transaction.atomic():
        booking = get_object_or_404(
            Booking.objects.select_for_update(),
            pk=booking_id,
        )

        if booking.status == Booking.Status.CANCELLED:
            messages.warning(request, "This booking is already cancelled.")
        else:
            booking.status = Booking.Status.CANCELLED
            booking.save(update_fields=["status", "updated_at"])
            messages.success(
                request,
                f"Booking {booking.ticket_number} cancelled successfully."
            )

    return redirect("core:booking_list")


@login_required
def route_list(request):
    if not can_manage_flights(request.user):
        messages.error(request, "You cannot manage routes.")
        return redirect("core:home")

    routes = FlightRoute.objects.select_related("aircraft").all()

    return render(
        request,
        "core/route_list.html",
        {"routes": routes},
    )


@login_required
def route_create(request):
    if not can_manage_flights(request.user):
        messages.error(request, "You cannot create flight routes.")
        return redirect("core:home")

    aircraft = Aircraft.objects.filter(is_active=True)

    if request.method == "POST":
        aircraft_id = request.POST.get("aircraft")
        departure = request.POST.get("departure_airport", "").strip()
        destination = request.POST.get("destination_airport", "").strip()
        departure_time = request.POST.get("departure_datetime", "").strip()
        arrival_time = request.POST.get("arrival_datetime", "").strip()

        try:
            selected_aircraft = aircraft.get(pk=aircraft_id)
            departure_dt = timezone.datetime.fromisoformat(departure_time)
            arrival_dt = timezone.datetime.fromisoformat(arrival_time)

            if timezone.is_naive(departure_dt):
                departure_dt = timezone.make_aware(departure_dt)
            if timezone.is_naive(arrival_dt):
                arrival_dt = timezone.make_aware(arrival_dt)

            if not departure or not destination:
                raise ValueError("Enter both departure and destination airports.")

            if departure_dt <= timezone.now():
                raise ValueError("Departure must be in the future.")

            if arrival_dt <= departure_dt:
                raise ValueError("Arrival must be after departure.")

        except Aircraft.DoesNotExist:
            messages.error(request, "Select a valid active aircraft.")
        except (ValueError, TypeError):
            messages.error(
                request,
                "Enter valid airports and departure/arrival date and times."
            )
        else:
            FlightRoute.objects.create(
                aircraft=selected_aircraft,
                departure_airport=departure,
                destination_airport=destination,
                departure_datetime=departure_dt,
                arrival_datetime=arrival_dt,
            )
            messages.success(request, "Flight route created successfully.")
            return redirect("core:route_list")

    return render(
        request,
        "core/route_form.html",
        {"aircraft": aircraft},
    )


@login_required
def manifest_flights(request):
    profile = get_profile(request.user)

    if not (
        request.user.is_superuser
        or profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.MANIFEST,
        ]
    ):
        messages.error(request, "You are not authorised to access passenger flights.")
        return redirect("core:home")

    routes = FlightRoute.objects.filter(
        is_active=True,
        departure_datetime__gt=timezone.now(),
        aircraft__is_active=True,
    ).select_related("aircraft").order_by("departure_datetime")

    return render(request, "core/manifest_flights.html", {
        "profile": profile,
        "routes": routes,
    })


@login_required
def passenger_book(request):
    profile = get_profile(request.user)

    if not (
        request.user.is_superuser
        or profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.MANIFEST,
        ]
    ):
        messages.error(request, "You are not authorised to book flights.")
        return redirect("core:home")

    routes = FlightRoute.objects.filter(
        is_active=True,
        departure_datetime__gt=timezone.now(),
        aircraft__is_active=True,
    ).select_related("aircraft").order_by("departure_datetime")

    # Use the saved profile for the passenger's identity.
    first_name = profile.first_name or request.user.first_name
    last_name = profile.last_name or request.user.last_name
    middle_name = profile.middle_name
    rank = profile.rank
    service_number = request.user.username

    if request.method == "POST":
        route_id = request.POST.get("route")
        appointment = request.POST.get("appointment", "").strip()
        passenger_weight_raw = request.POST.get("passenger_weight_kg", "").strip()
        luggage_count_raw = request.POST.get("luggage_count", "0").strip()
        luggage_weight_raw = request.POST.get("luggage_weight_kg", "0").strip()

        errors = []
        selected_route = None
        passenger_weight = None
        luggage_count = 0
        luggage_weight = Decimal("0")

        try:
            selected_route = routes.get(pk=route_id)
        except (FlightRoute.DoesNotExist, ValueError, TypeError):
            errors.append("Select a valid available flight.")

        if not first_name or not last_name:
            errors.append(
                "Your first and last names must be saved in your profile before booking."
            )

        if passenger_weight_raw:
            try:
                passenger_weight = Decimal(passenger_weight_raw)
                if passenger_weight < 0:
                    raise InvalidOperation
            except (InvalidOperation, ValueError):
                errors.append("Passenger weight must be a valid non-negative number.")

        try:
            luggage_count = int(luggage_count_raw)
            if luggage_count < 0:
                raise ValueError
        except (ValueError, TypeError):
            errors.append("Luggage count must be zero or a positive whole number.")

        try:
            luggage_weight = Decimal(luggage_weight_raw)
            if luggage_weight < 0:
                raise InvalidOperation
        except (InvalidOperation, ValueError):
            errors.append("Luggage weight must be a valid non-negative number.")

        if luggage_count == 0 and luggage_weight > 0:
            errors.append("Enter a luggage count if you have luggage weight.")

        if selected_route and not errors:
            with transaction.atomic():
                route = FlightRoute.objects.select_for_update().select_related(
                    "aircraft"
                ).get(pk=selected_route.pk)

                active_bookings = Booking.objects.filter(
                    route=route,
                    status__in=[
                        Booking.Status.PENDING,
                        Booking.Status.APPROVED,
                    ],
                )

                already_booked = active_bookings.filter(
                    passenger=request.user
                ).exists()

                seat_count = active_bookings.count()

                if not route.is_active or not route.aircraft.is_active:
                    messages.error(request, "This flight is no longer available.")
                elif route.departure_datetime <= timezone.now():
                    messages.error(request, "This flight has already reached its departure time.")
                elif already_booked:
                    messages.error(request, "You already have an active booking for this flight.")
                elif seat_count >= route.aircraft.passenger_capacity:
                    messages.error(request, "This flight is full.")
                else:
                    total_weight = luggage_weight
                    if passenger_weight is not None:
                        total_weight += passenger_weight

                    if (
                        route.aircraft.maximum_payload_kg > 0
                        and total_weight > route.aircraft.maximum_payload_kg
                    ):
                        messages.error(
                            request,
                            "Passenger and luggage weight exceeds the aircraft's "
                            "configured maximum payload."
                        )
                    else:
                        Booking.objects.create(
                            passenger=request.user,
                            route=route,
                            service_number=service_number,
                            rank=rank,
                            first_name=first_name,
                            middle_name=middle_name,
                            last_name=last_name,
                            appointment=appointment,
                            passenger_weight_kg=passenger_weight,
                            luggage_count=luggage_count,
                            luggage_weight_kg=luggage_weight,
                            status=Booking.Status.PENDING,
                        )
                        messages.success(
                            request,
                            "Your booking request was submitted. "
                            "Check its status on the Check Booking page."
                        )
                        return redirect("core:my_bookings")

        for error in errors:
            messages.error(request, error)

    return render(request, "core/passenger_book.html", {
        "profile": profile,
        "routes": routes,
        "service_number": service_number,
        "rank": rank,
        "first_name": first_name,
        "middle_name": middle_name,
        "last_name": last_name,
    })


@login_required
def my_bookings(request):
    profile = get_profile(request.user)

    if not (
        request.user.is_superuser
        or profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.MANIFEST,
        ]
    ):
        messages.error(request, "You are not authorised to view these bookings.")
        return redirect("core:home")

    bookings = Booking.objects.filter(
        passenger=request.user
    ).select_related(
        "route",
        "route__aircraft",
        "authorizing_staff",
    ).order_by("-created_at")

    return render(request, "core/my_bookings.html", {
        "profile": profile,
        "bookings": bookings,
    })


@login_required
def official_seat_reservations(request):
    if not can_manage_flights(request.user):
        messages.error(
            request,
            "You are not authorised to manage seat reservations."
        )
        return redirect("core:home")

    if request.method == "POST":
        route_id = request.POST.get("route")
        seats_text = request.POST.get("seats_reserved", "").strip()
        reason = request.POST.get("reason", "").strip()

        try:
            seats_to_reserve = int(seats_text)
            if seats_to_reserve < 1:
                raise ValueError
        except (ValueError, TypeError):
            messages.error(
                request, "Enter a valid number of seats greater than zero."
            )
            return redirect("core:official_seat_reservations")

        if not reason:
            messages.error(request, "Enter the reason for the reservation.")
            return redirect("core:official_seat_reservations")

        try:
            with transaction.atomic():
                route = get_object_or_404(
                    FlightRoute.objects.select_for_update()
                    .select_related("aircraft"),
                    pk=route_id,
                )

                if (
                    not route.is_active
                    or not route.aircraft.is_active
                    or route.departure_datetime <= timezone.now()
                ):
                    messages.error(
                        request,
                        "Seats can only be reserved on active future flights."
                    )
                else:
                    passenger_bookings = Booking.objects.filter(
                        route=route,
                        status__in=[
                            Booking.Status.PENDING,
                            Booking.Status.APPROVED,
                        ],
                    ).count()

                    existing_reservations = (
                        OfficialSeatReservation.objects.filter(
                            route=route,
                            is_active=True,
                        ).aggregate(total=Sum("seats_reserved"))["total"]
                        or 0
                    )

                    available = (
                        route.aircraft.passenger_capacity
                        - passenger_bookings
                        - existing_reservations
                    )

                    if seats_to_reserve > max(available, 0):
                        messages.error(
                            request,
                            f"Only {max(available, 0)} seats are available "
                            "for official reservation on this flight."
                        )
                    else:
                        OfficialSeatReservation.objects.create(
                            route=route,
                            seats_reserved=seats_to_reserve,
                            reason=reason,
                            reserved_by=request.user,
                        )
                        messages.success(
                            request,
                            f"{seats_to_reserve} seat(s) reserved successfully."
                        )

        except (ValueError, TypeError):
            messages.error(request, "Please select a valid flight.")

        return redirect("core:official_seat_reservations")

    upcoming_routes = FlightRoute.objects.filter(
        is_active=True,
        aircraft__is_active=True,
        departure_datetime__gt=timezone.now(),
    ).select_related("aircraft").order_by("departure_datetime")

    reservations = (
        OfficialSeatReservation.objects
        .filter(is_active=True)
        .select_related("route", "route__aircraft", "reserved_by")
    )

    return render(
        request,
        "core/official_seat_reservations.html",
        {
            "upcoming_routes": upcoming_routes,
            "reservations": reservations,
        },
    )


@login_required
@require_POST
def release_official_seat_reservation(request, reservation_id):
    if not can_manage_flights(request.user):
        messages.error(
            request,
            "You are not authorised to release seat reservations."
        )
        return redirect("core:home")

    with transaction.atomic():
        reservation = get_object_or_404(
            OfficialSeatReservation.objects.select_for_update(),
            pk=reservation_id,
        )

        if reservation.is_active:
            reservation.is_active = False
            reservation.released_at = timezone.now()
            reservation.save(
                update_fields=["is_active", "released_at"]
            )
            messages.success(
                request,
                f"{reservation.seats_reserved} seat(s) released successfully."
            )
        else:
            messages.warning(
                request, "This reservation has already been released."
            )

    return redirect("core:official_seat_reservations")


@login_required
def flight_reports(request):
    if not can_manage_flights(request.user):
        messages.error(
            request,
            "You are not authorised to access flight reports."
        )
        return redirect("core:home")

    
    search_query = request.GET.get("q", "").strip()
    selected_route_id = request.GET.get("route", "").strip()
    selected_status = request.GET.get("status", "ALL").upper()

    valid_statuses = [
        Booking.Status.APPROVED,
        Booking.Status.PENDING,
        Booking.Status.CANCELLED,
    ]

    if selected_status not in ["ALL", *valid_statuses]:
        selected_status = "ALL"


    routes = FlightRoute.objects.select_related("aircraft").all()

    # Search by aircraft name or tail number.
    if search_query:
        routes = routes.filter(
            Q(aircraft__name__icontains=search_query)
            | Q(aircraft__tail_number__icontains=search_query)
        )

    selected_route = None
    bookings = Booking.objects.none()

    passenger_count = 0
    total_luggage_count = 0
    total_passenger_weight = 0
    total_luggage_weight = 0

    if selected_route_id:
        selected_route = get_object_or_404(
            routes,
            pk=selected_route_id,
        )

        
        bookings = Booking.objects.filter(
            route=selected_route,
        ).select_related(
            "passenger",
            "authorizing_staff",
        ).order_by(
            "last_name",
            "first_name",
        )

        if selected_status != "ALL":
            bookings = bookings.filter(status=selected_status)


        totals = bookings.aggregate(
            passenger_weight=Sum("passenger_weight_kg"),
            luggage_weight=Sum("luggage_weight_kg"),
            luggage_count=Sum("luggage_count"),
        )

        passenger_count = bookings.count()
        total_luggage_count = totals["luggage_count"] or 0
        total_passenger_weight = totals["passenger_weight"] or 0
        total_luggage_weight = totals["luggage_weight"] or 0

    return render(
        request,
        "core/reports.html",
        {
            "routes": routes,
            "selected_route": selected_route,
            "bookings": bookings,
            "search_query": search_query,
            "selected_route_id": selected_route_id,
            "passenger_count": passenger_count,
            "total_luggage_count": total_luggage_count,
            "total_passenger_weight": total_passenger_weight,
            "total_luggage_weight": total_luggage_weight,
            "report_prepared_by": request.user,
            "selected_status": selected_status,
            "report_date": timezone.localdate(),
        }
    )
# added for forms ops



@login_required
def flight_record_create(request):
    profile = get_profile(request.user)

    permitted = (
        request.user.is_superuser
        or profile.role in [
            UserProfile.Role.ADMIN,
            UserProfile.Role.FLIGHTOPS,
        ]
    )

    if not permitted:
        messages.error(
            request,
            "You are not authorised to create flight records.",
        )
        return redirect("core:home")

    if request.method == "POST":
        form = FlightRecordForm(request.POST)

        if form.is_valid():
            record = form.save(commit=False)
            record.created_by = request.user

            # Fetch identity details from the authenticated account.
            record.service_number = request.user.username
            record.rank = profile.get_rank_display()
            record.personnel_name = (
                profile.full_name
                or " ".join(
                    part for part in [
                        profile.first_name or request.user.first_name,
                        profile.middle_name,
                        profile.last_name or request.user.last_name,
                    ]
                    if part
                )
            )

            record.save()

            messages.success(
                request,
                "Flight record saved successfully.",
            )
            return redirect("core:flight_record_create")
    else:
        form = FlightRecordForm()

    routes = (
        FlightRoute.objects
        .filter(
            is_active=True,
            aircraft__is_active=True,
            departure_datetime__gt=timezone.now(),
        )
        .select_related("aircraft")
        .order_by("departure_datetime")
    )

    route_details = [
        {
            "id": route.pk,
            "aircraft": route.aircraft.name,
            "tail_number": route.aircraft.tail_number,
            "departure": route.departure_airport,
            "destination": route.destination_airport,
            "departure_time": route.departure_datetime.isoformat(),
            "arrival_time": route.arrival_datetime.isoformat(),
        }
        for route in routes
    ]

    return render(
        request,
        "core/flight_record_form.html",
        {
            "form": form,
            "profile": profile,
            "service_number": request.user.username,
            "personnel_name": (
                profile.full_name
                or request.user.get_full_name()
                or request.user.username
            ),
            "rank_display": profile.get_rank_display(),
            "route_details": route_details,
        },
    )

# route added
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from .models import FlightRoute
from .forms import FlightRecordForm


@login_required
def flight_record_create(request):
    routes = (
        FlightRoute.objects
        .filter(is_active=True, aircraft__is_active=True)
        .select_related("aircraft")
        .order_by("departure_datetime")
    )

    if request.method == "POST":
        form = FlightRecordForm(request.POST)

        if form.is_valid():
            record = form.save(commit=False)
            record.created_by = request.user

            # Keep your existing profile and identity assignments here.
            record.save()

            messages.success(request, "Flight record saved successfully.")
            return redirect("flight_record_create")
    else:
        form = FlightRecordForm()

    route_details = {}

    for route in routes:
        duration = route.arrival_datetime - route.departure_datetime

        route_details[str(route.id)] = {
            "aircraft": route.aircraft.name,
            "tail_number": route.aircraft.tail_number,
            "departure": route.departure_airport,
            "destination": route.destination_airport,
            "scheduled_departure": route.departure_datetime.strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "scheduled_arrival": route.arrival_datetime.strftime(
                "%Y-%m-%dT%H:%M"
            ),
            "duration": str(duration),
        }

    return render(
        request,
        "core/flight_record_form.html",
        {
            "form": form,
            "routes": routes,
            "route_details": route_details,
        },
)

# def about_kois(request):
#     """Display information about the KOIS flight operations system."""
#     return render(request, "core/about.html")
