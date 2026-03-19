from django.contrib import admin
from django.apps import apps
from django.db import models

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
for model in app_models:
    try:
        admin.site.register(model, generate_auto_admin(model))
    except admin.sites.AlreadyRegistered:
        pass
