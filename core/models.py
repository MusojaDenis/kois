
import uuid

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Count, Sum
from django.utils import timezone


class UserProfile(models.Model):

    class Role(models.TextChoices):
        ADMIN = "ADMIN", "System Administrator"
        BOOKING_ADMIN = "BOOKING_ADMIN", "Booking Administrator"
        MANIFEST = "MANIFEST", "Flight Booking & Manifest"
        FLIGHTOPS = "FLIGHTOPS", "Flight Authorization & Hours"
        MAINTENANCE = "MAINTENANCE", "Aircraft Maintenance"
        VIEWER = "VIEWER", "Read-only Viewer"

    class Rank(models.TextChoices):
        SENIOR_PRIVATE = "SENIOR_PRIVATE", "Senior Private"
        CORPORAL = "CORPORAL", "Corporal"
        SERGEANT = "SERGEANT", "Sergeant"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="kois_profile",
    )
    rank = models.CharField(
        max_length=20,
        choices=Rank.choices,
        blank=True,
    )
    first_name = models.CharField(max_length=100, blank=True)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    full_name = models.CharField(max_length=300, blank=True)
    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.VIEWER,
    )

    def __str__(self):
        return f"{self.user.username} - {self.get_role_display()}"


class Aircraft(models.Model):
    name = models.CharField(max_length=150)
    tail_number = models.CharField(max_length=30, unique=True)
    passenger_capacity = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    maximum_payload_kg = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        default=0,
    )
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.tail_number})"


class FlightRoute(models.Model):
    aircraft = models.ForeignKey(
        Aircraft,
        on_delete=models.PROTECT,
        related_name="routes",
    )
    departure_airport = models.CharField(max_length=150)
    destination_airport = models.CharField(max_length=150)
    departure_datetime = models.DateTimeField()
    arrival_datetime = models.DateTimeField()
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["departure_datetime"]

    def __str__(self):
        return (
            f"{self.aircraft.name}: {self.departure_airport} "
            f"to {self.destination_airport} "
            f"({self.departure_datetime:%Y-%m-%d %H:%M})"
        )

    @property
    def reserved_seats(self):
        return self.bookings.filter(
            status=Booking.Status.PENDING
        ).count()

    @property
    def occupied_seats(self):
        return self.bookings.filter(
            status=Booking.Status.APPROVED
        ).count()

    
    @property
    def available_seats(self):
        passenger_bookings = self.bookings.filter(
            status__in=[
                Booking.Status.PENDING,
                Booking.Status.APPROVED,
            ]
        ).count()

        official_reservations = (
            self.official_seat_reservations
            .filter(is_active=True)
            .aggregate(total=Sum("seats_reserved"))["total"]
            or 0
        )

        remaining = (
            self.aircraft.passenger_capacity
            - passenger_bookings
            - official_reservations
        )

        return max(remaining, 0)


    


class Booking(models.Model):

    class Status(models.TextChoices):
        PENDING = "PENDING", "Pending approval"
        APPROVED = "APPROVED", "Approved"
        CANCELLED = "CANCELLED", "Cancelled"

    ticket_number = models.CharField(
        max_length=40,
        unique=True,
        blank=True,
    )
    passenger = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="kois_bookings",
    )
    route = models.ForeignKey(
        FlightRoute,
        on_delete=models.PROTECT,
        related_name="bookings",
    )

    # Passenger information captured at booking time.
    service_number = models.CharField(max_length=150)
    rank = models.CharField(max_length=20, blank=True)
    first_name = models.CharField(max_length=100)
    middle_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100)
    appointment = models.CharField(max_length=150, blank=True)

    passenger_weight_kg = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        validators=[MinValueValidator(0)],
    )
    luggage_count = models.PositiveIntegerField(default=0)
    luggage_weight_kg = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        default=0,
        validators=[MinValueValidator(0)],
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    authorizing_staff = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="kois_authorized_bookings",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["created_at"]

    def save(self, *args, **kwargs):
        if not self.ticket_number:
            self.ticket_number = (
                "KOIS-" + uuid.uuid4().hex[:12].upper()
            )
        super().save(*args, **kwargs)

    @property
    def passenger_full_name(self):
        return " ".join(
            part for part in [
                self.first_name,
                self.middle_name,
                self.last_name,
            ] if part
        )

    def __str__(self):
        return f"{self.ticket_number} - {self.service_number}"


class OfficialSeatReservation(models.Model):
    route = models.ForeignKey(
        FlightRoute,
        on_delete=models.PROTECT,
        related_name="official_seat_reservations",
    )
    seats_reserved = models.PositiveIntegerField(
        validators=[MinValueValidator(1)]
    )
    reason = models.CharField(max_length=255)
    reserved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name="kois_official_seat_reservations",
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    released_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return (
            f"{self.route} - {self.seats_reserved} official seats"
        )
