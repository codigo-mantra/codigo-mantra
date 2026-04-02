from django import forms
# from django_recaptcha.fields import ReCaptchaField
# from django_recaptcha.widgets import ReCaptchaV2Checkbox 
from .models import ContactUs, Newsletter, Application, Booking, User
import datetime
import re



# class ContactUsForm(forms.Form):
#     # name = forms.CharField(max_length=150, required=True, min_length=4)
#     first_name = forms.CharField(max_length=100, required=True, min_length=2)
#     last_name = forms.CharField(max_length=100, required=True, min_length=2)
#     email = forms.EmailField( required=True)
#     contact = forms.CharField( max_length=15, required=True, min_length=10)
#     subject = forms.CharField( max_length=500, required=True, min_length=8)
#     message = forms.CharField(widget=forms.Textarea(attrs={'name':'body', 'rows':3, 'cols':5}))
#     # captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox) 

#     # def clean_captcha(self):
#     #     captcha = self.cleaned_data.get('captcha')
#     #     if not captcha:
#     #         self.add_error('captcha','Captcha is required')
#     #     return captcha


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

    class Meta:
        model = Booking
        fields = ['booking_date', 'start_time', 'service_requested', 'project_brief']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'service_requested': forms.TextInput(attrs={'placeholder': 'Mention service here'}),
            'project_brief': forms.Textarea(
                attrs={'placeholder': 'Please describe your project', 'style': 'resize: none;'}
            ),
        }
        error_messages = {
            'service_requested': {
                'required': 'Please mention the service you want.'
            },
            'project_brief': {
                'required': 'Please provide a message.'
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

    def clean_service_requested(self):
        service = self.cleaned_data.get('service_requested')
        if len(service) < 3:
            raise forms.ValidationError("Service name is too short.")
        return service

    def clean_project_brief(self):
        message = self.cleaned_data.get('project_brief')
        if len(message.strip()) < 5:
            raise forms.ValidationError("Message is too short.")
        return message


class ContactUsForm(forms.ModelForm):

    class Meta:
        model = ContactUs
        fields = ['first_name', 'last_name', 'email', 'phone', 'message']

        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number(+91XXXXXXXXXX)'}),
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
        last_name = self.cleaned_data.get('last_name')
        if not re.match(r'^[A-Za-z ]+$', last_name):
            raise forms.ValidationError("Please enter a valid last name.")
        return last_name

    def clean_phone(self):
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise forms.ValidationError("Phone number is required.")

        # Remove spaces
        phone = phone.replace(" ", "")

        # Must be digits only
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")

        # Must be exactly 11 digits
        if len(phone) != 11:
            raise forms.ValidationError("Phone number must be exactly 11 digits.")

        return phone

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


class CareerApplicationForm(forms.ModelForm):
    last_name = forms.CharField(
        max_length=100,
        required=True,
        widget=forms.TextInput(attrs={'placeholder': 'Last name', 'required': 'required'}),
        error_messages={'required': 'This field is required.'}
    )

    class Meta:
        model = Application
        fields = ['name', 'email', 'phone', 'resume']
        widgets = {
            'name': forms.TextInput(attrs={'placeholder': 'First name', 'required': 'required'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address', 'required': 'required'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number(+91XXXXXXXXXX)', 'required': 'required'}),
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
        last_name = self.cleaned_data.get('last_name')
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
        phone = self.cleaned_data.get('phone')

        if not phone:
            raise forms.ValidationError("Phone number is required.")

        # Remove spaces
        phone = phone.replace(" ", "")

        # Must be digits only
        if not phone.isdigit():
            raise forms.ValidationError("Phone number must contain digits only.")

        # Must be exactly 11 digits
        if len(phone) != 11:
            raise forms.ValidationError("Phone number must be exactly 11 digits.")

        return phone

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
