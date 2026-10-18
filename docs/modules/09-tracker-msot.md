# Module 09: Application Tracker & MSOT Admin Job Board

## 1. Overview
Module 09 provides student job application lifecycle tracking and institutional placement management for MSOT (Master of Science in Organizational Technology) students and placement officers:
1. **One-Click "Open & Apply"**: Launches verified application URLs in a separate tab while concurrently displaying an immediate logging prompt offering to capture the role into the application tracker as either `Applied` or `Saved`.
2. **Comprehensive Application Tracker**:
   - Manages company name, role title, job URL, application date, status (`Saved`, `Applied`, `Shortlisted`, `Interview`, `Offer`, `Rejected`), and notes.
   - Dual-view interface: Table view with sorting/filtering and Kanban Board view with drag/click status progression.
   - Configurable inactivity follow-up reminders (defaulting to 7 days without status change).
   - "Has Movement" filter highlighting applications whose status has evolved beyond `Saved` or `Applied`.
   - Complete status change history timeline for audit and progression tracking.
3. **MSOT Staff / Admin Job Board**:
   - Direct campus job and internship creation with benchmark eligibility gating: minimum readiness score (0–100), required skills, and target roles.
   - Pinned direct institutional postings: automatically displayed at the top of the job discovery feed exclusively for eligible students (ineligible students cannot see restricted institutional postings).
   - Applicant review portal: admins view students who applied to campus postings, inspect their latest readiness scores and verified profile skills, and promote candidate application statuses.
   - Role-Based Access Control (RBAC): student accounts attempting to access admin endpoints are strictly rejected with HTTP 403 Forbidden.
   - Duplicate prevention: attempting to apply twice to the same job returns HTTP 409 Conflict.

---

## 2. How It Works: Flow with Exact Files and Functions

