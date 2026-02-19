import attendance.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0080_add_absent_fine"),
    ]

    operations = [
        migrations.AddField(
            model_name="organizationsettings",
            name="weekend_days",
            field=models.JSONField(
                default=attendance.models.default_weekend_days,
                help_text="List of weekend weekdays using Python weekday numbers (0=Monday ... 6=Sunday).",
            ),
        ),
    ]
