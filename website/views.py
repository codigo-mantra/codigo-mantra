from django.shortcuts import render,redirect
from django.core.mail import send_mail
from django.http import JsonResponse
from django.conf import settings
from .forms import ContactUsForm, CareerApplicationForm, NewsletterForm
from django import views
from django.contrib import messages
from .models import * 
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator

# Custom error views
def error_404_view(request, exception=None):
    return render(request, 'website/404-error.html', status=404)

def error_500_view(request):
    return render(request, 'website/500-error.html', status=500)

def trigger_error(request):
    """View to intentionally trigger a 500 error for testing."""
    raise Exception("This is a test 500 error triggered by the developer.")


# @method_decorator(cache_page(60 * 5), name='dispatch')
class LandingPage(views.View):
    def get(self,request):
        form = ContactUsForm()
        services = Service.objects.all().order_by('display_order')[:6].values("name", "description", "icon")  # last 6 services
        insights = Insight.objects.all().order_by('-created_at')[:3]  # last 3 insights
        testimonials_qs = list(Testimonial.objects.all().order_by('-created_at')[:6])  # last 6 testimonials
        # Ensure image testimonials appear before video testimonials (preserve recency within each group)
        testimonials = sorted(testimonials_qs, key=lambda t: t.media_type == "video")
        industries = Industry.objects.all().values("name", "svg_icon")  # all industries with svg icons
        case_studies = CaseStudy.objects.all().order_by('-created_at')[:3].prefetch_related(
            "services", "industries", "images"
        )  # last 3 case studies
        return render(request,'website/index.html',{'form':form, 'services':services, 'insights':insights, 'testimonials':testimonials, 'industries':industries, 'case_studies':case_studies})
    def post(self,request):
            form = ContactUsForm(data = request.POST)
            if form.is_valid():
                name = form.cleaned_data.get('name','') or ''
                fromEmail = form.cleaned_data.get('email','') or ''
                subject = form.cleaned_data.get('subject','') or ''
                contact = form.cleaned_data.get('contact','') or ''
                message = form.cleaned_data.get('message','')
                # toEmail='codigomantra@gmail.com'
                toEmail = "akshit.codigomantra@gmail.com"
                message= "Client Name is :  "+name+" , email is : "+fromEmail+" , contact number is : "+contact + " and message is : "+message
                send_mail(subject,message,settings.EMAIL_HOST_USER,[toEmail])
                messages.success(request,'Thank you for contacting us.')
                return redirect('index')
            print(form.errors)
            return render(request,'website/index.html',{'form':form})



class AboutUsPage(views.View):
    def get(self,request):
        team_members = TeamMember.objects.all().order_by('created_at')
        services = Service.objects.all()[:3].values("name", "description", "icon")
        workspace_images = CompanyEventImage.objects.all().order_by('created_at')
        return render(request,'website/about.html',{'team_members':team_members, 'services':services, 'workspace_images':workspace_images})

    
class ServicePage(views.View):
    def get(self,request):
        industries = Industry.objects.all().values("name", "svg_icon")  # all industries with svg icons
        services = Service.objects.all().order_by('display_order')
        return render(request,'website/services.html',{'services':services, 'industries':industries})
    

class CareerPage(views.View):
    def get(self,request):
        job_openings = JobOpening.objects.all().order_by('-created_at')
        services = Service.objects.all()[:3].values("name", "description", "icon")
        return render(request,'website/career.html',{'job_openings':job_openings, 'services':services})

class CareerFormPage(views.View):
    def get(self,request, job_id):
        try:
            job = JobOpening.objects.get(id=job_id)
            similar_jobs = JobOpening.objects.filter(job_type=job.job_type, department = job.department).exclude(id=job_id)[:2]
        except JobOpening.DoesNotExist:
            # messages.error(request, 'Job opening not found.')
            return redirect('career')

        form = CareerApplicationForm()
        return render(request,'website/career_form.html',{'form':form, 'job':job, 'similar_jobs':similar_jobs})
    
    
    def post(self, request, job_id):
        try:
            job = JobOpening.objects.get(id=job_id)
        except JobOpening.DoesNotExist:
            print("Job opening not found.")
            return redirect('career')

        form = CareerApplicationForm(request.POST, request.FILES)

        if form.is_valid():
            application = form.save(commit=False)
            application.job = job
            application.save()
            print("Application submitted successfully.")
            return redirect("career")

        return render(request, 'website/career_form.html', {'form': form, 'job': job})
    

class PortfolioPage(views.View):
    def get(self,request):
        case_studies = CaseStudy.objects.all().order_by('-created_at').prefetch_related(
            "services", "industries", "images"
        )
        industries = Industry.objects.all().values("name") 
        # technologies = Technology.objects.all().values("name")
        filtered_case_studies = []

        return render(request,'website/portfolio.html',{'case_studies':case_studies, 'industries':industries})
    

class CaseStudyDetailPage(views.View):
    def get(self,request, pk):

        case_studies = CaseStudy.objects.all().order_by('-created_at').prefetch_related(
            "services", "industries", "images"
        )
        try:
            case_study = CaseStudy.objects.get(pk=pk)
        except CaseStudy.DoesNotExist:
            print("Case study not found.")
            return redirect('portfolio')

        return render(request,'website/portfolio_details.html',{'case_study':case_study, 'case_studies':case_studies})
    

class ContactPage(views.View):
    def get(self,request):
        form = ContactUsForm()
        faqs = FAQ.objects.all()
        return render(request,'website/contact.html',{'form':form, 'faqs':faqs})
    
    def post(self, request):
        form = ContactUsForm(request.POST)

        if form.is_valid():
            form.save()
            print("Contact form submitted successfully.")
            return redirect('contact')

        return render(request, 'website/contact.html', {'form': form})
    


# class NewsletterSubscribeView(views.View):

#     def post(self, request):
#         form = NewsletterForm(request.POST)

#         if form.is_valid():
#             form.save()
#             print("Newsletter subscription successful.")
#             return JsonResponse({"success": True, "message": "Subscribed successfully!"})

#         return JsonResponse({"success": False, "errors": form.errors})


from django.contrib import messages
from django.shortcuts import redirect

def newsletter_subscribe(request):
    if request.method == "POST":
        form = NewsletterForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Subscribed!")
        else:
            messages.error(request, "Invalid email")

    return redirect(request.META.get('HTTP_REFERER', '/'))