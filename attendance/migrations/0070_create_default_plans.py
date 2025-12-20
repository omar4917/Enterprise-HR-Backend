# Data migration to create default subscription plans

from django.db import migrations


def create_default_plans(apps, schema_editor):
    """Create default subscription plans."""
    SubscriptionPlan = apps.get_model('attendance', 'SubscriptionPlan')
    
    plans = [
        {
            'name': 'Free Trial',
            'slug': 'free-trial',
            'description': '14-day free trial with limited features',
            'max_employees': 5,
            'max_devices': 1,
            'features': ['attendance', 'employees'],
            'price_monthly': 0,
            'price_yearly': 0,
            'is_active': True,
            'is_default': True,
        },
        {
            'name': 'Basic',
            'slug': 'basic',
            'description': 'For small teams and startups',
            'max_employees': 25,
            'max_devices': 2,
            'features': ['attendance', 'employees', 'shifts', 'holidays', 'reports'],
            'price_monthly': 999,  # User will edit later
            'price_yearly': 9999,
            'is_active': True,
            'is_default': False,
        },
        {
            'name': 'Pro',
            'slug': 'pro',
            'description': 'For growing businesses',
            'max_employees': 100,
            'max_devices': 5,
            'features': ['attendance', 'employees', 'shifts', 'holidays', 'reports', 'salary', 'voice_message', 'livefeed'],
            'price_monthly': 2999,
            'price_yearly': 29999,
            'is_active': True,
            'is_default': False,
        },
        {
            'name': 'Enterprise',
            'slug': 'enterprise',
            'description': 'Unlimited everything for large organizations',
            'max_employees': 999999,  # Essentially unlimited
            'max_devices': 999999,
            'features': ['attendance', 'employees', 'shifts', 'holidays', 'reports', 'salary', 'voice_message', 'livefeed', 'audit_logs', 'api_access', 'priority_support'],
            'price_monthly': 9999,
            'price_yearly': 99999,
            'is_active': True,
            'is_default': False,
        },
    ]
    
    for plan_data in plans:
        SubscriptionPlan.objects.get_or_create(
            slug=plan_data['slug'],
            defaults=plan_data
        )
    
    print(f"  -> Created {len(plans)} subscription plans")


def remove_default_plans(apps, schema_editor):
    """Remove default plans."""
    SubscriptionPlan = apps.get_model('attendance', 'SubscriptionPlan')
    SubscriptionPlan.objects.filter(slug__in=['free-trial', 'basic', 'pro', 'enterprise']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('attendance', '0069_subscription_and_audit'),
    ]

    operations = [
        migrations.RunPython(create_default_plans, remove_default_plans),
    ]
