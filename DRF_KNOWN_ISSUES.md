# DRF Migration — Known Issues & Future Work

## 1. Legacy Endpoints Still Active
The following 6 endpoints are still served by the old function-based views in `attendance/urls.py` because they contain complex custom business logic (face recognition, binary image handling, FCM token registration) that cannot be trivially converted to a DRF `ModelViewSet`:

| Endpoint | Reason Kept |
|----------|-------------|
| `POST /api/validate-admin/` | HTTP Basic Auth decoding + PHP login contract |
| `POST /api/enroll/` | Base64 facial_template + employee image upload |
| `POST /api/enroll-unknown/` | Creates employee from unknown face scan |
| `POST /api/check-in/` | Face recognition attendance event + cooldown logic + image capture |
| `POST /api/livefeed/` | Multipart image upload with retention/purge logic |
| `POST /api/register-token/` | FCM device token registration |

**Action:** Each of these should be migrated to a custom `@action` method on the relevant ViewSet (e.g., `EmployeeViewSet.enroll`) or a standalone `APIView`.

---

## 2. Android APK Pagination Format
DRF wraps list responses in a paginated envelope:
```json
{"count": 42, "next": "...?page=2", "previous": null, "results": [...]}
```
The Android APK may expect a **flat JSON array** instead. If so, set `pagination_class = None` on APK-facing ViewSets, or create a custom pagination class.

---

## 3. Swagger Type Hint Warnings
`drf-spectacular` reports 35 cosmetic warnings about `SerializerMethodField` methods missing return type annotations. Fix by adding Python type hints:
```python
# Before
def get_employee_name(self, obj):
    return obj.employee.name

# After
def get_employee_name(self, obj) -> str | None:
    return obj.employee.name if obj.employee else None
```

---

## 4. PDF & Export Endpoints Not Migrated
These template-rendering and file-download views remain in `views.py`:
- `attendance-dashboard/pdf/`
- `attendance-dashboard/pdf/bulk/`
- `attendance-dashboard/pdf/combined/`
- `salary-report/pdf/`
- `moderator-edit/`

These are Django template views, not JSON APIs, so they don't need DRF migration — but they could benefit from proper authentication via DRF permissions.

---

## 5. Import/Export APIs Removed
The old `/api/export/`, `/api/import/`, `/api/export-data/`, `/api/import-data/`, `/api/staged-upload/`, and `/api/export-job/` endpoints were removed with the legacy routes. If needed, re-implement them as custom `@action` methods on the relevant ViewSets.

---

## 6. Analytics API Removed
`/api/analytics/` was removed. Re-implement as a custom `@action` on `OrganizationViewSet` or a standalone `APIView`.
