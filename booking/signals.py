from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from .models import LoginEvent


@receiver(user_logged_in, dispatch_uid="busbook_record_successful_login")
def record_successful_login(sender, request, user, **kwargs):
    source = "ADMIN" if request.path.startswith("/admin/") else "SITE"
    LoginEvent.objects.create(user=user, source=source)
