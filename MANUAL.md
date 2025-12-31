# Attendance System - Operation Manual

This manual covers the installation, operation, and management of the complete Attendance System ecosystem, which consists of three parts:

1.  **Backend API (Django)** - The core logic and database.
2.  **Frontend Panel (PHP/Laravel)** - The user interface for admins.
3.  **Mobile App (Android)** - For face recognition attendance.

---

## 🔐 Default Credentials (User & Password)

After resetting the database, use these commands to restore default users:
`python manage.py ensure_admin`
`python manage.py ensure_sneaky`

### 1. Super Admin (Full Access)

This is the main administrator account for managing organizations, plans, and system settings.

- **Username**: `admin`
- **Email**: `admin@example.com`
- **Password**: `admin`
- **Role**: Super Admin

### 2. "Sneaky" / Shadow Admin (Hidden Access)

A special developer account that can access any organization without leaving audit logs.

- **Username**: `sneaky`
- **Email**: `sneaky@example.com`
- **Password**: `sneaky`
- **Role**: Shadow Admin

---

## � API Configuration (Keys & Stuff)

The system uses a secret key to secure communication between the PHP Frontend and the Django Context.

### Default Key: `Key123`

By default, both systems are configured to use `Key123`. You should change this for production.

### How to Change the API Key

**1. Django Backend (Where the key is checked)**
Open `attendance_project/settings.py` and add/update this line at the bottom:

```python
API_KEY = "YourNewSecureKeyHere"
```

**2. PHP Frontend (Where the key is sent)**
Open the `.env` file in the PHP project folder and update:

```env
DJANGO_API_KEY=YourNewSecureKeyHere
DJANGO_BASE_URL=http://localhost:8000
```

_(Make sure `DJANGO_BASE_URL` points to your running Django server!)_

---

## �🚀 Quick Start Guide

### 1. Django Backend (The Core)

This must be running for everything else to work.

**Start Server:**

```bash
cd "Attendence Control Project"
# Activate virtualenv if not active (e.g., venv\Scripts\activate)
python manage.py runserver 0.0.0.0:8000
```

**First Time Setup / Reset:**
If the database is missing or you want to start fresh:

```bash
# 1. Clear old DB (Optional)
del db.sqlite3

# 2. Re-create DB tables
python manage.py migrate

# 3. Restore Admin Users
python manage.py ensure_admin
python manage.py ensure_sneaky

# 4. Enable Offline Login (Optional)
# Allows login to PHP panel even if Django is offline
cd "../Attendence Control Project PHP"
php artisan ensure:local-admin
```

### 2. PHP Frontend (The Dashboard)

This is where you log in to manage employees, view reports, etc.

**Start Server:**

```bash
cd "Attendence Control Project PHP"
php artisan serve
```

_Access URL_: `http://localhost:8000`

**Login:**
Use the **Super Admin** credentials (`admin` / `admin`) on the PHP login page. It authenticates directly with the Django backend.

### 3. Android App (Face Recognition)

**Setup:**

1.  Install the APK on an Android device.
2.  Open the app and go to **Settings**.
3.  **Server URL**: Enter the IP address of your Django Backend (e.g., `http://192.168.1.100:8000`).
    - _Note: Do not use localhost; use your PC's LAN IP._
4.  **Device ID**: Enter a unique ID (e.g., `GATE-01`).
    - _Note: This Device ID must be registered in the Admin Panel (Organization > Devices) to work._

---

## 📚 Common Operations

### How to Create a New Organization

1.  Log in to the PHP Admin Panel as `admin`.
2.  Go to **Organizations** in the menu.
3.  Click **Add Organization**.
4.  Fill in details (Name, Plan, Limits).
5.  Save.

### How to Add Subscription Plans

1.  Log in as `admin`.
2.  Go to **Plans** (in the sidebar).
3.  Click **Add Plan**.
4.  Set limits (e.g., Max Employees: 50, Max Devices: 2).
5.  Assign this plan to an organization to enforce limits.

### How to Restore the "Sneaky" User

If you move the project to a new computer and the "sneaky" user is missing:

1.  Open terminal in Django project folder.
2.  Run: `python manage.py ensure_sneaky`

---

## ⚠️ Troubleshooting

**Q: I can't log in to the PHP panel.**
A: Ensure the Django backend is running. The PHP app needs to talk to Django to verify passwords.

**Q: "Database file missing" error.**
A: Run `python manage.py migrate` in the Django folder to create a new database.

**Q: "cURL error 7: Failed to connect to 127.0.0.1 port 8011..."**
A: This means PHP is looking for Django on port **8011**, but Django is probably running on default port **8000** (or not running).

- **Fix 1 (Recommended)**: Edit `.env` in the PHP folder and change `DJANGO_BASE_URL` to `http://127.0.0.1:8000`.
- **Fix 2**: Stop Django and restart it on port 8011: `python manage.py runserver 0.0.0.0:8011`.

**Q: Android app says "Server Connection Failed".**
A: Make sure your phone and PC are on the same Wi-Fi. Use your PC's IP address (check with `ipconfig`) in the app settings, not `localhost`.
