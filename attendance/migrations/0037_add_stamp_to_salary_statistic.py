from django.db import migrations, models
from decimal import Decimal


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0036_salarystatistic_use_default"),
    ]

    operations = [
        migrations.AddField(
            model_name="salarystatistic",
            name="stamp",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
        migrations.AddField(
            model_name="salarystatisticdefault",
            name="stamp",
            field=models.DecimalField(decimal_places=2, default=Decimal("0.00"), max_digits=12),
        ),
    ]

