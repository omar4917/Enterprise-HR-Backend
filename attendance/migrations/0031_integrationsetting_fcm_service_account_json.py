from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0030_integrationsetting"),
    ]

    operations = [
        migrations.AddField(
            model_name="integrationsetting",
            name="fcm_service_account_json",
            field=models.TextField(
                blank=True,
                help_text="Optional: paste Firebase service account JSON (used for HTTP v1).",
            ),
        ),
    ]
