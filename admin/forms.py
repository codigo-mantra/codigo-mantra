from django import forms


class ContactUsForm(forms.Form):
    name = forms.CharField(max_length=150, required=True, min_length=4)
    email = forms.EmailField( required=True)
    contact = forms.CharField( max_length=15, required=True, min_length=10)
    subject = forms.CharField( max_length=500, required=True, min_length=8)
    message = forms.CharField(widget=forms.Textarea(attrs={'name':'body', 'rows':3, 'cols':5}))
