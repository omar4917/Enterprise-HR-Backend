from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0039_merge_0038_merge_20251126_1602_0038_trim_salary_statistic_default_fields"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="salarystatisticdefault",
            name="tds_amount",
        ),
    ]

