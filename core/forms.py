
from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

# added for ops
from django import forms
from .models import FlightRecord, FlightRoute
# end

from .models import UserProfile

User = get_user_model()


class KOISSignUpForm(UserCreationForm):

    # Django's username field will hold the service number.
    username = forms.CharField(
        max_length=150,
        label="Service Number",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter service number",
                "autocomplete": "username",
            }
        ),
    )

    rank = forms.ChoiceField(
        choices=UserProfile.Rank.choices,
        label="Rank",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    first_name = forms.CharField(
        max_length=100,
        label="First Name",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    middle_name = forms.CharField(
        max_length=100,
        label="Middle Name",
        required=False,
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    last_name = forms.CharField(
        max_length=100,
        label="Last Name",
        widget=forms.TextInput(attrs={"class": "form-control"}),
    )

    email = forms.EmailField(
        label="Email Address",
        widget=forms.EmailInput(attrs={"class": "form-control"}),
    )

    phone_number = forms.CharField(
        max_length=20,
        label="Phone Number",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "e.g. 0712345678",
            }
        ),
    )

    class Meta:
        model = User
        fields = (
            "username",
            "rank",
            "first_name",
            "middle_name",
            "last_name",
            "email",
            "phone_number",
            "password1",
            "password2",
        )

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError(
                "An account with this email already exists."
            )

        return email

    def save(self, commit=True):
        user = super().save(commit=False)

        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"].strip()

        if commit:
            user.save()

            first_name = self.cleaned_data["first_name"].strip()
            middle_name = self.cleaned_data["middle_name"].strip()
            last_name = self.cleaned_data["last_name"].strip()

            full_name = " ".join(
                name
                for name in [first_name, middle_name, last_name]
                if name
            )

            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "rank": self.cleaned_data["rank"],
                    "first_name": first_name,
                    "middle_name": middle_name,
                    "last_name": last_name,
                    "full_name": full_name,
                    "phone_number": self.cleaned_data["phone_number"].strip(),
                    "role": UserProfile.Role.VIEWER,
                },
            )

        return user


class KOISLoginForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        label="Service Number",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter service number",
                "autocomplete": "username",
            }
        ),
    )

    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(
            attrs={
                "class": "form-control",
                "placeholder": "Enter password",
                "autocomplete": "current-password",
            }
        ),
    )

# added for ops



class FlightRecordForm(forms.ModelForm):
    class Meta:
        model = FlightRecord
        fields = [
            # Section 2: Pilot, Students and Passengers
            "crew_names",
            "student_names",
            "passenger_names",

            # Other flight details
            "officer_name_initial",
            "captain_name_initial",

            # Section 3: Actual Flight Times
            "actual_takeoff",
            "actual_landing",
            "day_hours",
            "night_hours",

            # Flight details
            "instrument_flying",
            "approach_aid",
            "pax",
            "frt",
            "xty",
            "xx",
            "remarks",
            "number_of_landings",
            "captains_initials",
        ]

        widgets = {
            "crew_names": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "student_names": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "passenger_names": forms.Textarea(
                attrs={"class": "form-control", "rows": 3}
            ),
            "actual_takeoff": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
            ),
            "actual_landing": forms.DateTimeInput(
                format="%Y-%m-%dT%H:%M",
                attrs={
                    "type": "datetime-local",
                    "class": "form-control",
                },
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Accept the format used by datetime-local inputs.
        for field_name in ("actual_takeoff", "actual_landing"):
            self.fields[field_name].input_formats = [
                "%Y-%m-%dT%H:%M",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d %H:%M",
            ]

        # Apply Bootstrap styling to all fields.
        for field in self.fields.values():
            existing_class = field.widget.attrs.get("class", "")
            if "form-control" not in existing_class:
                field.widget.attrs["class"] = (
                    existing_class + " form-control"
                ).strip()
