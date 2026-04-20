from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
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

from .google_meet import generate_google_meet_link
import logging
import threading
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

logger = logging.getLogger(__name__)

# Bookings are stored as calendar date + wall clock in this zone (matches Django TIME_ZONE / Zoom).
ADMIN_BOOKING_TZ = "Asia/Kolkata"
TZ_ALIASES = {
    "America/NewYork": "America/New_York",
    # Not a real IANA id; India uses Asia/Kolkata
    "Asia/India": "Asia/Kolkata",
}


def _safe_zone(tz_name: str) -> ZoneInfo:
    raw = (tz_name or "").strip()
    if not raw:
        return ZoneInfo(ADMIN_BOOKING_TZ)
    # Fix "Asia / India" → "Asia/India" (then alias → Asia/Kolkata)
    name = "".join(raw.split())
    name = TZ_ALIASES.get(name, name)
    lower = name.lower()
    for alias, canonical in TZ_ALIASES.items():
        if alias.lower() == lower:
            name = canonical
            break
    try:
        return ZoneInfo(name)
    except Exception:
        return ZoneInfo(ADMIN_BOOKING_TZ)


def _client_local_to_ist(booking_date, start_time, client_tz: str) -> datetime:
    """Interpret date + time in the client's IANA zone; return aware datetime in Asia/Kolkata."""
    z_client = _safe_zone(client_tz)
    dt_client = datetime.combine(booking_date, start_time, tzinfo=z_client)
    return dt_client.astimezone(ZoneInfo(ADMIN_BOOKING_TZ))


def _booking_to_aware_ist(booking) -> datetime:
    naive = datetime.combine(booking.booking_date, booking.start_time)
    return naive.replace(tzinfo=ZoneInfo(ADMIN_BOOKING_TZ))


def _format_date_time_in_zone(dt_ist: datetime, tz_name: str):
    """dt_ist must be timezone-aware (IST). Returns (date_str, time_str) in tz_name."""
    z = _safe_zone(tz_name)
    local = dt_ist.astimezone(z)
    date_str = local.strftime("%A, %B %d, %Y")
    time_str = local.strftime("%I:%M %p").lstrip("0")
    return date_str, time_str


