from django import forms
# from django_recaptcha.fields import ReCaptchaField
# from django_recaptcha.widgets import ReCaptchaV2Checkbox 
from .models import ContactUs, Newsletter, Application, Booking, User
import datetime
import re

from django import forms
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class BookingForm(forms.ModelForm):

    client_name = forms.CharField(
        max_length=255,
        label="Full name",
        error_messages={"required": "Full name is required."}
    )

    client_email = forms.EmailField(
        label="Email address",
        error_messages={
            "required": "Email address is required.",
            "invalid": "Please enter a valid email address.",
        },
    )

    phone_number = forms.CharField(
        max_length=10,
        label="Phone Number",
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter 10-digit phone number',
            'maxlength': '10'
        }),
        error_messages={
            "required": "Phone number is required."
        }
    )

    project_brief = forms.CharField(
        required=False,     # <-- OPTIONAL
        widget=forms.Textarea(
            attrs={
                'placeholder': 'Please describe your project',
                'style': 'resize: none;'
            }
        )
    )

    class Meta:
        model = Booking
        fields = ['booking_date', 'start_time', 'phone_number', 'project_brief']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
        }
        error_messages = {
            'booking_date': {
                'required': 'Please select a date.'
            },
            'start_time': {
                'required': 'Please select a time.'
            },
            'phone_number': {
                'required': 'Phone number is required.'
            }
        }

    # -------------------------------
    # CUSTOM VALIDATION METHODS
    # -------------------------------

    def clean_client_name(self):
        name = self.cleaned_data.get('client_name')

        if not re.match(r'^[A-Za-z ]+$', name):
            raise forms.ValidationError("Name must contain letters only.")

        return name

    def clean_phone_number(self):
        phone = self.cleaned_data.get('phone_number')

        # Only EXACT 10 digits allowed
        if not re.match(r'^[0-9]{10}$', phone):
            raise forms.ValidationError("Phone number must be exactly 10 digits.")

        return phone


    def clean_project_brief(self):
        message = self.cleaned_data.get('project_brief', '')

        # Validate only if not empty (it's optional)
        # if message and len(message.strip()) < 5:
        #     raise forms.ValidationError("Message is too short.")

        return message

class ContactUsForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['last_name'].required = False


    class Meta:
        model = ContactUs
        fields = ['first_name', 'last_name', 'email', 'phone', 'message']

        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone Number'}),
            'message': forms.Textarea(attrs={'placeholder': 'Message', 'style': 'resize: none;'}),
        }

        error_messages = {
            'first_name': {'required': 'This field is required.'},
            'last_name': {'required': 'This field is required.'},
            'email': {
                'required': 'This field is required.',
                'invalid': 'Please enter a valid email address.'
            },
            'phone': {'required': 'This field is required.'},
            'message': {'required': 'This field is required.'},
        }

    # -------------------------
    # CUSTOM VALIDATION
    # -------------------------

    def clean_first_name(self):
        first_name = self.cleaned_data.get('first_name')
        if not re.match(r'^[A-Za-z ]+$', first_name):
            raise forms.ValidationError("Please enter a valid first name.")
        return first_name

    def clean_last_name(self):
        last_name = (self.cleaned_data.get('last_name') or '').strip()
        if not last_name:
            return ''
        if not re.match(r'^[A-Za-z ]+$', last_name):
            raise forms.ValidationError("Please enter a valid last name.")
        return last_name

    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        if not phone:
            raise forms.ValidationError("Phone number is required.")

        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        if digits == "0" * 10:
            raise forms.ValidationError("Phone number cannot be all zeros.")

        return digits

    def clean_message(self):
        message = self.cleaned_data.get('message')
        # allow numbers + alphabets + punctuation
        if not re.search(r'[A-Za-z0-9]', message):
            raise forms.ValidationError("Please enter a valid message.")
        return message
    
class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ['email']
    def clean_email(self):
        email = self.cleaned_data.get('email', '').strip().lower()

        if email.startswith(("-", ".", "_")):
            raise forms.ValidationError("Email cannot start with special characters.")

        # Django's built-in validate_email is enough — drop the custom regex
        try:
            validate_email(email)
        except ValidationError:
            raise forms.ValidationError("Enter a valid email address.")

        return email

class CareerApplicationForm(forms.ModelForm):
    last_name = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={'placeholder': 'Last name'}),
        # error_messages={'required': 'This field is required.'}
    )

    class Meta:
        model = Application
        fields = ['name', 'email', 'phone', 'resume']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'First name', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address', 'required': 'required'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone Number', 'required': 'required'}),
            'resume': forms.FileInput(attrs={'required': 'required'}),
        }
        error_messages = {
            'name': {'required': 'This field is required.'},
            'email': {'required': 'This field is required.'},
            'phone': {'required': 'This field is required.'},
            'resume': {'required': 'This field is required.'},
        }

    # FIRST NAME VALIDATION
    def clean_name(self):
        name = self.cleaned_data.get('name')
        if not re.match(r'^[A-Za-z ]+$', name):
            raise forms.ValidationError("Please enter a valid first name.")
        return name

    # LAST NAME VALIDATION
    def clean_last_name(self):
        last_name = (self.cleaned_data.get('last_name') or '').strip()
        if not last_name:
            return ''
        if not re.match(r'^[A-Za-z ]+$', last_name):
            raise forms.ValidationError("Please enter a valid last name.")
        return last_name

    def save(self, commit=True):
        instance = super().save(commit=False)
        last_name = self.cleaned_data.get('last_name')
        if last_name:
            instance.name = f"{instance.name} {last_name}"
        if commit:
            instance.save()
        return instance

    # PHONE VALIDATION
    def clean_phone(self):
        phone = self.cleaned_data.get("phone")

        if not phone:
            raise forms.ValidationError("Phone number is required.")

        digits = "".join(c for c in phone if c.isdigit())
        if len(digits) != 10:
            raise forms.ValidationError("Phone number must be exactly 10 digits.")
        if digits == "0" * 10:
            raise forms.ValidationError("Phone number cannot be all zeros.")

        return digits

    # RESUME VALIDATION
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')

        if not resume:
            raise forms.ValidationError("Please upload your resume.")

        # SIZE LIMIT 5MB
        if resume.size > 5 * 1024 * 1024:
            raise forms.ValidationError("File size must be less than 5MB.")

        allowed_ext = ['pdf', 'doc', 'docx']
        ext = resume.name.split('.')[-1].lower()

        if ext not in allowed_ext:
            raise forms.ValidationError("Only PDF, DOC, or DOCX files are allowed.")

        return resume
