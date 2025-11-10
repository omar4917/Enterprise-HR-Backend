import os
import random
from datetime import datetime, timedelta

folder = r"C:\Users\BARA BD\Desktop\Attendence Control Project\Test\OUT"

for i in range(1, 201):
    file_path = os.path.join(folder, f"EMP{i:03}.jpg")
    if os.path.exists(file_path):
        base_date = datetime.today().replace(
            hour=11, minute=40, second=0, microsecond=0
        )
        random_seconds = random.randint(0, 360 * 60)  # 0 → 5400 seconds
        random_time = base_date + timedelta(seconds=random_seconds)
        ts = random_time.timestamp()
        os.utime(file_path, (ts, ts))

print("✅ Randomized timestamps set for all images between 8:00 AM and 9:30 AM.")
