from website.models import Industry, Service, CaseStudy , CompanyContact, SocialMediaHandle
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import NewsletterForm
from decouple import config

BASE_URL = config("BASE_URL")

def navbar_context(request):
    """Global context available in all templates"""
    # Fetch top-level services (categories) and their children
    services = Service.objects.filter(parent__isnull=True).order_by("display_order").prefetch_related('children')
    
    # Specific case studies for navbar sections
    bells_crm = CaseStudy.objects.filter(title__icontains='BellsCRM').first()

    if bells_crm:
        bells_crm = {
            "title": bells_crm.title,
            "slug": bells_crm.slug,
            "content": bells_crm.content,
            "url": bells_crm.url,
            "cover_image": bells_crm.cover_image, 
        }
    
    yurayi = CaseStudy.objects.filter(title__icontains='Yurayi').first()
    # .values(
    #     "title", "slug", "content", "cover_image", "url"
    # ).first()

    if yurayi:
        yurayi = {
            "title": yurayi.title,
            "slug": yurayi.slug,
            "content": yurayi.content,
            "url": yurayi.url,
            "cover_image": yurayi.cover_image, 
        }

    # Default fallback
    case_study = bells_crm or yurayi or CaseStudy.objects.values(
        "title", "slug", "content", "cover_image", "url"
    ).first()

    contact = CompanyContact.objects.first()
    social_handles = SocialMediaHandle.objects.all()
    newsletter_form = NewsletterForm()
    industries = Industry.objects.all()[:12].values("name", "slug")
    return {
        'services_nav': services,
        "case_study_nav": case_study,
        "bells_crm_nav": bells_crm,
        "yurayi_nav": yurayi,
        'contact': contact,
        'social_handles': social_handles,
        "newsletter_form": newsletter_form,
        "industries_nav": industries,
    }

# def footer_context(request):
#     """Global context available in all templates"""
#     contact = CompanyContact.objects.first()
#     social_handles = SocialMediaHandle.objects.all()
#     return {
       
#         "case_study":case_study
#     }


def canonical_url(request):
    if request.path == "/":
        url = BASE_URL
    else:
        url = f"{BASE_URL}{request.path}"

    return {
        "canonical_url": url
    }