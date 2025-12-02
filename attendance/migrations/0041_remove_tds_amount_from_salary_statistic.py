from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0039_merge_0038_merge_20251126_1602_0038_trim_salary_statistic_default_fields"),
        ("attendance", "0040_remove_tds_amount_from_default"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="salarystatistic",
            name="tds_amount",
        ),
    ]

