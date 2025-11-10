# import requests
# import os

# # Folder to save images
# folder = r"C:\Users\BARA BD\Desktop\Attendence Control Project\media\checkin_images" # noqa
# os.makedirs(folder, exist_ok=True)

# # Download 200 fake face images
# for i in range(1, 201):
#     url = "https://thispersondoesnotexist.com/image"
#     r = requests.get(url)
#     if r.status_code == 200:
#         file_path = os.path.join(folder, f"EMP{i:03}.jpg")  # EMP001.jpg, EMP002.jpg ... # noqa
#         with open(file_path, "wb") as f:
#             f.write(r.content)
#         print(f"Downloaded {file_path}")
#     else:
#         print(f"Failed to download image {i}")


from PIL import Image, ImageDraw, ImageFont # noqa
import os
import random

folder = r"C:\Users\BARA BD\Desktop\Attendence Control Project\Test\IN"
os.makedirs(folder, exist_ok=True)

for i in range(1, 101):
    # Create a 200x200 image with random background color
    img = Image.new(
        "RGB",
        (200, 200),
        color=(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255)), # noqa
    )

    # Optionally, write the employee ID on the image
    draw = ImageDraw.Draw(img)
    draw.text((50, 90), f"EMP{i:03}", fill=(255, 255, 255))  # white text

    # Save the image
    img.save(os.path.join(folder, f"EMP{i:03}.jpg"))

print("✅ 200 placeholder images created locally.")
