from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from .models import BlogDetails


@receiver(post_save, sender=BlogDetails)
def _blogdetails_saved_update_parent_reading_time(sender, instance, **kwargs):
    blog = instance.blog
    if blog is None:
        return
    blog.update_reading_time(save=True)


@receiver(post_delete, sender=BlogDetails)
def _blogdetails_deleted_update_parent_reading_time(sender, instance, **kwargs):
    blog = instance.blog
    if blog is None:
        return
    blog.update_reading_time(save=True)
