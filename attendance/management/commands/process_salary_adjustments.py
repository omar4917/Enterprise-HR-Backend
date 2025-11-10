from django.core.management.base import BaseCommand
from datetime import date
from ...utils.salary_helpers import process_monthly_salary_adjustments


class Command(BaseCommand):
    help = 'Process automatic salary adjustments (bonuses/fines) for a given month'

    def add_arguments(self, parser):
        parser.add_argument('--year', type=int, default=date.today().year)
        parser.add_argument('--month', type=int, default=date.today().month)

    def handle(self, *args, **options):
        year = options['year']
        month = options['month']
        
        self.stdout.write(f'Processing salary adjustments for {year}-{month:02d}...')
        
        processed_count = process_monthly_salary_adjustments(year, month)
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {processed_count} salary adjustments for {year}-{month:02d}'
            )
        )