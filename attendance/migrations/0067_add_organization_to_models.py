# Generated migration for adding organization FK to remaining models
# For complete multi-tenant data isolation

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0066_assign_default_organization'),
    ]

    operations = [
        # Add organization to BulkHoliday
        migrations.AddField(
            model_name='bulkholiday',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='holidays',
                to='attendance.organization',
            ),
        ),
        
        # Add organization to Shift
        migrations.AddField(
            model_name='shift',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='shifts',
                to='attendance.organization',
            ),
        ),
        
        # Add organization to SalaryStatisticDefault
        migrations.AddField(
            model_name='salarystatisticdefault',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='salary_defaults',
                to='attendance.organization',
            ),
        ),
        
        # Add organization to CompanyInfo
        migrations.AddField(
            model_name='companyinfo',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='company_info',
                to='attendance.organization',
            ),
        ),
        
        # Add organization to VoiceSetting
        migrations.AddField(
            model_name='voicesetting',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='voice_settings',
                to='attendance.organization',
            ),
        ),
        
        # Add organization to ContextSetting
        migrations.AddField(
            model_name='contextsetting',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='context_settings',
                to='attendance.organization',
            ),
        ),
        
        # Add organization to ModeratorLabel
        migrations.AddField(
            model_name='moderatorlabel',
            name='organization',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='moderator_labels',
                to='attendance.organization',
            ),
        ),
    ]