def _booking_followup_zoom_and_emails(booking_id, client_name, client_email, client_tz=None):
    """Zoom + emails after commit — runs in a background thread.

    client_tz: IANA name from the booking form (not stored on Booking); used only for
    formatting the client-facing email in their wall time.
    """
    close_old_connections()
    try:
        booking = Booking.objects.select_related("consultant").get(pk=booking_id)
        consultant = booking.consultant

        # Generate meeting link if not exists
        if not booking.meet_link:
            meet_link = generate_google_meet_link(booking=booking, client_email=client_email)
            if not meet_link:
                meet_link = generate_zoom_meet_link(booking=booking, client_email=client_email)
            if meet_link:
                booking.meet_link = meet_link
                booking.save(update_fields=["meet_link"])
            else:
                logger.warning(
                    "Booking %s: meet_link not saved — both Google Meet and Zoom failed.",
                    booking.pk,
                )

        dt_ist = _booking_to_aware_ist(booking)
        client_tz = (client_tz or "").strip() or ADMIN_BOOKING_TZ

        client_date_str, client_time_str = _format_date_time_in_zone(dt_ist, client_tz)
        admin_date_str, admin_time_str = _format_date_time_in_zone(dt_ist, ADMIN_BOOKING_TZ)

        client_first_name = (client_name or "").split(" ")[0]
        # Client email: wall time in the zone they chose when booking (e.g. America/New_York).
        # Admin email: same instant, shown in Asia/Kolkata for the team.
        client_html = render_to_string("call-email.html", {
            "name": client_first_name,
            "email": client_email,
            "date": client_date_str,
            "time": f"{client_time_str} ({client_tz})",
            "client_tz": client_tz,
            "meet_link": booking.meet_link,
        })

        admin_html = render_to_string("call-email-admin.html", {
            "name": client_name,
            "admin_name": consultant.name if consultant else "Admin",
            "email": client_email,
            "phone_number": booking.phone_number or "N/A",
            "date": admin_date_str,
            "time": f"{admin_time_str} ({ADMIN_BOOKING_TZ})",
            "admin_tz": ADMIN_BOOKING_TZ,
            "client_tz": client_tz,
            "meet_link": booking.meet_link,
        })

        # Admin recipients
        admin_recipients = list(getattr(settings, "BOOKING_ADMIN_EMAILS", []) or [])
        if not admin_recipients:
            host_user = getattr(settings, "EMAIL_HOST_USER", "")
            if host_user:
                admin_recipients = [host_user]

        if not getattr(settings, "BOOKING_SINGLE_ADMIN_INBOX", True):
            if consultant and consultant.email:
                ce = consultant.email.strip()
                if ce and ce not in admin_recipients:
                    admin_recipients.append(ce)

        admin_recipients = [e for e in admin_recipients if e]

        # Send client email (only to the address they entered on the form)
        try:
            client_msg = EmailMessage(
                "Your Upcoming Call with Codigo Mantra",
                client_html,
                settings.DEFAULT_FROM_EMAIL,
                [client_email],
            )
            client_msg.content_subtype = "html"
            client_msg.send(fail_silently=False)
        except Exception as e:
            logger.warning("Booking: failed to email client %s: %s", client_email, e)

        # Admin notification (call-email-admin.html) — do not also BCC/copy the client template
        # to EMAIL_HOST_USER or admins get two messages for one booking.
        # Send admin email
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

        applicant_first_name = (name or "").split(" ")[0]
        user_html = render_to_string(
            "email-application.html",
            {
                "name": applicant_first_name,
                "job_title": job_title,
            }
        )
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
        show_success_modal = request.GET.get('success') == '1'

        now_ist = datetime.now(ZoneInfo(ADMIN_BOOKING_TZ))
        form.fields['start_time'].widget.attrs['min'] = now_ist.strftime("%H:%M")

        return render(request, 'website/schedule_call2.html', {
            'form': form, 
            'faqs': faqs,
            'show_success_modal': show_success_modal
        })

    def post(self, request):
        is_ajax = (
            request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 
            request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
        )
        form = BookingForm(request.POST)
        ignore_conflict = request.POST.get('ignore_conflict') == 'true'

        if form.is_valid():
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

            client_timezone = (request.POST.get("client_timezone") or "").strip() or ADMIN_BOOKING_TZ

            # Client's date/time (from step 1) are in client_timezone → convert to IST for storage
            client_date = booking.booking_date
            client_time = booking.start_time
            try:
                dt_ist = _client_local_to_ist(client_date, client_time, client_timezone)
            except Exception:
                if is_ajax:
                    return JsonResponse(
                        {"status": "error", "message": "Invalid timezone. Please choose a valid region."},
                        status=400,
                    )
                messages.error(request, "Invalid timezone. Please choose a valid region.")
                return render(request, 'website/schedule_call2.html', {'form': form, 'faqs': FAQ.objects.all()})

            booking.booking_date = dt_ist.date()
            booking.start_time = dt_ist.time()

            # ------------------- Real-time validation (IST) -------------------
            now_ist = datetime.now(ZoneInfo(ADMIN_BOOKING_TZ))
            # Restrict same-day bookings: booking must be tomorrow onwards (IST)
            if dt_ist.date() <= now_ist.date():
                msg = "Please select a date from tomorrow onwards for your meeting."
                if is_ajax:
                    return JsonResponse({'status': 'error', 'message': msg}, status=400)
                messages.error(request, msg)
                return render(request, 'website/schedule_call2.html', {'form': form, 'faqs': FAQ.objects.all()})

            # ------------------- Check duplicate bookings (IST wall time) -------------------
            if not ignore_conflict:
                selected_datetime_naive = datetime.combine(booking.booking_date, booking.start_time)
                window_start = (selected_datetime_naive - timedelta(minutes=14, seconds=59)).time()
                window_end = (selected_datetime_naive + timedelta(minutes=14, seconds=59)).time()

                # Check if this consultant or this client is already booked in this window
                # Ensure we only check for OTHER bookings (not the one we are about to save if it already has an ID, 
                # though here we haven't saved it yet, but we filter by client and consultant)
                existing_qs = Booking.objects.filter(
                    Q(client=client) | Q(consultant=consultant),
                    booking_date=booking.booking_date
                )
                
                # IMPORTANT: If we're updating an existing booking (though step 2 usually creates new),
                # we should exclude it from the conflict check.
                if booking.pk:
                    existing_qs = existing_qs.exclude(pk=booking.pk)
                
                if window_start <= window_end:
                    existing_qs = existing_qs.filter(start_time__range=(window_start, window_end))
                else:
                    existing_qs = existing_qs.filter(start_time=booking.start_time)

                if existing_qs.exists():
                    ex_booking = existing_qs.first()
                    ex_dt_ist = _booking_to_aware_ist(ex_booking)

                    # Suggest next available slot (30-minute grid)
                    suggested_dt = dt_ist + timedelta(minutes=30)
                    while True:
                        s_naive = suggested_dt.replace(tzinfo=None)
                        s_start = (s_naive - timedelta(minutes=14, seconds=59)).time()
                        s_end = (s_naive + timedelta(minutes=14, seconds=59)).time()
                        
                        s_qs = Booking.objects.filter(
                            Q(client=client) | Q(consultant=consultant),
                            booking_date=suggested_dt.date()
                        )
                        if s_start <= s_end:
                            s_qs = s_qs.filter(start_time__range=(s_start, s_end))
                        else:
                            s_qs = s_qs.filter(start_time=suggested_dt.time())
                        
                        if not s_qs.exists():
                            break
                        suggested_dt += timedelta(minutes=30)

                    if is_ajax:
                        ex_d, ex_t = _format_date_time_in_zone(ex_dt_ist, client_timezone)
                        sel_d, sel_t = _format_date_time_in_zone(dt_ist, client_timezone)
                        sug_d, sug_t = _format_date_time_in_zone(suggested_dt, client_timezone)
                        return JsonResponse({
                            "status": "conflict",
                            "existing_time": f"{ex_d} at {ex_t}",
                            "selected_time": f"{sel_d} at {sel_t}",
                            "suggested_time": f"{sug_d} at {sug_t}",
                            "suggested_raw_time": suggested_dt.astimezone(_safe_zone(client_timezone)).strftime("%H:%M"),
                            # "suggested_raw_date": suggested_dt.astimezone(_safe_zone(client_timezone)).strftime("%Y-%m-%d")
                        }, status=409)
                    ex_d, ex_t = _format_date_time_in_zone(ex_dt_ist, client_timezone)
                    messages.error(request, f"A booking already exists on {ex_d} at {ex_t} (your time).")
                    return render(request, 'website/schedule_call2.html', {'form': form, 'faqs': FAQ.objects.all()})

            # Create meeting link before persisting booking so meet_link is saved with booking.
            meet_link = generate_google_meet_link(booking=booking, client_email=client_email)
            if not meet_link:
                meet_link = generate_zoom_meet_link(booking=booking, client_email=client_email)
            if not meet_link:
                msg = (
                    "We could not schedule your call, please try again"
                )
                if is_ajax:
                    return JsonResponse({"status": "error", "message": msg}, status=503)
                messages.error(request, msg)
                return render(request, 'website/schedule_call2.html', {'form': form, 'faqs': FAQ.objects.all()})

            booking.meet_link = meet_link

            # ------------------- Save booking & trigger follow-up -------------------
            # Removed duplicate delete logic to allow multiple bookings
            booking.save()
            _bid = booking.pk
            _ctz = client_timezone
            transaction.on_commit(
                lambda bid=_bid, n=client_name, e=client_email, tz=_ctz: threading.Thread(
                    target=_booking_followup_zoom_and_emails,
                    args=(bid, n, e, tz),
                    daemon=True,
                ).start()
            )

            if is_ajax:
                return JsonResponse({'status': 'success', 'message': 'Your call has been scheduled successfully!'})

            messages.success(request, 'Your call has been scheduled successfully!')
            return redirect(reverse('schedule-call-2') + '?success=1')

        # Form invalid
        if is_ajax:
            errors = {field: [{'message': str(e)} for e in errs] for field, errs in form.errors.items()}
            return JsonResponse({'status': 'error', 'errors': errors}, status=400)

        return render(request, 'website/schedule_call2.html', {'form': form, 'faqs': FAQ.objects.all()})


