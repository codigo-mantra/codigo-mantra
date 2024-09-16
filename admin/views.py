from django.shortcuts import render,redirect
from django.core.mail import send_mail
from django.http import JsonResponse
from django.conf import settings
from .forms import ContactUsForm
from django import views
from django.contrib import messages
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
                return redirect('index')
            print(form.errors)
            return render(request,'index.html',{'form':form})
