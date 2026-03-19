from django import forms
# from django_recaptcha.fields import ReCaptchaField
# from django_recaptcha.widgets import ReCaptchaV2Checkbox 
from .models import ContactUs, Newsletter, Application




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
