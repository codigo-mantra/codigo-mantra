from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import JsonResponse
from django.conf import settings
from .forms import ContactUsForm, CareerApplicationForm, NewsletterForm
from django import views
from django.contrib import messages
from .models import * 
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db import IntegrityError


# Custom error views
def error_404_view(request, exception=None):
    return render(request, 'website/404-error.html', status=404)

def error_500_view(request):
    return render(request, 'website/500-error.html', status=500)

def trigger_error(request):
    """View to intentionally trigger a 500 error for testing."""
    raise Exception("This is a test 500 error triggered by the developer.")



class PrivacyPolicyView(views.View):
    template_name = 'website/privacy-policy.html'

    def get(self, request):
        policy = PrivacyPolicy.objects.first()
        pdf_absolute_url = (
            request.build_absolute_uri(policy.pdf.url) if policy and policy.pdf else ''
        )
        return render(
            request,
            self.template_name,
            {'policy': policy, 'pdf_absolute_url': pdf_absolute_url},
        )


class TermsConditionsView(views.View):
    template_name = 'website/terms-conditions.html'

    def get(self, request):
        terms = TermsofService.objects.first()
        pdf_absolute_url = (
            request.build_absolute_uri(terms.pdf.url) if terms and terms.pdf else ''
        )
        return render(
            request,
            self.template_name,
            {'terms': terms, 'pdf_absolute_url': pdf_absolute_url},
        )


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
    def post(self, request):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = ContactUsForm(request.POST)

        if form.is_valid():
            contact_instance = form.save()
            
            name         = f"{contact_instance.first_name} {contact_instance.last_name}"
            from_email   = contact_instance.email
            phone        = contact_instance.phone
            message_body = contact_instance.message
            base_url     = request.build_absolute_uri('/')[:-1]

            admin_html_message = render_to_string('email-contact-admin.html', {
                'name': name, 'email': from_email,
                'phone': phone, 'message_body': message_body, 'base_url': base_url
            })
            html_message = render_to_string('email-contact.html', {
                'name': contact_instance.first_name, 'base_url': base_url
            })

            try:
                email = EmailMessage(
                    f"New Contact Form Submission from {name}",
                    admin_html_message,
                    settings.DEFAULT_FROM_EMAIL,
                    ["abbas.codigo@gmail.com"],
                    reply_to=[from_email],
                )
                email.content_subtype = "html"
                email.send(fail_silently=False)

                send_mail(
                    "Thank You for Reaching Out to Codigo Mantra!",
                    strip_tags(html_message),
                    settings.DEFAULT_FROM_EMAIL,
                    [from_email],
                    html_message=html_message,
                    fail_silently=False,
                )

            except Exception as e:
                print(f"Email error: {e}")
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

            # Return JSON for AJAX
            if is_ajax:
                return JsonResponse({'status': 'success'})

            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')

        # Form invalid
        if is_ajax:
            errors = {
                field: [{'message': str(e)} for e in errs]
                for field, errs in form.errors.items()
            }
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        return render(request, 'website/contact.html', {
            'form'   : form,
            'faqs'   : FAQ.objects.all(),
            'contact': ContactInfo.objects.first()
        })

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
        show_application_success = request.GET.get('success') == '1'
        return render(
            request,
            'website/career_form.html',
            {
                'form': form,
                'job': job,
                'similar_jobs': similar_jobs,
                'show_application_success': show_application_success,
            },
        )
    
    
    def post(self, request, job_id):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

        try:
            job = JobOpening.objects.get(id=job_id)
        except JobOpening.DoesNotExist:
            if is_ajax:
                return JsonResponse(
                    {'status': 'error', 'message': 'This job is no longer available.'},
                    status=404,
                )
            return redirect('career')

        form = CareerApplicationForm(request.POST, request.FILES)

        if not form.is_valid():
            if is_ajax:
                errors = {
                    field: [{'message': str(e)} for e in errs]
                    for field, errs in form.errors.items()
                }
                return JsonResponse({'status': 'error', 'errors': errors}, status=400)

            similar_jobs = JobOpening.objects.filter(
                job_type=job.job_type, department=job.department
            ).exclude(id=job_id)[:2]
            return render(
                request,
                'website/career_form.html',
                {
                    'form': form,
                    'job': job,
                    'similar_jobs': similar_jobs,
                    'show_application_success': False,
                },
            )

        application = form.save(commit=False)
        application.job = job
        application.save()

        name = application.name
        applicant_email = application.email
        phone = application.phone
        job_title = job.title

        user_html = render_to_string('email-application.html', {})
        admin_html = render_to_string('email-application-admin.html', {
            'name': name,
            'email': applicant_email,
            'job_title': job_title,
            'message_body': (
                f'Phone: {phone}\n\n'
                f'Resume is attached to this email for HR review.'
            ),
        })
        hr_recipients = ['abbas.codigo@gmail.com']

        email_warning = False
        try:
            admin_msg = EmailMessage(
                f'New job application: {name} — {job_title}',
                admin_html,
                settings.DEFAULT_FROM_EMAIL,
                hr_recipients,
                reply_to=[applicant_email],
            )
            admin_msg.content_subtype = 'html'
            if application.resume:
                try:
                    admin_msg.attach_file(application.resume.path)
                except Exception:
                    pass
            admin_msg.send(fail_silently=False)

            send_mail(
                f'Application received — {job_title}',
                strip_tags(user_html),
                settings.DEFAULT_FROM_EMAIL,
                [applicant_email],
                html_message=user_html,
                fail_silently=False,
            )
            messages.success(
                request,
                'Your application has been submitted successfully.',
            )
        except Exception as e:
            print(f'Application email error: {e}')
            email_warning = True
            messages.warning(
                request,
                'Your application was saved, but we could not send the emails. Our team will still review it.',
            )

        if is_ajax:
            payload = {'status': 'success'}
            if email_warning:
                payload['email_warning'] = True
            return JsonResponse(payload)

        return redirect(f"{reverse('career-apply', kwargs={'job_id': job_id})}?success=1")
    