# @method_decorator(cache_page(60 * 5), name='dispatch')
class LandingPage(views.View):
    def get(self,request):
        form = ContactUsForm()
        services = Service_index.objects.all().order_by('display_order')[:6]  # last 6 services
        insights = Insight.objects.all().order_by('-created_at')[:3]  # last 3 insights
        testimonials_qs = list(Testimonial.objects.all().order_by('-created_at')[:6])  # last 6 testimonials
        # Ensure image testimonials appear before video testimonials (preserve recency within each group)
        testimonials = sorted(testimonials_qs, key=lambda t: t.media_type == "video")
        # industries = Industry.objects.all().values("name", "svg_icon")  # all industries with svg icons
        industry_names = [
            'Healthcare & MedTech', 'EdTech & E-Learning', 'Fintech & Banking',
            'E-Commerce & Retail', 'Real Estate & PropTech', 'Logistics & Supply Chain',
            'Legal & LegalTech', 'Media & Entertainment', 'Travel & Hospitality',
            'SaaS & Software Products', 'Startups & SMBs'
        ]
        industries = Industry.objects.filter(name__in=industry_names).values("name", "svg_icon")
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
        # services = Service.objects.all()[:3].values("name", "description", "icon")
        services = Service.objects.all()[:3].values("name")
        workspace_images = CompanyEventImage.objects.all().order_by('created_at')
        return render(request,'website/about.html',{'team_members':team_members, 'services':services, 'workspace_images':workspace_images})

    
