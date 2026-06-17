from django.urls import path
from .views import *
# from .views import zoho_callback
urlpatterns = [
    path('', LandingPage.as_view(), name='index'), 
    path('about-us/', AboutUsPage.as_view(), name='about-us'),
    path('services/', ServicePage.as_view(), name='services'),
    
    path('services/<slug:slug>/', ServiceDetailsView.as_view(), name='service_detail'),
    path('industry/<slug:slug>/', IndustryDetailsView.as_view(), name='industry_detail'),    
    path('contact-us/', ContactPage.as_view(), name=    'contact'),
    path('schedule-call/', ScheduleCallPage.as_view(), name='schedule-call'),
    path('schedule-call/step-2/', ScheduleCallStep2Page.as_view(), name='schedule-call-2'),
    path('career/', CareerPage.as_view(), name='career'),
    path('career/apply/<str:job_id>/', CareerFormPage.as_view(), name='career-apply'),
    path('portfolio/', PortfolioPage.as_view(), name='portfolio'),
    path('portfolio/<str:pk>/', CaseStudyDetailPage.as_view(), name='case_study_detail'),
    path('newsletter/subscribe/', newsletter_subscribe, name='newsletter-subscribe'),
    # URL to intentionally trigger a 500 error for testing
    path('trigger-error/', trigger_error, name='trigger_error'),
    path('privacy-policy/', PrivacyPolicyView.as_view(), name='privacy-policy'),
    path('terms-and-conditions/', TermsConditionsView.as_view(), name='terms-conditions'),
    path('service-details/', ServiceDetailsView.as_view(), name='service-details'),
    path('service-details/<slug:slug>/', ServiceDetailsView.as_view(), name='service-details-slug'),
    path('industry-details/',IndustryDetailsView.as_view(), name='industry-details'),
    path('industry-details/<slug:slug>/', IndustryDetailsView.as_view(), name='industry-details-slug'),
    

    # path("zoho/callback/", zoho_callback),/


]

