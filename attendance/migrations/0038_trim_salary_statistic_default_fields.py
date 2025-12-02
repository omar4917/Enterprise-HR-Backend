from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0037_add_stamp_to_salary_statistic"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="salarystatisticdefault",
            name="basic_salary",
        ),
        migrations.RemoveField(
            model_name="salarystatisticdefault",
            name="ot_hours",
        ),
    ]