class PortfolioPage(views.View):
    def get(self,request):
        case_studies = CaseStudy.objects.all().order_by('-created_at').prefetch_related(
            "services", "industries", "technologies", "images"
        )
        industries = Industry.objects.all()
        technologies = Technology.objects.all()
        featured_projects = case_studies.all()[:3]
        

        return render(request,'website/portfolio.html',{'case_studies':case_studies, 'industries':industries, 'technologies': technologies,'featured_projects': featured_projects})
    

class CaseStudyDetailPage(views.View):
    def get(self,request, pk):

        case_studies = CaseStudy.objects.all().order_by('-created_at').prefetch_related(
            "services", "industries", "technologies", "images"
        )
        try:
            case_study = CaseStudy.objects.get(pk=pk)
        except CaseStudy.DoesNotExist:
            print("Case study not found.")
            return redirect('portfolio')

        # Get exactly 3 other projects to avoid slice issues in template
        other_projects_list = case_studies.exclude(pk=pk)[:3]

        return render(request,'website/portfolio_details.html',{'case_study':case_study, 'case_studies':other_projects_list})

    

class ContactPage(views.View):
    def get(self,request):
        form = ContactUsForm()
        faqs = FAQ.objects.all()
        return render(request,'website/contact.html',{'form':form, 'faqs':faqs})
    
    def post(self, request):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = ContactUsForm(request.POST)

        if form.is_valid():
            contact_instance = form.save()
            
            name         = f"{contact_instance.first_name} {contact_instance.last_name}"
            from_email   = contact_instance.email
            phone        = contact_instance.phone
            message_body = contact_instance.message
            base_url     = request.build_absolute_uri('/')[:-1]

            admin_html_message = render_to_string('email-contact-admin.html', {
                'name': name, 'email': from_email,
                'phone': phone, 'message_body': message_body, 'base_url': base_url
            })
            html_message = render_to_string('email-contact.html', {
                'name': contact_instance.first_name, 'base_url': base_url
            })

            try:
                email = EmailMessage(
                    f"New Contact Form Submission from {name}",
                    admin_html_message,
                    settings.DEFAULT_FROM_EMAIL,
                    ["abbas.codigo@gmail.com"],
                    reply_to=[from_email],
                )
                email.content_subtype = "html"
                email.send(fail_silently=False)

                send_mail(
                    "Thank You for Reaching Out to Codigo Mantra!",
                    strip_tags(html_message),
                    settings.DEFAULT_FROM_EMAIL,
                    [from_email],
                    html_message=html_message,
                    fail_silently=False,
                )

            except Exception as e:
                print(f"Email error: {e}")
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

            # Return JSON for AJAX
            if is_ajax:
                return JsonResponse({'status': 'success'})

            messages.success(request, 'Your message has been sent successfully!')
            return redirect('contact')

        # Form invalid
        if is_ajax:
            errors = {
                field: [{'message': str(e)} for e in errs]
                for field, errs in form.errors.items()
            }
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        return render(request, 'website/contact.html', {
            'form'   : form,
            'faqs'   : FAQ.objects.all(),
            'contact': ContactInfo.objects.first()
        })
    


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

# def newsletter_subscribe(request):
#     if request.method == "POST":
#         form = NewsletterForm(request.POST)
#         if form.is_valid():
#             form.save()
#             messages.success(request, "Subscribed!")
#         else:
#             messages.error(request, "Invalid email")

#     return redirect(request.META.get('HTTP_REFERER', '/'))

def newsletter_subscribe(request):
    if request.method == "POST":
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        email   = request.POST.get('email', '').strip().lower()

        if not email:
            if is_ajax:
                return JsonResponse({'status': 'error', 'message': 'Email is required.'}, status=400)
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Helper to send email
        def send_welcome_email(email_to):
            try:
                html_message = render_to_string('email-newsletter.html', {
                    'email': email_to,
                    'base_url': request.build_absolute_uri('/')[:-1]
                })
                send_mail(
                    'Welcome to Codigo Mantra Newsletter!',
                    strip_tags(html_message),
                    settings.DEFAULT_FROM_EMAIL,
                    [email_to],
                    html_message=html_message,
                    fail_silently=False,
                )
            except Exception as e:
                print(f"Newsletter email error: {e}")

        # Handle duplicate silently — still show success to user
        if Newsletter.objects.filter(email=email).exists():
            send_welcome_email(email)
            if is_ajax:
                return JsonResponse({'status': 'success', 'already': True})
            messages.success(request, "You're already subscribed!")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        form = NewsletterForm(request.POST)

        if form.is_valid():
            try:
                form.save()
                
                # Send confirmation email
                send_welcome_email(email)

                if is_ajax:
                    return JsonResponse({'status': 'success', 'already': False})
                messages.success(request, "Subscribed successfully!")

            except IntegrityError:
                # Race condition safety net
                if is_ajax:
                    return JsonResponse({'status': 'success', 'already': True})
                messages.success(request, "You're already subscribed!")
        else:
            if is_ajax:
                return JsonResponse({
                    'status': 'error',
                    'message': 'Please enter a valid email address.'
                }, status=400)
            messages.error(request, "Invalid email.")

    return redirect(request.META.get('HTTP_REFERER', '/'))
