from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("booking", "0010_recompile_trip_schedule_guard"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LoginEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("occurred_at", models.DateTimeField(auto_now_add=True)),
                ("source", models.CharField(choices=[("SITE", "Website"), ("ADMIN", "Admin")], max_length=12)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="login_events", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ["-occurred_at", "-id"]},
        ),
        migrations.AddIndex(
            model_name="loginevent",
            index=models.Index(fields=["user", "occurred_at"], name="idx_login_user_time"),
        ),
    ]
