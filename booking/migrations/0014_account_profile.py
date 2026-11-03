from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


def create_existing_profiles(apps, schema_editor):
    User = apps.get_model(*settings.AUTH_USER_MODEL.split("."))
    Profile = apps.get_model("booking", "AccountProfile")
    for user_id in User.objects.values_list("id", flat=True).iterator():
        Profile.objects.get_or_create(user_id=user_id)


class Migration(migrations.Migration):
    dependencies = [("booking", "0013_service_billing_reviews"), migrations.swappable_dependency(settings.AUTH_USER_MODEL)]
    operations = [
        migrations.CreateModel(name="AccountProfile", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("phone", models.CharField(max_length=20, blank=True)),
            ("theme", models.CharField(max_length=6, choices=[("SYSTEM", "Use device setting"), ("LIGHT", "Light"), ("DARK", "Dark")], default="SYSTEM")),
            ("user", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="account_profile", to=settings.AUTH_USER_MODEL)),
        ]),
        migrations.RunPython(create_existing_profiles, migrations.RunPython.noop),
    ]
