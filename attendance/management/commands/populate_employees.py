# from django.core.management.base import BaseCommand
# from faker import Faker
# from attendance.models import Employee  # replace with your actual app name


# class Command(BaseCommand):
#     help = "Populate DB with 200 fake employees for testing"

#     def handle(self, *args, **kwargs):
#         fake = Faker()
#         employees = []

#         for _ in range(200):
#             employees.append(
#                 Employee(
#                     employee_id=fake.unique.bothify(text="EMP####"),
#                     name=fake.name(),
#                     email=fake.unique.email(),
#                     department=fake.job(),
#                     phone=fake.phone_number(),
#                     designation=fake.job(),
#                     branch=fake.city(),
#                 )
#             )

#         Employee.objects.bulk_create(employees)
#         self.stdout.write(
#             self.style.SUCCESS("✅ 200 fake employees created successfully!")
#         )


from django.core.management.base import BaseCommand
from faker import Faker
from attendance.models import Employee  # replace with your actual app name


class Command(BaseCommand):
    help = "Populate DB with 200 fake employees for testing (consecutive IDs)"

    def handle(self, *args, **kwargs):
        fake = Faker()
        employees = []

        for i in range(1, 201):  # 1 to 200
            employee_id = f"EMP{i:03}"  # EMP001, EMP002, ..., EMP200
            employees.append(
                Employee(
                    employee_id=employee_id,
                    name=fake.name(),
                    email=fake.unique.email(),
                    department=fake.job(),
                    phone=fake.phone_number(),
                    designation=fake.job(),
                    branch=fake.city(),
                )
            )

        Employee.objects.bulk_create(employees)
        self.stdout.write(
            self.style.SUCCESS("✅ 200 fake employees created successfully!")
        )
