
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
            "route",
            "crew_names",
            "student_names",
            "passenger_names",
            "officer_name_initial",
            "captain_name_initial",
            "actual_takeoff",
            "actual_landing",
            "day_hours",
            "night_hours",
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
            "route": forms.Select(attrs={
                "class": "form-select",
            }),
            "crew_names": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Enter crew names",
            }),
            "student_names": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Enter student names",
            }),
            "passenger_names": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 2,
                "placeholder": "Enter passenger names",
            }),
            "officer_name_initial": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Officer name and initial",
            }),
            "captain_name_initial": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Captain name and initial",
            }),
            "actual_takeoff": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
            "actual_landing": forms.DateTimeInput(attrs={
                "class": "form-control",
                "type": "datetime-local",
            }),
            "day_hours": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }),
            "night_hours": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
                "step": "0.01",
            }),
            "instrument_flying": forms.Select(attrs={
                "class": "form-select",
            }),
            "approach_aid": forms.Select(attrs={
                "class": "form-select",
            }),
            "pax": forms.NumberInput(attrs={
                "class": "form-control", "min": "0",
            }),
            "frt": forms.NumberInput(attrs={
                "class": "form-control", "min": "0",
            }),
            "xty": forms.NumberInput(attrs={
                "class": "form-control", "min": "0",
            }),
            "xx": forms.NumberInput(attrs={
                "class": "form-control", "min": "0",
            }),
            "remarks": forms.Textarea(attrs={
                "class": "form-control", "rows": 3,
            }),
            "number_of_landings": forms.NumberInput(attrs={
                "class": "form-control", "min": "0",
            }),
            "captains_initials": forms.TextInput(attrs={
                "class": "form-control",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["route"].queryset = (
            FlightRoute.objects
            .filter(is_active=True, aircraft__is_active=True)
            .select_related("aircraft")
            .order_by("departure_datetime")
        )

    def clean(self):
        cleaned = super().clean()
        takeoff = cleaned.get("actual_takeoff")
        landing = cleaned.get("actual_landing")

        if takeoff and landing and landing < takeoff:
            self.add_error(
                "actual_landing",
                "Actual landing cannot be before actual take-off.",
            )

        return cleaned
