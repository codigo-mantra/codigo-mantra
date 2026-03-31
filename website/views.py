from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.mail import send_mail, EmailMessage
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.http import JsonResponse
from django.conf import settings
from .forms import ContactUsForm, CareerApplicationForm, NewsletterForm, BookingForm
from django import views
from django.contrib import messages
from .models import * 
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db import IntegrityError, close_old_connections, transaction
from .zoom_meet import generate_zoom_meet_link

# Google Meet (Calendar API): uncomment import and the fallback block in
# `_booking_followup_zoom_and_emails` to try Meet when Zoom returns no URL.
from .google_meet import generate_google_meet_link
import logging
import threading
import datetime
from datetime import timedelta

logger = logging.getLogger(__name__)


def _booking_followup_zoom_and_emails(booking_id, client_name, client_email):
    """Zoom + emails after commit — runs in a background thread so HTTP returns fast."""
    close_old_connections()
    try:
        booking = Booking.objects.select_related("consultant").get(pk=booking_id)
        consultant = booking.consultant

        if not booking.meet_link:
            # Try Google Meet first (user preference)
            meet_link = generate_google_meet_link(
                booking=booking,
                client_email=client_email,
            )
            # Fallback to Zoom if Google Meet fails
            if not meet_link:
                meet_link = generate_zoom_meet_link(
                    booking=booking,
                    client_email=client_email,
                )
            if meet_link:
                booking.meet_link = meet_link
                booking.save(update_fields=["meet_link"])
            else:
                logger.warning(
                    "Booking %s: meet_link not saved — both Google Meet and Zoom failed. "
                    "Check client_secret JSON and token.pickle for Meet, "
                    "or ZOOM_* credentials for Zoom fallback.",
                    booking.pk,
                )

        try:
            booking_date_str = booking.booking_date.strftime("%A, %B %d, %Y")
        except Exception:
            booking_date_str = str(booking.booking_date)

        try:
            booking_time_str = datetime.datetime.strptime(
                str(booking.start_time), "%H:%M:%S"
            ).strftime("%I:%M %p").lstrip("0")
        except Exception:
            booking_time_str = str(booking.start_time)

        client_html = render_to_string("call-email.html", {
            "name": client_name,
            "email": client_email,
            "date": booking_date_str,
            "time": booking_time_str,
            "meet_link": booking.meet_link,
        })
        admin_html = render_to_string("call-email-admin.html", {
            "name": client_name,
            "admin_name": consultant.name if consultant and consultant.name else "Admin",
            "email": client_email,
            "number": "N/A",
            "date": booking_date_str,
            "time": booking_time_str,
            "meet_link": booking.meet_link,
        })

        admin_recipients = list(getattr(settings, "BOOKING_ADMIN_EMAILS", None) or [])
        if not admin_recipients:
            host_user = getattr(settings, "EMAIL_HOST_USER", "") or ""
            if host_user:
                admin_recipients = [host_user]
        if not getattr(settings, "BOOKING_SINGLE_ADMIN_INBOX", True):
            if consultant and getattr(consultant, "email", None):
                ce = consultant.email.strip()
                if ce and ce not in admin_recipients:
                    admin_recipients.append(ce)
        admin_recipients = [e for e in admin_recipients if e]

        inbox = (getattr(settings, "EMAIL_HOST_USER", "") or "").strip().lower()
        client_lower = (client_email or "").strip().lower()

        try:
            client_msg = EmailMessage(
                "Your call is scheduled — Codigo Mantra",
                client_html,
                settings.DEFAULT_FROM_EMAIL,
                [client_email],
            )
            client_msg.content_subtype = "html"
            client_msg.send(fail_silently=False)
        except Exception as e:
            logger.warning("Booking: failed to email client %s: %s", client_email, e)

        # Same inbox as SMTP user: also receive the client-style mail when booker used another address
        if getattr(settings, "BOOKING_SINGLE_ADMIN_INBOX", True) and inbox and client_lower != inbox:
            try:
                copy_msg = EmailMessage(
                    "[Copy] Your call is scheduled — Codigo Mantra",
                    client_html,
                    settings.DEFAULT_FROM_EMAIL,
                    [getattr(settings, "EMAIL_HOST_USER", "")],
                )
                copy_msg.content_subtype = "html"
                copy_msg.send(fail_silently=False)
            except Exception as e:
                logger.warning("Booking: failed to copy client mail to admin %s: %s", inbox, e)

        if admin_recipients:
            try:
                admin_msg = EmailMessage(
                    f"New call scheduled — {client_name}",
                    admin_html,
                    settings.DEFAULT_FROM_EMAIL,
                    admin_recipients,
                    reply_to=[client_email],
                )
                admin_msg.content_subtype = "html"
                admin_msg.send(fail_silently=False)
            except Exception as e:
                logger.warning("Booking: failed to email admins %s: %s", admin_recipients, e)
        else:
            logger.warning(
                "Booking %s: no admin email recipients (set EMAIL_HOST_USER or BOOKING_ADMIN_EMAILS).",
                booking.pk,
            )
    except Booking.DoesNotExist:
        logger.warning("Booking follow-up: booking %s not found", booking_id)
    except Exception as e:
        logger.exception("Booking follow-up failed for %s: %s", booking_id, e)
    finally:
        close_old_connections()


