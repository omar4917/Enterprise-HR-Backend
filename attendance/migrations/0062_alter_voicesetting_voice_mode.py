from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0061_employeevoicepreference"),
    ]

    operations = [
        migrations.AlterField(
            model_name="voicesetting",
            name="voice_mode",
            field=models.CharField(
                choices=[
                    ("default", "Default"),
                    ("calm", "Calm"),
                    ("energetic", "Energetic"),
                    ("slow", "Slow"),
                    ("soft", "Soft"),
                    ("clear_slow", "Clear & Slow"),
                    ("female_soft", "Female Soft"),
                    ("female_clear", "Female Clear"),
                ],
                default="default",
                help_text="Optional mode hint for the client.",
                max_length=16,
            ),
        ),
    ]
