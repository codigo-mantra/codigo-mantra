from django.urls import path
from .views import *

urlpatterns = [
    path('', LandingPage.as_view(), name='index'), 
    path('about-us/', AboutUsPage.as_view(), name='about-us'),
    path('services/', ServicePage.as_view(), name='services'),
    
    # 2. FIX: Change the name here to 'service_detail'
    path('services/<slug:slug>/', ServicePage.as_view(), name='service_detail'),    
    path('contact-us/', ContactPage.as_view(), name=    'contact'),
    # path('schedule-call/', ScheduleCallPage.as_view(), name='schedule-call'),
    path('career/', CareerPage.as_view(), name='career'),
    path('career/apply/<str:job_id>/', CareerFormPage.as_view(), name='career-apply'),
    path('portfolio/', PortfolioPage.as_view(), name='portfolio'),
    path('portfolio/<str:pk>/', CaseStudyDetailPage.as_view(), name='case_study_detail'),
    path('newsletter/subscribe/', newsletter_subscribe, name='newsletter-subscribe'),
    
    # URL to intentionally trigger a 500 error for testing
    path('trigger-error/', trigger_error, name='trigger_error'),

    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-and-conditions/', TermsConditionsView.as_view(), name='terms-conditions'),

]