def _contact_form_send_emails(name, from_email, phone, message_body, base_url, first_name):
    """SMTP for contact form — background thread."""
    close_old_connections()
    try:
        admin_html_message = render_to_string(
            "email-contact-admin.html",
            {
                "name": name,
                "email": from_email,
                "phone": phone,
                "message_body": message_body,
                "base_url": base_url,
            },
        )
        html_message = render_to_string(
            "email-contact.html",
            {"name": first_name, "base_url": base_url},
        )
        admin_addr = getattr(settings, "EMAIL_HOST_USER", "") or ""
        if not admin_addr:
            logger.warning("Contact form: EMAIL_HOST_USER not set; skipping admin notification")
        else:
            email = EmailMessage(
                f"New Contact Form Submission from {name}",
                admin_html_message,
                settings.DEFAULT_FROM_EMAIL,
                [admin_addr],
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
        logger.warning("Contact form email error: %s", e)
    finally:
        close_old_connections()


def _career_application_send_emails(application_id):
    """SMTP for job application — background thread."""
    close_old_connections()
    try:
        application = Application.objects.select_related("job").get(pk=application_id)
        job = application.job
        job_title = job.title
        name = application.name
        applicant_email = application.email
        phone = application.phone

        user_html = render_to_string("email-application.html", {})
        admin_html = render_to_string(
            "email-application-admin.html",
            {
                "name": name,
                "email": applicant_email,
                "job_title": job_title,
                "message_body": (
                    f"Phone: {phone}\n\n"
                    f"Resume is attached to this email for HR review."
                ),
            },
        )
        hr_addr = getattr(settings, "EMAIL_HOST_USER", "") or ""
        if not hr_addr:
            logger.warning("Career application: EMAIL_HOST_USER not set; skipping HR mail")
            return

        admin_msg = EmailMessage(
            f"New job application: {name} — {job_title}",
            admin_html,
            settings.DEFAULT_FROM_EMAIL,
            [hr_addr],
            reply_to=[applicant_email],
        )
        admin_msg.content_subtype = "html"
        if application.resume:
            try:
                admin_msg.attach_file(application.resume.path)
            except Exception as e:
                logger.warning("Career: could not attach resume: %s", e)
        admin_msg.send(fail_silently=False)

        send_mail(
            f"Application received — {job_title}",
            strip_tags(user_html),
            settings.DEFAULT_FROM_EMAIL,
            [applicant_email],
            html_message=user_html,
            fail_silently=False,
        )
    except Application.DoesNotExist:
        logger.warning("Career application: row %s not found", application_id)
    except Exception as e:
        logger.warning("Career application email error: %s", e)
    finally:
        close_old_connections()


def _newsletter_welcome_email(email_to, base_url):
    """Welcome email after newsletter subscribe — background thread."""
    close_old_connections()
    try:
        html_message = render_to_string(
            "email-newsletter.html",
            {"email": email_to, "base_url": base_url},
        )
        send_mail(
            "Welcome to Codigo Mantra Newsletter!",
            strip_tags(html_message),
            settings.DEFAULT_FROM_EMAIL,
            [email_to],
            html_message=html_message,
            fail_silently=False,
        )
    except Exception as e:
        logger.warning("Newsletter welcome email error for %s: %s", email_to, e)
    finally:
        close_old_connections()


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


class ScheduleCallPage(views.View):
    def get(self, request):
        form = BookingForm()
        faqs = FAQ.objects.all()
        return render(request, 'website/schedule_call1.html', {'form': form, 'faqs': faqs})


class ScheduleCallStep2Page(views.View):
    def get(self, request):
        form = BookingForm()
        faqs = FAQ.objects.all()
        return render(request, 'website/schedule_call2.html', {
            'form': form,
            'faqs': faqs
        })

    def post(self, request):
        is_ajax = request.headers.get('X-Requested-With') == 'XMLHttpRequest'
        form = BookingForm(request.POST)

        if form.is_valid():

            # Extract client info
            client_name = form.cleaned_data.get('client_name')
            client_email = form.cleaned_data.get('client_email')

            client, created = User.objects.get_or_create(
                email=client_email,
                defaults={'name': client_name, 'role': 'client', 'status': 'active'}
            )
            if client.name != client_name:
                client.name = client_name
                client.save(update_fields=['name'])

            consultant = User.objects.filter(role='consultant', status='active').first()
            if not consultant:
                consultant = User.objects.create(
                    name="Admin Consultant",
                    email="admin@codigomantra.com",
                    role="consultant",
                    status="active"
                )

            booking = form.save(commit=False)
            booking.client = client
            booking.consultant = consultant
            booking.status = 'pending'

            # -------------------------------
            # CHECK EXISTING BOOKING
            # -------------------------------
            new_start = datetime.datetime.combine(
                booking.booking_date,
                booking.start_time
            )

            window_start = (new_start - timedelta(minutes=14, seconds=59)).time()
            window_end = (new_start + timedelta(minutes=14, seconds=59)).time()

            existing_qs = Booking.objects.filter(
                client=client,
                booking_date=booking.booking_date,
            )

            if window_start <= window_end:
                existing_qs = existing_qs.filter(start_time__range=(window_start, window_end))
            else:
                existing_qs = existing_qs.filter(start_time=booking.start_time)

            # If an existing booking is found
            if existing_qs.exists():
                existing_time = existing_qs.first().start_time
                selected_time = booking.start_time

                if is_ajax:
                    return JsonResponse({
                        "status": "duplicate",
                        "existing_time": existing_time.strftime("%I:%M %p"),
                        "selected_time": selected_time.strftime("%I:%M %p"),
                    }, status=409)

                # Non-AJAX
                faqs = FAQ.objects.all()
                return render(request, 'website/schedule_call2.html', {
                    'form': form,
                    'faqs': faqs,
                    'existing_time': existing_time.strftime("%I:%M %p"),
                    'selected_time': selected_time.strftime("%I:%M %p"),
                    'duplicate': True,
                })

            # -------------------------------
            # SAVE BOOKING
            # -------------------------------
            booking.save()

            _bid = booking.pk
            transaction.on_commit(
                lambda: threading.Thread(
                    target=_booking_followup_zoom_and_emails,
                    args=(_bid, client_name, client_email),
                    daemon=True,
                ).start()
            )

            if is_ajax:
                return JsonResponse({
                    'status': 'success',
                    'message': 'Your call has been scheduled successfully!',
                })

            messages.success(request, 'Your call has been scheduled successfully!')
            return redirect('index')

        # Form invalid
        if is_ajax:
            errors = {field: [{'message': str(e)} for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        faqs = FAQ.objects.all()
        return render(request, 'website/schedule_call2.html', {'form': form, 'faqs': faqs})


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
            with transaction.atomic():
                contact_instance = form.save()
                name = f"{contact_instance.first_name} {contact_instance.last_name}"
                from_email = contact_instance.email
                phone = contact_instance.phone
                message_body = contact_instance.message
                base_url = request.build_absolute_uri("/")[:-1]
                fn = contact_instance.first_name
                transaction.on_commit(
                    lambda n=name, fe=from_email, ph=phone, mb=message_body, bu=base_url, f=fn: threading.Thread(
                        target=_contact_form_send_emails,
                        args=(n, fe, ph, mb, bu, f),
                        daemon=True,
                    ).start()
                )

            if is_ajax:
                return JsonResponse({"status": "success"})

            messages.success(request, "Your message has been sent successfully!")
            return redirect("contact")

        # Form invalid
        if is_ajax:
            errors = {
                field: [{"message": str(e)} for e in errs]
                for field, errs in form.errors.items()
            }
            return JsonResponse({"status": "error", "errors": errors}, status=400)

        return render(
            request,
            "website/contact.html",
            {
                "form": form,
                "faqs": FAQ.objects.all(),
                "contact": ContactInfo.objects.first(),
            },
        )

class AboutUsPage(views.View):
    def get(self,request):
        team_members = TeamMember.objects.all().order_by('created_at')
        services = Service.objects.all()[:3].values("name", "description", "icon")
        workspace_images = CompanyEventImage.objects.all().order_by('created_at')
        return render(request,'website/about.html',{'team_members':team_members, 'services':services, 'workspace_images':workspace_images})

    
class ServicePage(views.View):
    def get(self,request):
        industries = Industry.objects.all().values("name", "svg_icon")  # all industries with svg icons
        services = Service.objects.all().order_by('display_order')[:9]
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
        with transaction.atomic():
            application.save()
            aid = application.pk
            transaction.on_commit(
                lambda pk=aid: threading.Thread(
                    target=_career_application_send_emails,
                    args=(pk,),
                    daemon=True,
                ).start()
            )

        messages.success(
            request,
            "Your application has been submitted successfully.",
        )

        if is_ajax:
            return JsonResponse({"status": "success"})

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
            with transaction.atomic():
                contact_instance = form.save()
                name = f"{contact_instance.first_name} {contact_instance.last_name}"
                from_email = contact_instance.email
                phone = contact_instance.phone
                message_body = contact_instance.message
                base_url = request.build_absolute_uri("/")[:-1]
                fn = contact_instance.first_name
                transaction.on_commit(
                    lambda n=name, fe=from_email, ph=phone, mb=message_body, bu=base_url, f=fn: threading.Thread(
                        target=_contact_form_send_emails,
                        args=(n, fe, ph, mb, bu, f),
                        daemon=True,
                    ).start()
                )

            if is_ajax:
                return JsonResponse({"status": "success"})

            messages.success(request, "Your message has been sent successfully!")
            return redirect("contact")

        # Form invalid
        if is_ajax:
            errors = {
                field: [{"message": str(e)} for e in errs]
                for field, errs in form.errors.items()
            }
            return JsonResponse({"status": "error", "errors": errors}, status=400)

        return render(
            request,
            "website/contact.html",
            {
                "form": form,
                "faqs": FAQ.objects.all(),
                "contact": ContactInfo.objects.first(),
            },
        )
    


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
        is_ajax = request.headers.get("X-Requested-With") == "XMLHttpRequest"
        email = request.POST.get("email", "").strip().lower()
        base_url = request.build_absolute_uri("/")[:-1]

        if not email:
            if is_ajax:
                return JsonResponse({"status": "error", "message": "Email is required."}, status=400)
            return redirect(request.META.get("HTTP_REFERER", "/"))

        def queue_welcome(em):
            threading.Thread(
                target=_newsletter_welcome_email,
                args=(em, base_url),
                daemon=True,
            ).start()

        # Duplicate — still success UX; welcome mail in background
        if Newsletter.objects.filter(email=email).exists():
            queue_welcome(email)
            if is_ajax:
                return JsonResponse({"status": "success", "already": True})
            messages.success(request, "You're already subscribed!")
            return redirect(request.META.get("HTTP_REFERER", "/"))

        form = NewsletterForm(request.POST)

        if form.is_valid():
            try:
                with transaction.atomic():
                    form.save()
                    transaction.on_commit(
                        lambda em=email: threading.Thread(
                            target=_newsletter_welcome_email,
                            args=(em, base_url),
                            daemon=True,
                        ).start()
                    )

                if is_ajax:
                    return JsonResponse({"status": "success", "already": False})
                messages.success(request, "Subscribed successfully!")

            except IntegrityError:
                if is_ajax:
                    return JsonResponse({"status": "success", "already": True})
                messages.success(request, "You're already subscribed!")
        else:
            if is_ajax:
                return JsonResponse(
                    {
                        "status": "error",
                        "message": "Please enter a valid email address.",
                    },
                    status=400,
                )
            messages.error(request, "Invalid email.")

    return redirect(request.META.get("HTTP_REFERER", "/"))
