from website.models import Industry, Service, CaseStudy , CompanyContact, SocialMediaHandle
from django.shortcuts import render, redirect
from django.conf import settings
from .forms import NewsletterForm
def navbar_context(request):
    """Global context available in all templates"""
    # industries = Industry.objects.all().values("name", "slug")
    services = Service.objects.all().order_by("display_order")[:12].values("name","slug")
    case_study = CaseStudy.objects.values(
        "title", "slug", "content", "cover_image"
    ).first()
    # if case_study and case_study["cover_image"]:
    #     case_study["cover_image"] = request.build_absolute_uri(
    #         settings.MEDIA_URL + case_study["cover_image"]
    #     )
    contact = CompanyContact.objects.first()
    social_handles = SocialMediaHandle.objects.all()
    newsletter_form = NewsletterForm()
    industries = Industry.objects.all()[:12].values("name", "slug")
    return {
        # 'industries': industries,
        'services_nav': services,
        "case_study_nav":case_study,
        'contact': contact,
        'social_handles': social_handles,
        "newsletter_form":newsletter_form,
        "industries_nav": industries,
    }



# def footer_context(request):
#     """Global context available in all templates"""
#     contact = CompanyContact.objects.first()
#     social_handles = SocialMediaHandle.objects.all()
#     return {
       
#         "case_study":case_study
#     }
