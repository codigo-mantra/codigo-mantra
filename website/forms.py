from django import forms
# from django_recaptcha.fields import ReCaptchaField
# from django_recaptcha.widgets import ReCaptchaV2Checkbox 
from .models import ContactUs, Newsletter, Application, Booking, User
import datetime




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
    # These fields are for the client User model
    client_name = forms.CharField(max_length=255, label="Full name")
    client_email = forms.EmailField(label="Email address")

    class Meta:
        model = Booking
        fields = ['booking_date', 'start_time', 'service_requested', 'project_brief']
        widgets = {
            'booking_date': forms.DateInput(attrs={'type': 'date'}),
            'start_time': forms.TimeInput(attrs={'type': 'time'}),
            'service_requested': forms.TextInput(attrs={'placeholder': 'Mention service here'}),
            'project_brief': forms.Textarea(attrs={'placeholder': 'Please describe your project in detail that will help prepare for our meeting'}),
        }


class ContactUsForm(forms.ModelForm):

    class Meta:
        model = ContactUs
        fields = ['first_name', 'last_name', 'email', 'phone', 'message']

        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'First name'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'Last name'}),
            'email': forms.EmailInput(attrs={'placeholder': 'Email address'}),
            'phone': forms.TextInput(attrs={'placeholder': 'Phone number(+91XXXXXXXXXX)'}),
            'message': forms.Textarea(attrs={'placeholder': 'Message'}),
        }

class NewsletterForm(forms.ModelForm):
    class Meta:
        model = Newsletter
        fields = ['email']


class CareerApplicationForm(forms.ModelForm):
    class Meta:
        model = Application
        fields = ['name', 'email', 'phone', 'resume']
