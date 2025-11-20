from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("attendance", "0027_merge_20251112_1614"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="employee",
            name="face_encoding",
        ),
        migrations.AddField(
            model_name="employee",
            name="facial_template",
            field=models.TextField(blank=True, help_text="Base64 FaceSDK template provided by the Android app", null=True),
        ),
        migrations.AlterField(
            model_name="employee",
            name="email",
            field=models.EmailField(blank=True, max_length=254, null=True, unique=True),
        ),
        migrations.AlterField(
            model_name="employee",
            name="department",
            field=models.CharField(blank=True, max_length=100),
        ),
        migrations.AlterField(
            model_name="employee",
            name="phone",
            field=models.CharField(blank=True, max_length=15),
        ),
        migrations.AlterField(
            model_name="employee",
            name="designation",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.AlterField(
            model_name="employee",
            name="branch",
            field=models.CharField(blank=True, max_length=50),
        ),
        migrations.CreateModel(
            name="DeviceRegistration",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("token", models.CharField(max_length=255, unique=True)),
                ("platform", models.CharField(blank=True, max_length=20)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
        ),
    ]
