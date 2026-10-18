# Module 02: Profile Intake

## 1. What the Module Does
Module 02 implements the **Profile Intake & Privacy Pipeline** for MSOT students:
- **Mandatory Consent Gate**: Requires explicit student consent before reading, parsing, or storing any resume, LinkedIn, GitHub, LeetCode, or project data. Any intake attempt without consent is rejected with a clean HTTP 400 Bad Request.
- **ATS Resume Parser**: Parses uploaded resumes in PDF (`PyMuPDF`) and Word DOCX (`python-docx`) formats into exact page count, canonical sections (`education`, `experience`, `projects`, `skills`, `achievements`), extracted skills matching a benchmark taxonomy, structured projects, and web hyperlinks.
- **LinkedIn Profile Intake**: Accepts LinkedIn official "Save to PDF" exports or copy-pasted profile text, extracting headline, about summary, experience blocks, and skills.
- **Public Profiles & Extracurriculars**: Collects GitHub and LeetCode usernames/URLs, project showcases (title, repo URL, live URL, tech stack, description), and achievements (hackathons, certifications, club leadership). Supports intake via form and chat messages.
- **"My Data" Transparency & Complete Deletion**: Fully complies with Rule 4 by displaying all stored fields and tracked files. Provides "Clear Profile Data & Files" (resets database rows and physically unlinks uploaded files from disk) and "Delete My Account & All Data" (cascades deletion of the User, Profile, all associated DB rows, and physically removes all files from disk).
- **Tenant Isolation**: Strictly prevents Student A from reading or modifying Student B's data (enforcing 403 Forbidden).

---

## 2. How It Works (Flow with Exact Files and Functions)

### A. Consent Enforcement Flow
1. **Consent Verification**:
   - In [profile.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/profile.py), any endpoint mutating profile data (`PUT /api/profile/me`, `POST /api/profile/resume`, `POST /api/profile/linkedin/upload`, `POST /api/profile/linkedin/paste`, `POST /api/profile/chat-intake`) calls `get_or_create_profile(current_user, db)`.
   - If `not profile.consent_given`, it immediately raises `HTTPException(status_code=400, detail="Consent is required before submitting or updating profile data. Please grant consent first.")`.
2. **Consent State Management**:
   - `POST /api/profile/consent` accepts `{ consent_given: bool }` via `ConsentUpdate` in [schemas.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/schemas.py).
   - It updates `profile.consent_given` and records `profile.consent_date = datetime.utcnow()`.

### B. Resume Extraction Flow (PDF & DOCX)
1. **Upload & Format Dispatch**:
   - `upload_resume(file, current_user, db)` in [profile.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/profile.py) verifies file extension (`.pdf`, `.docx`, `.doc`).
   - If corrupt, malformed, or empty, [profile_parser.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/profile_parser.py) raises a clean `ValueError`, which the router translates into an HTTP 400 with actionable feedback (preventing 500 errors).
2. **PyMuPDF PDF Parsing**:
   - `extract_text_and_links_from_pdf(file_bytes)` in [profile_parser.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/profile_parser.py) loads the document into `fitz.open(stream=file_bytes, filetype="pdf")`.
   - `page_count` is determined by `len(doc)`.
   - Embedded hyperlinks are parsed from `page.get_links()`, supplemented by regex detection of plain-text URLs.
3. **python-docx Parsing**:
   - `extract_text_and_links_from_docx(file_bytes)` parses paragraph text, table text, and XML relationship targets (`part.rels`).
4. **Section & Skill Extraction**:
   - `identify_sections(text)` segments the text into sections (`education`, `experience`, `projects`, `skills`, `achievements`, `summary`) by matching canonical header keywords.
   - `extract_skills_from_text(text)` extracts recognized languages, frameworks, and cloud tools against `COMMON_SKILLS`.
   - `extract_projects_from_text(text, links)` identifies individual projects, correlating them with GitHub and live URLs.
5. **Disk Persistence**:
   - Saves file bytes to `backend/data/uploads/<user_id>_<timestamp>_<filename>`.
   - Records file metadata in SQLite via the `UploadedFile` model in [models.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/models.py).

### C. LinkedIn & Chat Intake Flow
1. **LinkedIn Parsing**:
   - `parse_linkedin_text(text)` extracts headline, about summary, experience blocks, and skills.
   - `parse_linkedin_pdf(file_bytes)` parses LinkedIn official PDF exports.
