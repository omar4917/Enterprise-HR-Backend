"""
Management command to create dummy organization data for testing.
Run with: python manage.py create_dummy_organizations
"""

from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from attendance.models import Organization, Device, OrganizationSettings, OrganizationUser, Employee
from django.utils import timezone
import random


class Command(BaseCommand):
    help = 'Create dummy organizations with devices and employees for testing'

    def handle(self, *args, **options):
        # Sample company data
        companies = [
            {
                'name': 'Tech Solutions Ltd',
                'slug': 'tech-solutions',
                'email': 'admin@techsolutions.com',
                'phone': '+880-1711-111111',
                'address': 'House 12, Road 5, Gulshan-1, Dhaka',
                'max_employees': 100,
                'max_devices': 5,
                'devices': [
                    {'device_id': 'ts_main_gate', 'device_name': 'Main Gate Tablet', 'location': 'Main Entrance'},
                    {'device_id': 'ts_floor_1', 'device_name': 'Floor 1 Device', 'location': '1st Floor Reception'},
                ],
                'employees': [
                    {'employee_id': 'TS001', 'name': 'Ahmed Rahman', 'department': 'Engineering', 'designation': 'Senior Developer'},
                    {'employee_id': 'TS002', 'name': 'Fatima Begum', 'department': 'Engineering', 'designation': 'Developer'},
                    {'employee_id': 'TS003', 'name': 'Mohammad Hasan', 'department': 'HR', 'designation': 'HR Manager'},
                    {'employee_id': 'TS004', 'name': 'Ayesha Khatun', 'department': 'Finance', 'designation': 'Accountant'},
                ]
            },
            {
                'name': 'Global Trading Co.',
                'slug': 'global-trading',
                'email': 'info@globaltrading.bd',
                'phone': '+880-1722-222222',
                'address': 'Plot 45, Motijheel C/A, Dhaka-1000',
                'max_employees': 50,
                'max_devices': 3,
                'devices': [
                    {'device_id': 'gt_reception', 'device_name': 'Reception Kiosk', 'location': 'Reception Desk'},
                ],
                'employees': [
                    {'employee_id': 'GT001', 'name': 'Karim Uddin', 'department': 'Sales', 'designation': 'Sales Manager'},
                    {'employee_id': 'GT002', 'name': 'Nasreen Akter', 'department': 'Sales', 'designation': 'Sales Executive'},
                    {'employee_id': 'GT003', 'name': 'Rafiq Ahmed', 'department': 'Operations', 'designation': 'Operations Head'},
                ]
            },
            {
                'name': 'Sunrise Garments',
                'slug': 'sunrise-garments',
                'email': 'hr@sunrisegarments.com',
                'phone': '+880-1733-333333',
                'address': 'BSCIC Industrial Area, Gazipur',
                'max_employees': 500,
                'max_devices': 10,
                'devices': [
                    {'device_id': 'sg_gate_a', 'device_name': 'Gate A Device', 'location': 'Main Gate A'},
                    {'device_id': 'sg_gate_b', 'device_name': 'Gate B Device', 'location': 'Main Gate B'},
                    {'device_id': 'sg_floor_1', 'device_name': 'Floor 1 Scanner', 'location': 'Production Floor 1'},
                    {'device_id': 'sg_floor_2', 'device_name': 'Floor 2 Scanner', 'location': 'Production Floor 2'},
                ],
                'employees': [
                    {'employee_id': 'SG001', 'name': 'Abdul Malik', 'department': 'Production', 'designation': 'Production Manager'},
                    {'employee_id': 'SG002', 'name': 'Shahida Parvin', 'department': 'Quality', 'designation': 'QC Supervisor'},
                    {'employee_id': 'SG003', 'name': 'Jamal Hossain', 'department': 'Production', 'designation': 'Line Supervisor'},
                    {'employee_id': 'SG004', 'name': 'Rina Begum', 'department': 'HR', 'designation': 'HR Executive'},
                    {'employee_id': 'SG005', 'name': 'Faruk Ahmed', 'department': 'Maintenance', 'designation': 'Maintenance Head'},
                ]
            },
            {
                'name': 'Digital Media Agency',
                'slug': 'digital-media',
                'email': 'hello@digitalmedia.agency',
                'phone': '+880-1744-444444',
                'address': 'Level 8, Shanta Western Tower, Banani, Dhaka',
                'max_employees': 30,
                'max_devices': 2,
                'devices': [
                    {'device_id': 'dma_office', 'device_name': 'Office Tablet', 'location': 'Main Office'},
                ],
                'employees': [
                    {'employee_id': 'DMA001', 'name': 'Tanvir Islam', 'department': 'Creative', 'designation': 'Creative Director'},
                    {'employee_id': 'DMA002', 'name': 'Sadia Rahman', 'department': 'Marketing', 'designation': 'Marketing Manager'},
                    {'employee_id': 'DMA003', 'name': 'Imran Khan', 'department': 'Development', 'designation': 'Web Developer'},
                ]
            },
            {
                'name': 'Healthcare Plus Hospital',
                'slug': 'healthcare-plus',
                'email': 'admin@healthcareplus.com.bd',
                'phone': '+880-1755-555555',
                'address': 'House 25, Road 12, Dhanmondi, Dhaka',
                'max_employees': 200,
                'max_devices': 8,
                'devices': [
                    {'device_id': 'hp_main', 'device_name': 'Main Reception', 'location': 'Main Reception'},
                    {'device_id': 'hp_emergency', 'device_name': 'Emergency Dept', 'location': 'Emergency Department'},
                    {'device_id': 'hp_opd', 'device_name': 'OPD Scanner', 'location': 'OPD Building'},
                ],
                'employees': [
                    {'employee_id': 'HP001', 'name': 'Dr. Aminul Haque', 'department': 'Medical', 'designation': 'Chief Doctor'},
                    {'employee_id': 'HP002', 'name': 'Nurse Fatema', 'department': 'Nursing', 'designation': 'Head Nurse'},
                    {'employee_id': 'HP003', 'name': 'Rashid Khan', 'department': 'Admin', 'designation': 'Hospital Admin'},
                    {'employee_id': 'HP004', 'name': 'Sultana Begum', 'department': 'Pharmacy', 'designation': 'Pharmacist'},
                ]
            }
        ]

        created_orgs = 0
        created_devices = 0
        created_employees = 0

        for company_data in companies:
            # Check if org already exists
            org, org_created = Organization.objects.get_or_create(
                slug=company_data['slug'],
                defaults={
                    'name': company_data['name'],
                    'email': company_data['email'],
                    'phone': company_data['phone'],
                    'address': company_data['address'],
                    'max_employees': company_data['max_employees'],
                    'max_devices': company_data['max_devices'],
                    'is_active': True,
                }
            )

            if org_created:
                created_orgs += 1
                self.stdout.write(f"  [+] Created organization: {org.name}")

                # Create settings
                OrganizationSettings.objects.get_or_create(organization=org)

                # Create devices
                for device_data in company_data['devices']:
                    device, device_created = Device.objects.get_or_create(
                        device_id=device_data['device_id'],
                        defaults={
                            'organization': org,
                            'device_name': device_data['device_name'],
                            'location': device_data['location'],
                            'is_active': True,
                        }
                    )
                    if device_created:
                        created_devices += 1
                        self.stdout.write(f"    - Device: {device.device_name}")

                # Create employees
                for emp_data in company_data['employees']:
                    emp, emp_created = Employee.objects.get_or_create(
                        employee_id=emp_data['employee_id'],
                        defaults={
                            'organization': org,
                            'name': emp_data['name'],
                            'department': emp_data['department'],
                            'designation': emp_data['designation'],
                            'is_active': True,
                            'monthly_salary': random.randint(25000, 80000),
                        }
                    )
                    if emp_created:
                        created_employees += 1
                        self.stdout.write(f"    - Employee: {emp.name}")
            else:
                self.stdout.write(f"  [*] Organization already exists: {org.name}")

        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS(f'Done! Created:'))
        self.stdout.write(self.style.SUCCESS(f'  • {created_orgs} organizations'))
        self.stdout.write(self.style.SUCCESS(f'  • {created_devices} devices'))
        self.stdout.write(self.style.SUCCESS(f'  • {created_employees} employees'))