class ServicePage(views.View):
    def get(self,request):
        # industries = Industry.objects.all().values("name", "svg_icon")  # all industries with svg icons
        industry_names = [
            'Healthcare & MedTech', 'EdTech & E-Learning', 'Fintech & Banking',
            'E-Commerce & Retail', 'Real Estate & PropTech', 'Logistics & Supply Chain',
            'Legal & LegalTech', 'Media & Entertainment', 'Travel & Hospitality',
            'SaaS & Software Products', 'Startups & SMBs'
        ]
        industries = Industry.objects.filter(name__in=industry_names).values("name", "svg_icon")
        services = Service_page.objects.all().order_by('display_order')[:9]
        return render(request,'website/services.html',{'services':services, 'industries':industries})
    

class CareerPage(views.View):
    def get(self,request):
        job_openings = JobOpening.objects.filter(is_active=True).order_by('-created_at')
        # services = Service.objects.all()[:3].values("name", "description", "icon")
        services = Service.objects.all()[:3].values("name")
        return render(request,'website/career.html',{'job_openings':job_openings, 'services':services})

class CareerFormPage(views.View):
    def get(self,request, job_id):
        try:
            job = JobOpening.objects.get(id=job_id, is_active=True)
            similar_jobs = JobOpening.objects.filter(
                job_type=job.job_type,
                department=job.department,
                is_active=True,
            ).exclude(id=job_id)[:2]
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
            job = JobOpening.objects.get(id=job_id, is_active=True)
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
                job_type=job.job_type, department=job.department, is_active=True
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
        )[:6]
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
