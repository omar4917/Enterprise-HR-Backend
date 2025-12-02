from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0035_merge_0034_alter_salarystatistic_id_0034_salarystatisticdefault"),
    ]

    operations = [
        migrations.AddField(
            model_name="salarystatistic",
            name="use_default",
            field=models.BooleanField(default=True, help_text="If enabled, values will sync from default template on each export"),
        ),
    ]

