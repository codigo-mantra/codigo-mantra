from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from .models import Service_page, JobOpening

class StaticViewSitemap(Sitemap):
    priority = 0.8
    changefreq = 'weekly'

    def items(self):
        return ['index', 'about-us', 'services', 'contact', 'schedule-call', 'career', 'portfolio']

    def location(self, item):
        return reverse(item)

class ServiceSitemap(Sitemap):
    priority = 0.6
    changefreq = 'monthly'

    def items(self):
        return Service_page.objects.all()

    def location(self, obj):
        return f'/service-details/{obj.slug}/'

class JobSitemap(Sitemap):
    priority = 0.5
    changefreq = 'monthly'

    def items(self):
        return JobOpening.objects.filter(is_active=True)

    def location(self, obj):
        return reverse('career-apply', kwargs={'job_id': obj.id})
