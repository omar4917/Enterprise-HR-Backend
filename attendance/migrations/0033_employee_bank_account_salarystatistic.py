from django.db import migrations, models
import django.db.models.deletion
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0032_shift_late_override"),
    ]

    operations = [
        migrations.AddField(
            model_name="employee",
            name="bank_account",
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
        migrations.CreateModel(
            name="SalaryStatistic",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("month", models.PositiveIntegerField()),
                ("year", models.PositiveIntegerField()),
                ("basic_salary", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("house_rent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("medical_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("conveyance_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("food_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("other_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("gross_salary", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("working_days", models.PositiveIntegerField(default=0)),
                ("weekends", models.PositiveIntegerField(default=0)),
                ("leave_days", models.PositiveIntegerField(default=0)),
                ("holidays", models.PositiveIntegerField(default=0)),
                ("attended_days", models.PositiveIntegerField(default=0)),
                ("ot_hours", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=8)),
                ("ot_rate", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=10)),
                ("ot_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("hd_allowance", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("attendance_bonus", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("tds_percent", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=6)),
                ("tds_amount", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("payable", models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("employee", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="attendance.employee")),
            ],
            options={
                "unique_together": {("employee", "month", "year")},
                "ordering": ["employee__name"],
            },
        ),
    ]

