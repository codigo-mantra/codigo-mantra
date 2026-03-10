from django.urls import path
from admin.views import *
app_name = 'admin'

urlpatterns = [
    path('',LandingPage.as_view(),name='index'),   
    path('form/contact-us/', contactus_form_view, name='contact-us-form'), #yurayi contact us form 
]
