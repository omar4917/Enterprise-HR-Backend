from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0059_fix_messagesetting_managed"),
    ]

    operations = [
        migrations.AddField(
            model_name="voicesetting",
            name="voice_repeat_delay_seconds",
            field=models.FloatField(
                default=1.5,
                help_text="Delay in seconds between repeated voice prompts.",
            ),
        ),
    ]
