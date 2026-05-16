# Enterprise HR Backend — Known Issues & Future Work

This document tracks all known issues, limitations, and planned improvements across the entire project.

---

# 🔴 Critical / Infrastructure

## 1. Ephemeral SQLite Database (Render Free Tier)
Render's free tier uses an **ephemeral filesystem**. The `db.sqlite3` file is wiped on every deploy, restart, or sleep cycle. All data (employees, attendance, settings) is lost.

**Impact:** Every restart triggers `build.sh` which re-runs migrations and `seed_db` to inject dummy data. Real production data cannot persist.

**Fix:** Migrate to a managed PostgreSQL database (Render offers one, or use Supabase/Neon free tier). Update `DATABASES` in `settings.py` to use `dj-database-url`.

---

## 2. Ephemeral Media Files (Uploaded Images)
Employee photos, check-in/check-out images, and live feed captures are stored on disk (`/media/`). These are also wiped on every deploy/restart.

**Fix:** Integrate an S3-compatible storage service (Cloudflare R2, AWS S3, or Backblaze B2) using `django-storages`. Update `DEFAULT_FILE_STORAGE` in `settings.py`.

---

# 🟡 DRF Migration (Branch: `feature/drf-refactor`)

## 3. Legacy Endpoints Still Active
6 endpoints remain as old function-based views because they have complex custom logic:

| Endpoint | Reason Kept |
|----------|-------------|
| `POST /api/validate-admin/` | HTTP Basic Auth decoding + PHP login contract |
| `POST /api/enroll/` | Base64 facial_template + employee image upload |
| `POST /api/enroll-unknown/` | Creates employee from unknown face scan |
| `POST /api/check-in/` | Face recognition attendance event + cooldown + image capture |
| `POST /api/livefeed/` | Multipart image upload with retention/purge logic |
| `POST /api/register-token/` | FCM device token registration |

**Fix:** Migrate each to a custom `@action` on the relevant ViewSet or a standalone `APIView`.

---

## 4. Android APK Pagination Format
DRF wraps list responses in `{"count", "next", "previous", "results": [...]}`. The Android APK may expect a flat JSON array.

**Fix:** Set `pagination_class = None` on APK-facing ViewSets, or create a custom pagination class.

---

## 5. Swagger Type Hint Warnings
35 cosmetic warnings from `drf-spectacular` about missing return type annotations on `SerializerMethodField` methods.

**Fix:** Add Python type hints like `-> str | None` to all `get_*` methods in `serializers.py`.

---

## 6. Import/Export & Analytics APIs Removed
The following legacy endpoints were removed during DRF migration and need re-implementation:
- `/api/export/`, `/api/import/`
- `/api/export-data/`, `/api/import-data/`
- `/api/staged-upload/`, `/api/export-job/`
- `/api/analytics/`

**Fix:** Re-implement as `@action` methods or standalone `APIView` classes.

---

# 🟡 Deployment & Configuration

## 7. IntegrationSetting 500 Error on Fresh Deploy
Navigating to the `IntegrationSetting` admin add page can cause a 500 error if the singleton record doesn't exist yet and the admin template tries to render fields before the model is initialized.

**Fix:** The `seed_db` command now creates a default `IntegrationSetting` record. As long as `build.sh` runs `seed_db`, this is resolved. But if the database is wiped without running seed, the issue returns.

---

## 8. FCM_SERVER_KEY Not Required
The `FCM_SERVER_KEY` environment variable is optional. Push notifications will silently fail if it's not set, but the app won't crash. This is by design.

---

## 9. Admin Panel at Root URL
The Django admin panel is served at `/` (root) instead of the standard `/admin/`. Requests to `/admin/` are redirected to `/`. This was an intentional decision for the Render deployment but may confuse developers.

---

# 🟢 Nice-to-Have / Enhancements

## 10. PDF Views Lack DRF Authentication
The PDF export endpoints (`attendance-dashboard/pdf/`, `salary-report/pdf/`) use Django's `@staff_member_required` but don't integrate with the DRF permission system. They work fine but are inconsistent with the new architecture.

---

## 11. Jazzmin Fully Removed
`django-jazzmin` has been completely uninstalled. The admin panel now uses the default Django admin theme. If a premium theme is desired later, consider `django-unfold` or `django-grappelli`.

---

## 12. No Automated Tests
The project currently has zero unit tests or integration tests. Adding a test suite (`pytest-django`) would significantly improve reliability, especially for the complex attendance status calculation logic and salary computations.
