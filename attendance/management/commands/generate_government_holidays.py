from django.core.management.base import BaseCommand
from datetime import datetime
from attendance.models import GovernmentHoliday, BulkHoliday


class Command(BaseCommand):
    help = 'Generate government holidays for specified year'

    def add_arguments(self, parser):
        parser.add_argument(
            '--year',
            type=int,
            default=datetime.now().year,
            help='Year to generate holidays for (default: current year)'
        )
        parser.add_argument(
            '--setup',
            action='store_true',
            help='Setup default Bangladesh government holidays'
        )

    def handle(self, *args, **options):
        year = options['year']
        
        if options['setup']:
            self.setup_bangladesh_holidays()
        
        # Generate holidays for the year
        generated_count = 0
        processed_count = 0
        
        for gov_holiday in GovernmentHoliday.objects.filter(is_active=True):
            holiday = gov_holiday.generate_for_year(year)
            if holiday:
                generated_count += 1
                # Auto-process the holiday
                records_created = holiday.process_holiday_records()
                processed_count += records_created
                self.stdout.write(
                    self.style.SUCCESS(
                        f'Generated and processed: {holiday.name} ({records_created} records)'
                    )
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Generated {generated_count} government holidays for {year}'
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f'Created {processed_count} attendance records'
            )
        )

    def setup_bangladesh_holidays(self):
        """Setup default Bangladesh government holidays"""
        holidays = [
            {"name": "International Mother Language Day", "month": 2, "day": 21},
            {"name": "Independence Day", "month": 3, "day": 26},
            {"name": "Bengali New Year", "month": 4, "day": 14},
            {"name": "May Day", "month": 5, "day": 1},
            {"name": "National Mourning Day", "month": 8, "day": 15},
            {"name": "Victory Day", "month": 12, "day": 16},
            {"name": "Christmas Day", "month": 12, "day": 25},
        ]
        
        created_count = 0
        for holiday_data in holidays:
            holiday, created = GovernmentHoliday.objects.get_or_create(
                name=holiday_data["name"],
                month=holiday_data["month"],
                day=holiday_data["day"],
                defaults={
                    "description": f"Bangladesh Government Holiday - {holiday_data['name']}"
                }
            )
            if created:
                created_count += 1
        
        self.stdout.write(
            self.style.SUCCESS(f'Setup {created_count} new government holiday templates')
        )