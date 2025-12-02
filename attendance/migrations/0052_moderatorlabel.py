from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0051_companyinfo"),
    ]

    operations = [
        migrations.CreateModel(
            name="ModeratorLabel",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("key", models.CharField(max_length=128, unique=True)),
                ("label", models.CharField(blank=True, max_length=255)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "ordering": ["key"],
            },
        ),
    ]
