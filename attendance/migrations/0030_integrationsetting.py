from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0029_alter_employee_created_at_alter_employee_updated_at"),
    ]

    operations = [
        migrations.CreateModel(
            name="IntegrationSetting",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "fcm_server_key",
                    models.TextField(blank=True, help_text="Paste your Firebase Cloud Messaging server key here."),
                ),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
