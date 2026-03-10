from django.shortcuts import render,redirect
from django.core.mail import send_mail
from django.http import JsonResponse
from django.conf import settings
from .forms import ContactUsForm
from django import views
from django.contrib import messages
from django.template.loader import render_to_string
from django.core.exceptions import ValidationError
import json
from django.core.validators import validate_email as django_validate_email
from django.views.decorators.csrf import csrf_exempt
# Create your views here.


class LandingPage(views.View):
    def get(self,request):
        form = ContactUsForm()
        return render(request,'index.html',{'form':form})
    def post(self,request):
            form = ContactUsForm(data = request.POST)
            if form.is_valid():
                name = form.cleaned_data.get('name','') or ''
                fromEmail = form.cleaned_data.get('email','') or ''
                subject = form.cleaned_data.get('subject','') or ''
                contact = form.cleaned_data.get('contact','') or ''
                message = form.cleaned_data.get('message','')
                toEmail='codigomantra@gmail.com'
                # toEmail = "himanshu.codigomantra@gmail.com"
                message= "Client Name is :  "+name+" , email is : "+fromEmail+" , contact number is : "+contact + " and message is : "+message
                send_mail(subject,message,settings.EMAIL_HOST_USER,[toEmail])
                messages.success(request,'Thank you for contacting us.')
                return redirect('admin:index')
            print(form.errors)
            return render(request,'index.html',{'form':form})

@csrf_exempt
def contactus_form_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
        except json.JSONDecodeError:
            return JsonResponse({"message": "Invalid JSON"}, status=400)
        email = data.get('email')
        first_name = data.get('first_name')
        last_name = data.get('last_name')
        phone_number = data.get('phone_number', '')
        message = data.get('message')
        if phone_number:
            if not phone_number.isnumeric() or len(phone_number) < 10 or len(phone_number) > 18:
                return JsonResponse({'message': 'Invalid phone number!'}, status=400)
        required_fields = {
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "message": message
        }

        missing_fields = [field for field, value in required_fields.items() if not value]
        if missing_fields:
            return JsonResponse(
                {
                    "message": "Missing required fields",
                    "missing_fields": missing_fields
                },
                status=400
            )
        try:
            django_validate_email(email)
        except ValidationError:
            return JsonResponse(
                {"message": "Invalid email address"},
                status=400
            )
        context = {
                "first_name": first_name,
                "last_name": last_name,
                "phone_number": phone_number,
                "email_address": email,
                "message": message
            }
        try:
            html_content = render_to_string(
                    "email_templates/contactus.html",
                    context
                )
            send_mail(
                subject="We've received your message",
                message="We've received your message",
                from_email=settings.EMAIL_HOST_USER,
                recipient_list=[email],
                html_message=html_content,
                fail_silently=False,
            )
            return JsonResponse({'message': "Contact request submitted successfully."},status=200)
        except Exception as e:
            return JsonResponse({'message': f'Failed to send email: {str(e)}'}, status=400)

    return JsonResponse({'message': 'Invalid request method!'}, status=405)