### A. One-Click "Open & Apply" Flow
1. **Student clicks "Open & Apply"**:
   - In [JobDiscoveryPage.jsx](file:///Users/nakulmirai/Mirai%20Project/frontend/src/pages/JobDiscoveryPage.jsx) (`handleOpenAndApply`), `window.open(job.url, '_blank')` opens the external application portal in a new browser tab.
   - `setActiveApplyJob(job)` opens the in-app tracking prompt modal.
2. **Student chooses "Mark as Applied" or "Save to Tracker"**:
   - `handleLogApplication(status)` calls `api.createApplication` in [api.js](file:///Users/nakulmirai/Mirai%20Project/frontend/src/api.js).
   - Dispatches `POST /api/tracker` with `{company, role, link, job_id, status, notes}`.
   - [routers/tracker.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/tracker.py) (`create_application`):
     - Validates input via `ApplicationCreate` schema in [schemas.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/schemas.py).
     - Checks duplicate existence by `job_id` or `(company, role)` under active non-terminal statuses. If existing, raises `HTTPException(409, "Application already logged for this job")`.
     - Creates `Application` model with initial entry in `status_history`: `[{"status": status, "changed_at": iso_time, "note": "Initial application logged"}]`.
     - Returns `ApplicationResponse`.
   - UI updates card badge to `Applied` or `Saved` and offers direct navigation to the Tracker tab.

### B. Application Tracker & Movement Detection
1. **Fetching Applications**:
   - [ApplicationTrackerPage.jsx](file:///Users/nakulmirai/Mirai%20Project/frontend/src/pages/ApplicationTrackerPage.jsx) invokes `api.getApplications` with query filters (`status`, `has_movement`, `needs_followup`, `followup_days`).
   - [routers/tracker.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/tracker.py) (`list_applications`):
     - Queries `db.query(Application).filter(Application.user_id == current_user.id)`.
     - Evaluates `has_movement`: filters for items with `len(status_history) > 1` or current status in `{"Shortlisted", "Interview", "Offer", "Rejected"}`.
     - Evaluates `needs_followup`: checks if `(now - last_status_change_at).days >= followup_days` and status is not `Offer` or `Rejected`.
     - Returns `ApplicationListResponse` containing `items`, `total_count`, and KPI summary stats.
2. **Kanban & Table Views**:
   - Kanban organizes applications into 6 visual columns: `Saved`, `Applied`, `Shortlisted`, `Interview`, `Offer`, `Rejected`.
   - Table view provides tabular rendering with direct links, status badges, and quick actions.
   - Clicking an application opens the Details & Timeline Modal displaying the full historical trajectory (`status_history`).

### C. MSOT Institutional Posting & Eligibility Gating
1. **Admin Posts Campus Opening**:
   - Placement officer logs in with role `admin` and opens Admin Postings tab ([AdminJobBoardPage.jsx](file:///Users/nakulmirai/Mirai%20Project/frontend/src/pages/AdminJobBoardPage.jsx)).
   - Enters role details and eligibility criteria: `min_readiness_score`, `required_skills`, `target_roles`, and `is_pinned`.
   - Calls `POST /api/admin/jobs`.
   - [routers/admin.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/admin.py) (`create_admin_job`):
     - Enforces `require_admin` dependency; student users receive `HTTP 403 Forbidden`.
     - Persists `Job` model with `job_type`, `eligibility_criteria`, `is_pinned=True`, and `posted_by=current_admin.id`.
2. **Student Job Feed Discovery with Pinning**:
   - When a student requests `GET /api/jobs/discover`, [routers/jobs.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/jobs.py) passes their skills, target roles, and latest readiness score to `job_discovery_service.discover_jobs()`.
   - In [discovery_service.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/job_discovery/discovery_service.py) (`check_job_eligibility`):
     - **Score Gate**: Verifies `student_score >= min_readiness_score`.
     - **Skills Gate**: Verifies student possesses all required skills (case-insensitive).
     - **Role Gate**: Verifies overlap between student target roles and job target roles.
     - Ineligible students are excluded; the institutional job is omitted from their feed.
     - For eligible students, the job is attached with `source="msot_direct"`, `is_pinned=True`, and sorted to the top index of the feed ahead of public listings.
3. **Admin Applicant Management & Progression**:
   - Admin views candidates via `GET /api/admin/jobs/{id}/applicants` in [routers/admin.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/admin.py) (`get_job_applicants`).
   - Admin updates applicant status to `Interview` via `PATCH /api/admin/jobs/{id}/applicants/{app_id}/status` (`update_applicant_status`).
   - Updates student's `Application.status`, refreshes `last_status_change_at`, appends to `status_history`, and logs note `"Status updated by MSOT Placement Admin"`.
   - Student refreshes tracker or filters by "Has Movement": the application immediately reflects the promoted `Interview` stage.

---

## 3. Key Design Decisions and Rejected Alternatives
1. **Dynamic Eligibility Filtering vs. Static Job Feed Partitioning**:
   - *Decision*: Evaluate eligibility dynamically inside `discovery_service.py` at request time using the authenticated student's profile and readiness score.
   - *Rejected Alternative*: Partitioning jobs into separate tables or endpoints. Dynamic evaluation ensures that as soon as a student improves their readiness score (e.g. completes a mock interview or resume fix), institutional openings automatically unlock without data migration.
2. **Inactivity Reminders Computed On-the-Fly vs. Background Cron Jobs**:
   - *Decision*: Compute followup due status dynamically using `last_status_change_at` and user-configurable intervals (`followup_reminder_days`, default 7).
   - *Rejected Alternative*: Background daemon sending push emails. A lightweight calculated query guarantees real-time accuracy, avoids background process deadlocks, and respects local offline operation.
3. **Structured Status History in JSON Column**:
   - *Decision*: Store `status_history` as a JSON array of chronological transition objects `[{"status": ..., "changed_at": ..., "note": ...}]` on the `Application` table.
   - *Rejected Alternative*: Creating a separate `ApplicationStatusEvent` relational table. The JSON approach keeps SQLite operations atomic, simplifies serialization, and guarantees fast reads for the Kanban timeline modal.
4. **Strict Duplicate Prevention (HTTP 409)**:
   - *Decision*: Prevent accidental duplicate submissions by checking `job_id` or matching active `(company, role)`.
   - *Rejected Alternative*: Silently updating existing applications. Explicit 409 Conflict alerts the user that the application is already tracked.

---

## 4. Shortcuts and Faked Parts
- **None**: No hardcoded jobs, fake applicants, or faked movement data are used.
- All applications are stored in SQLite and linked via foreign keys to `User` and `Job`.
- Readiness score checks query real `ReadinessScore` table records.
- All permissions are enforced via FastAPI `Depends(require_admin)` and `Depends(get_current_user)`.

---

## 5. Verify It Yourself

### Step 1: Automated Playwright Dual-Session Flow
Run the complete automated browser verification script:
```bash
./backend/venv/bin/python3 backend/tests/test_browser_tracker_flow.py
```
**Expected Output**:
```
--- STEP 1: Admin Session ---
✓ Admin successfully published job with benchmark eligibility criteria.
--- STEP 2: Ineligible Student Session ---
✓ Ineligible student correctly does NOT see the restricted campus opening.
--- STEP 3: Eligible Student Session ---
✓ Eligible student sees the campus opening pinned at the top.
✓ Student applied via One-Click Open & Apply and logged as Applied.
✓ Card successfully rendered in Application Tracker Kanban.
✓ Table view successfully rendered with tabular row.
--- STEP 4: Admin Promotes Student ---
✓ Admin viewed applicants and promoted student to 'Interview'.
--- STEP 5: Student Verifies Movement ---
✓ 'Has Movement' filter successfully displays the updated application.
✓ Timeline modal verified with status transition history.
=== ALL DUAL-SESSION BROWSER E2E STEPS VERIFIED SUCCESSFULLY ===
```

### Step 2: Run Backend Unit & Integration Tests
Run pytest targeting tracker and MSOT admin tests:
```bash
backend/venv/bin/pytest -v backend/tests/test_tracker_msot.py
```
**Expected Output**: 5 passed tests (E2E workflow, RBAC permissions, duplicate 409 handling, follow-up reminders, CRUD operations).

### Step 3: Run Full Monorepo Test Suite
Confirm zero regressions across all modules:
```bash
make test
```
**Expected Output**: 94 passed tests across all 9 modules.

### Step 4: Interactive Browser Verification
1. Start frontend and backend with `make dev`.
2. Open `http://localhost:5173` and register as an Admin (`Role: MSOT Staff / Admin`).
3. Click **Admin Postings** tab. Fill out the campus job form with title `"Lead Cloud Fellow"`, required skills `"React, TypeScript"`, and min readiness score `75`. Click **Publish Campus Opening**.
4. Log out. Register as a Student with Backend skills only. Navigate to **Jobs**: confirm `"Lead Cloud Fellow"` does NOT appear.
5. In **Profile & My Data**, add `"React, TypeScript"` to skills and compute a readiness score $\ge 75$. Return to **Jobs**: `"Lead Cloud Fellow"` is now pinned at the very top with gold badge `MSOT Campus Direct Posting • Pinned for Eligible Students`.
6. Click **Open & Apply** -> **Mark as Applied**.
7. Navigate to **Application Tracker**: verify the card appears in the `Applied` column. Toggle between Kanban and Table views.
