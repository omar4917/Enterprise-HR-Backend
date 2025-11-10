# from django.core.management.base import BaseCommand
# from attendance.models import AttendanceRecord, Employee
# from datetime import datetime, timedelta, date
# import random


# class Command(BaseCommand):
#     help = "Generate realistic attendance records for Aug–Oct 2025 with 90–95% Present days"

#     def handle(self, *args, **kwargs):
#         employees = Employee.objects.all()
#         created_count = 0

#         for month in [8, 9, 10]:  # August, September, October
#             year = 2025
#             start_date = date(year, month, 1)
#             days_in_month = (
#                 start_date.replace(month=month % 12 + 1, day=1) - timedelta(days=1)
#             ).day

#             for emp in employees:
#                 # ✅ Identify working days (non-Friday)
#                 working_days = [
#                     date(year, month, day)
#                     for day in range(1, days_in_month + 1)
#                     if date(year, month, day).weekday() != 4
#                 ]

#                 # ✅ Select 90–95% of working days as Present
#                 present_ratio = random.randint(90, 95)
#                 present_count = int(len(working_days) * present_ratio / 100)
#                 present_days = set(random.sample(working_days, present_count))

#                 for day in range(1, days_in_month + 1):
#                     current_date = date(year, month, day)

#                     if AttendanceRecord.objects.filter(
#                         employee=emp, date=current_date
#                     ).exists():
#                         continue

#                     # ✅ Always mark Friday as Off Day
#                     if current_date.weekday() == 4:
#                         status = "Off Day"
#                     elif current_date in present_days:
#                         status = "Present"
#                     else:
#                         status = random.choice(
#                             [
#                                 "Absent",
#                                 "Early Leave",
#                                 "Half Day",
#                                 "On Leave",
#                                 "Holiday",
#                                 "Pending",
#                             ]
#                         )

#                     record = AttendanceRecord(
#                         employee=emp,
#                         date=current_date,
#                         status=status,
#                     )

#                     # ✅ Realistic time ranges for Present
#                     if status == "Present":
#                         checkin_hour = 8 if random.random() < 0.3 else 9
#                         checkin_minute = (
#                             random.randint(45, 59)
#                             if checkin_hour == 8
#                             else random.randint(0, 15)
#                         )
#                         checkout_hour = 17
#                         checkout_minute = random.randint(0, 30)

#                         record.checkin_time = datetime(
#                             year, month, day, checkin_hour, checkin_minute
#                         )
#                         record.checkout_time = datetime(
#                             year, month, day, checkout_hour, checkout_minute
#                         )

#                     record.save()
#                     created_count += 1

#         self.stdout.write(
#             self.style.SUCCESS(
#                 f"✅ Created {created_count} realistic attendance records for Aug–Oct 2025"
#             )
#         )


from django.core.management.base import BaseCommand
from attendance.models import AttendanceRecord, Employee
from datetime import datetime, timedelta, date
import random


class Command(BaseCommand):
    help = "Generate realistic attendance records for Aug–Oct 2025 with 90–95% Present days"

    def handle(self, *args, **kwargs):
        employees = Employee.objects.all()
        created_count = 0

        for month in [8, 9, 10]:  # August, September, October
            year = 2025
            start_date = date(year, month, 1)
            days_in_month = (
                start_date.replace(month=month % 12 + 1, day=1) - timedelta(days=1)
            ).day

            for emp in employees:
                # ✅ Identify working days (non-Friday)
                working_days = [
                    date(year, month, day)
                    for day in range(1, days_in_month + 1)
                    if date(year, month, day).weekday() != 4
                ]

                # ✅ Select 90–95% of working days as Present
                present_ratio = random.randint(90, 95)
                present_count = int(len(working_days) * present_ratio / 100)
                present_days = set(random.sample(working_days, present_count))

                for day in range(1, days_in_month + 1):
                    current_date = date(year, month, day)

                    if AttendanceRecord.objects.filter(
                        employee=emp, date=current_date
                    ).exists():
                        continue

                    # ✅ Always mark Friday as Off Day
                    if current_date.weekday() == 4:
                        status = "Off Day"
                    elif current_date in present_days:
                        status = "Present"
                    else:
                        status = random.choice(
                            [
                                "Absent",
                                "Early Leave",
                                "Half Day",
                                "On Leave",
                                "Holiday",
                                "Pending",
                            ]
                        )

                    record = AttendanceRecord(
                        employee=emp,
                        date=current_date,
                        status=status,
                    )

                    # ✅ Realistic time ranges for Present
                    if status == "Present":
                        # Check-in: 7:50 to 9:00
                        checkin_hour = (
                            7
                            if random.random() < 0.2
                            else 8 if random.random() < 0.5 else 9
                        )
                        if checkin_hour == 7:
                            checkin_minute = random.randint(50, 59)
                        elif checkin_hour == 8:
                            checkin_minute = random.randint(0, 59)
                        else:  # 9
                            checkin_minute = random.randint(0, 0)  # 9:00 exactly

                        # Check-out: 14:00 to 18:00
                        checkout_hour = random.randint(14, 18)
                        checkout_minute = random.randint(0, 59)

                        record.checkin_time = datetime(
                            year, month, day, checkin_hour, checkin_minute
                        )
                        record.checkout_time = datetime(
                            year, month, day, checkout_hour, checkout_minute
                        )

                    record.save()
                    created_count += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"✅ Created {created_count} realistic attendance records for Aug–Oct 2025"
            )
        )
