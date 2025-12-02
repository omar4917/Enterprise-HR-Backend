from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0033_employee_bank_account_salarystatistic"),
    ]

    operations = [
        migrations.CreateModel(
            name="SalaryStatisticDefault",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("basic_salary", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("house_rent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("medical_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("conveyance_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("food_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("other_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("working_days", models.PositiveIntegerField(default=0)),
                ("weekends", models.PositiveIntegerField(default=0)),
                ("leave_days", models.PositiveIntegerField(default=0)),
                ("holidays", models.PositiveIntegerField(default=0)),
                ("attended_days", models.PositiveIntegerField(default=0)),
                ("ot_hours", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=8)),
                ("ot_rate", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("hd_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("attendance_bonus", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("tds_percent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=6)),
                ("tds_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
            ],
        ),
    ]

