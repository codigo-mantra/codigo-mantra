from django.contrib import admin
from django.apps import apps
from django.db import models
from .models import (
    ServiceDetail, ServiceProblemItem, ServiceProblemCard, ServiceSolutionItem,
    ServiceCapabilityItem, ServiceWhyChooseItem,
    IndustryDetail, IndustryImpactItem, IndustrySolutionItem,
    IndustryProvideItem, IndustryWhyChooseItem,
    Service_index, Industry, Service_page
)

# --- ServiceDetail Inlines ---
class ServiceProblemItemInline(admin.TabularInline):
    model = ServiceProblemItem
    extra = 1

class ServiceProblemCardInline(admin.StackedInline):
    model = ServiceProblemCard
    extra = 1

class ServiceSolutionItemInline(admin.TabularInline):
    model = ServiceSolutionItem
    extra = 1

class ServiceCapabilityItemInline(admin.TabularInline):
    model = ServiceCapabilityItem
    extra = 1

class ServiceWhyChooseItemInline(admin.StackedInline):
    model = ServiceWhyChooseItem
    extra = 1

@admin.register(ServiceDetail)
class ServiceDetailAdmin(admin.ModelAdmin):
    inlines = [
        ServiceProblemItemInline,
        ServiceProblemCardInline,
        ServiceSolutionItemInline,
        ServiceCapabilityItemInline,
        ServiceWhyChooseItemInline,
    ]
    list_display = ['service_page', 'service_main_page', 'hero_title', 'created_at']
    search_fields = ['hero_title', 'service_page__name', 'service_main_page__name']

# --- IndustryDetail Inlines ---
class IndustryImpactItemInline(admin.StackedInline):
    model = IndustryImpactItem
    extra = 1

class IndustrySolutionItemInline(admin.TabularInline):
    model = IndustrySolutionItem
    extra = 1

class IndustryProvideItemInline(admin.StackedInline):
    model = IndustryProvideItem
    extra = 1

class IndustryWhyChooseItemInline(admin.TabularInline):
    model = IndustryWhyChooseItem
    extra = 1

@admin.register(IndustryDetail)
class IndustryDetailAdmin(admin.ModelAdmin):
    inlines = [
        IndustryImpactItemInline,
        IndustrySolutionItemInline,
        IndustryProvideItemInline,
        IndustryWhyChooseItemInline,
    ]
    list_display = ['industry', 'hero_title', 'created_at']
    search_fields = ['hero_title', 'industry__name']

# --- Parent Models with Detail Inlines ---
class ServiceDetailInline(admin.StackedInline):
    model = ServiceDetail
    can_delete = False
    verbose_name_plural = 'Service Detail'
    extra = 0

@admin.register(Service_index)
class ServiceIndexAdmin(admin.ModelAdmin):
    inlines = [ServiceDetailInline]
    list_display = ['name', 'display_order', 'created_at']
    search_fields = ['name']

@admin.register(Service_page)
class ServicePageAdmin(admin.ModelAdmin):
    inlines = [ServiceDetailInline]
    list_display = ['name', 'display_order', 'created_at']
    search_fields = ['name']

class IndustryDetailInline(admin.StackedInline):
    model = IndustryDetail
    can_delete = False
    verbose_name_plural = 'Industry Detail'
    extra = 0

@admin.register(Industry)
class IndustryAdmin(admin.ModelAdmin):
    inlines = [IndustryDetailInline]
    list_display = ['name', 'slug', 'created_at']
    search_fields = ['name', 'slug']

def generate_auto_admin(model):
    meta = model._meta
    fields = [f for f in meta.fields]
    
    admin_attrs = {
        'list_display': [f.name for f in fields if not isinstance(f, models.TextField)],
        'list_filter': [f.name for f in fields if isinstance(f, (models.BooleanField, models.DateField, models.ForeignKey))],
        'search_fields': [f.name for f in fields if isinstance(f, (models.CharField, models.TextField))],
        'ordering': ['-id'] if any(f.name == 'id' for f in fields) else None,
        'list_per_page': 50,
    }
    
    return type(f"{model.__name__}AutoAdmin", (admin.ModelAdmin,), admin_attrs)


app_name = 'website'
app_models = apps.get_app_config(app_name).get_models()

# List of models handled manually
manual_models = [
    ServiceDetail, ServiceProblemItem, ServiceProblemCard, ServiceSolutionItem,
    ServiceCapabilityItem, ServiceWhyChooseItem,
    IndustryDetail, IndustryImpactItem, IndustrySolutionItem,
    IndustryProvideItem, IndustryWhyChooseItem,
    Service_index, Industry, Service_page
]

for model in app_models:
    if model in manual_models:
        continue
    try:
        admin.site.register(model, generate_auto_admin(model))
    except admin.sites.AlreadyRegistered:
        pass
