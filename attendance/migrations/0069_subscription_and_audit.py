# Generated migration for SubscriptionPlan and AuditLog models
# For SaaS features: plans with limits and audit logging

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0068_assign_existing_to_default_org'),
    ]

    operations = [
        # Create SubscriptionPlan model
        migrations.CreateModel(
            name='SubscriptionPlan',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True)),
                ('slug', models.SlugField(max_length=50, unique=True)),
                ('description', models.TextField(blank=True)),
                ('max_employees', models.IntegerField(default=10)),
                ('max_devices', models.IntegerField(default=2)),
                ('features', models.JSONField(default=list, help_text='List of enabled features')),
                ('price_monthly', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('price_yearly', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('is_active', models.BooleanField(default=True)),
                ('is_default', models.BooleanField(default=False, help_text='Default plan for new organizations')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['price_monthly'],
            },
        ),
        
        # Add subscription fields to Organization
        migrations.AddField(
            model_name='organization',
            name='subscription_plan',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='organizations',
                to='attendance.subscriptionplan',
            ),
        ),
        migrations.AddField(
            model_name='organization',
            name='subscription_started',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='organization',
            name='subscription_expires',
            field=models.DateTimeField(blank=True, null=True),
        ),
        
        # Create AuditLog model
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('organization', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='audit_logs',
                    to='attendance.organization',
                )),
                ('user_email', models.CharField(max_length=200)),
                ('user_name', models.CharField(blank=True, max_length=200)),
                ('action', models.CharField(max_length=50, choices=[
                    ('login', 'Login'),
                    ('logout', 'Logout'),
                    ('create', 'Create'),
                    ('update', 'Update'),
                    ('delete', 'Delete'),
                    ('view', 'View'),
                    ('export', 'Export'),
                    ('import', 'Import'),
                ])),
                ('resource_type', models.CharField(max_length=50)),
                ('resource_id', models.IntegerField(blank=True, null=True)),
                ('resource_name', models.CharField(blank=True, max_length=200)),
                ('details', models.JSONField(default=dict, blank=True)),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True)),
                ('user_agent', models.TextField(blank=True)),
                ('timestamp', models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                'ordering': ['-timestamp'],
                'indexes': [
                    models.Index(fields=['organization', 'timestamp'], name='audit_org_ts_idx'),
                    models.Index(fields=['user_email', 'timestamp'], name='audit_user_ts_idx'),
                    models.Index(fields=['action', 'timestamp'], name='audit_action_ts_idx'),
                    models.Index(fields=['resource_type', 'timestamp'], name='audit_resource_ts_idx'),
                ],
            },
        ),
    ]
