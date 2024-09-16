from django import forms
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox 

class ContactUsForm(forms.Form):
    name = forms.CharField(max_length=150, required=True, min_length=4)
    email = forms.EmailField( required=True)
    contact = forms.CharField( max_length=15, required=True, min_length=10)
    subject = forms.CharField( max_length=500, required=True, min_length=8)
    message = forms.CharField(widget=forms.Textarea(attrs={'name':'body', 'rows':3, 'cols':5}))
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox) 

    def clean_captcha(self):
        captcha = self.cleaned_data.get('captcha')
        if not captcha:
            self.add_error('captcha','Captcha is required')
        return captcha