2. **Chat Intake Extraction**:
   - `extract_profile_data_from_chat_text(message)` in [profile_parser.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/profile_parser.py) identifies GitHub usernames/URLs, LeetCode handles, and project links from chat prompts.
   - [ChatShell.jsx](file:///Users/nakulmirai/Mirai%20Project/frontend/src/components/ChatShell.jsx) hooks into this to sync handles shared during conversation.

### D. "My Data" Transparency & Deletion Flow
1. **Data Inspection**:
   - `GET /api/profile/me` returns the full `ProfileResponse` in [schemas.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/schemas.py), including parsed resume sections, skills, and tracked files.
2. **Profile Data Reset**:
   - `DELETE /api/profile/data` finds all `UploadedFile` records for the user and physically unlinks each file from `backend/data/uploads/` via `os.remove`. It also clears all parsed resume data, LinkedIn data, projects, achievements, and skills from the database.
3. **Permanent Account Deletion**:
   - `DELETE /api/profile/account` physically deletes all uploaded files for the user from disk and executes `db.delete(current_user)`, cascading to the `Profile`, `UploadedFile`, and associated rows.

---

## 3. Key Design Decisions and Rejected Alternatives

1. **Local Deterministic Parsing (`PyMuPDF` + `python-docx`) vs. LLM-only Text Extraction**:
   - *Decision*: Computed page counts, hyperlinks, and section boundaries deterministically using pure Python code.
   - *Reason*: Meets Rule 2 ("Compute whatever can be computed in code... and use the LLM only for subjective checks"). It is instant, requires zero tokens, works completely offline, and returns identical results across repeated runs.
   - *Rejected*: Sending raw binary PDF bytes or full resumes directly to an LLM for initial extraction is slow, nondeterministic, and fails offline without an API key.
2. **Single Consent Gate Dependency vs. Ad-Hoc Frontend Disabling**:
   - *Decision*: Enforced consent validation at the backend router layer on every intake endpoint (`PUT /api/profile/me`, `POST /api/profile/resume`, `POST /api/profile/linkedin/*`).
   - *Reason*: Guarantees that no data can be submitted via direct API/curl calls without explicit consent.
   - *Rejected*: Relying solely on disabled frontend checkboxes, which can be bypassed via curl or DevTools.
3. **Physical File Unlinking on Disk vs. Soft-Delete DB Flag**:
   - *Decision*: Physically removed files from `backend/data/uploads/` using `os.remove` when deleting profile data or accounts.
   - *Reason*: Complies with Rule 4 ("the student can view, edit and delete all their data") and prompt requirement ("confirm the DB rows are gone AND the uploaded files are removed from disk").
   - *Rejected*: Soft-deletes leave orphaned binary resumes on disk indefinitely.

---

## 4. Shortcuts, Placeholders, or Faked Parts
- **None**: All resume parsing (PDF/DOCX), LinkedIn extraction, chat parsing, database persistence, physical disk file unlinking, and tenant isolation are fully implemented and verified against real files on disk.

---

## 5. Verify It Yourself

### Step 1: Run the Backend & Unit Tests
```bash
make test
```
**Expected Output**: `31 passed in ~1.2s` with zero errors.

### Step 2: Test Consent Rejection via curl
```bash
# Register a student
curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_student@mirai.dev","password":"password123","role":"student"}'

# Login to get access token
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"demo_student@mirai.dev","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Attempt to submit GitHub handle without consent (Must return 400)
curl -s -X PUT http://127.0.0.1:8000/api/profile/me \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"github_username":"octocat"}'
```
**Expected Output**: `{"detail":"Consent is required before submitting or updating profile data. Please grant consent first."}`

### Step 3: Grant Consent and Upload Clean Resume
```bash
# Grant consent
curl -s -X POST http://127.0.0.1:8000/api/profile/consent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"consent_given": true}'

# Upload clean 1-page resume
curl -s -X POST http://127.0.0.1:8000/api/profile/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/tests/fixtures/clean_1page_resume.pdf"
```
**Expected Output**: Returns JSON with `"page_count": 1`, detected skills (`Python`, `FastAPI`, `React`, `Docker`, `SQL`), extracted projects, and tracked uploaded file.

### Step 4: Verify Disk File Deletion
```bash
# List upload folder (file exists)
ls backend/data/uploads

# Delete profile data
curl -s -X DELETE http://127.0.0.1:8000/api/profile/data \
  -H "Authorization: Bearer $TOKEN"

# List upload folder (file removed from disk)
ls backend/data/uploads
```
**Expected Output**: Before deletion, the file `<user_id>_<timestamp>_clean_1page_resume.pdf` exists. After deletion, the file is removed from disk and database rows are reset.
