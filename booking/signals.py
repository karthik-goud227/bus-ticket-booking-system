from django.contrib.auth.signals import user_logged_in
from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import AccountProfile, LoginEvent


@receiver(user_logged_in, dispatch_uid="busbook_record_successful_login")
def record_successful_login(sender, request, user, **kwargs):
    source = "ADMIN" if request.path.startswith("/admin/") else "SITE"
    LoginEvent.objects.create(user=user, source=source)


@receiver(post_save, sender=settings.AUTH_USER_MODEL, dispatch_uid="busbook_create_account_profile")
def create_account_profile(sender, instance, created, **kwargs):
    if created:
        AccountProfile.objects.get_or_create(user=instance)
