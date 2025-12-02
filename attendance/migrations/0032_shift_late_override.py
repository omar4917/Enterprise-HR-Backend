from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0031_integrationsetting_fcm_service_account_json"),
    ]

    operations = [
        migrations.AddField(
            model_name="shift",
            name="late_override_minutes",
            field=models.PositiveIntegerField(
                default=0,
                help_text="If late beyond this many minutes, override status using late_override_status",
            ),
        ),
        migrations.AddField(
            model_name="shift",
            name="late_override_status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Late", "Late"),
                    ("Absent", "Absent"),
                    ("Early Leave", "Early Leave"),
                    ("Half Day", "Half Day"),
                    ("Present", "Present"),
                    ("Pending", "Pending"),
                ],
                help_text="Status to apply when late beyond late_override_minutes (optional)",
                max_length=20,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="attendancerecord",
            name="status",
            field=models.CharField(
                blank=True,
                choices=[
                    ("Present", "Present"),
                    ("Late", "Late"),
                    ("Early Leave", "Early Leave"),
                    ("Absent", "Absent"),
                    ("Half Day", "Half Day"),
                    ("On Leave", "On Leave"),
                    ("Holiday", "Holiday"),
                    ("Pending", "Pending"),
                    ("Off Day", "Off Day"),
                ],
                max_length=20,
                null=True,
            ),
        ),
    ]

