from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0052_moderatorlabel"),
    ]

    operations = [
        migrations.AddField(
            model_name="companyinfo",
            name="bin",
            field=models.CharField(
                blank=True, max_length=100, null=True, verbose_name="BIN / BFN"
            ),
        ),
        migrations.AddField(
            model_name="companyinfo",
            name="founder",
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name="companyinfo",
            name="tin",
            field=models.CharField(blank=True, max_length=100, null=True, verbose_name="TIN"),
        ),
    ]
