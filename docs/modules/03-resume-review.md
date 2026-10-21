# Module 03: Resume Review (Benchmark Rubric)

## 1. What the Module Does
Module 03 implements the **Placement Readiness Benchmark Resume Reviewer** for MSOT students:
- **Canonical 8-Point Rubric**: Evaluates resumes strictly against the placement benchmark specified in [docs/benchmarks.md](../benchmarks.md).
  1. Exactly one page format (`CHK-PAGE-COUNT`, 15 pts)
  2. Clean visual layout, typography, margin alignment, and uniform dates (`CHK-VISUAL-LAYOUT`, 10 pts)
  3. Zero spelling or grammar mistakes (`CHK-SPELL-GRAMMAR`, 10 pts)
  4. Every project has clear description, declared tech stack, quantifiable impact, live URL, and GitHub repo URL (`CHK-PROJECT-DETAILS`, 15 pts)
  5. LeetCode and GitHub profile links present (`CHK-PROFILE-LINKS`, 10 pts)
  6. Co-curricular achievements included (`CHK-ACHIEVEMENTS`, 10 pts)
  7. Bullet points start with active verbs and show measurable results (`CHK-ACTION-RESULTS`, 15 pts)
  8. ATS-friendly formatting: readable text stream, standard section headings, and zero text trapped in raster images (`CHK-ATS-FRIENDLY`, 15 pts)
- **Deterministic-First Computation**: Evaluates deterministic checks in code using PyMuPDF and regex. Uses the LLM at temperature 0 with structured schemas only for subjective checks, guaranteeing score variance <= 3 points across repeated runs.
- **Specific Actionable Fixes**: Every failed check produces an exact, non-generic fix (e.g., *"Correct the spelling of 'managment' to 'management' in your resume"*, *"Add your LeetCode profile URL (https://leetcode.com/u/yourhandle) to your contact header"*), strictly forbidding vague phrases like *"improve your resume"*.
- **Visual Layout Inspection**: Renders page 1 of PDF resumes to a 150 DPI PNG preview image for side-by-side visual layout inspection and vision analysis.
- **Full Review Page in UI**: Interactive dashboard with circular readiness score gauge, tier status pill, filterable checklist criteria, observed evidence, actionable fixes, and document preview panel.

---

## 2. How It Works (Flow with Exact Files and Functions)

### A. Review Trigger Flow
1. **Student Request**:
   - The student visits the **Resume Reviews** tab (`ResumeReviewPage.jsx`) or clicks **Re-run Review** / **Upload New Resume**.
   - Frontend calls `api.triggerResumeReview(file)` in [api.js](../../frontend/src/api.js).
2. **Consent & File Resolution**:
   - In [resume_review.py](../../backend/app/routers/resume_review.py), `trigger_resume_review` validates that `profile.consent_given == True`. If not, raises clean HTTP 400 Bad Request.
   - If a file is uploaded, reads the uploaded bytes; otherwise, reads the student's latest stored resume from `UploadedFile` on disk.

### B. Benchmark Evaluation Pipeline
In [resume_reviewer.py](../../backend/app/services/resume_reviewer.py), `review_resume` executes all 8 benchmark checks:
1. `evaluate_page_count(page_count, word_count)`:
   - Uses PyMuPDF `len(doc)` for PDF or estimated page count for DOCX.
   - Passes if `page_count == 1`.
2. `evaluate_ats_friendly(text, doc, sections)`:
   - Scans digital text stream length. If `len(text) < 50` while page contains raster images, flags image-only failure.
   - Checks presence of canonical ATS section headings (`Education`, `Experience`, `Projects`, `Skills`).
3. `evaluate_project_details(projects_text, links)`:
   - Extracts project blocks and checks for description, tech stack, impact metrics, live deployment link, and GitHub repository URL.
4. `evaluate_action_verbs_and_metrics(sections, raw_text)`:
   - Extracts accomplishment bullets (filtering out tech stack/metadata lines).
   - Verifies that >= 70% of bullets start with strong engineering action verbs (`STRONG_ACTION_VERBS`) and >= 50% include numerical metrics (`\d+(?:\.\d+)?%`, user counts, latency numbers).
5. `evaluate_profile_links(links, text)`:
   - Scans hyperlinks and header text for `github.com/<username>` and `leetcode.com/(u/)?<username>`.
6. `evaluate_visual_layout(doc, file_bytes)`:
   - Uses PyMuPDF text dictionary inspection (`page.get_text("dict")`).
   - Assesses unique font families (flagging if > 3 distinct fonts), margin variance across text blocks, vertical dead space / overlapping lines, and mixed date styles (seasons vs. standard months).
7. `evaluate_spelling_and_grammar(text, adapter)`:
   - Evaluates text against common technical resume typos (`COMMON_RESUME_TYPOS`) and structured LLM review at `temperature=0.0`.
8. `evaluate_co_curricular_achievements(sections, raw_text)`:
   - Verifies presence of distinct achievements section with hackathons, cloud certifications (AWS/CKA), or student leadership.

### C. Persistence & UI Presentation Flow
1. **Score Calculation**:
   - Sums points across all 8 checks (0 to 100), assigning tier classification (Tier 1: 90-100, Tier 2: 75-89, Tier 3: 60-74, Tier 4: < 60).
2. **Database Persistence**:
   - Saves record to SQLite `review_results` table via SQLAlchemy `ReviewResult` model.
3. **UI Rendering**:
   - [ResumeReviewPage.jsx](../../frontend/src/pages/ResumeReviewPage.jsx) renders score ring, summary, filter pills (`All`, `Needs Fix`, `Passed`), checklist cards with observed evidence and specific fixes, and visual document preview.

---

## 3. Key Design Decisions and Rejected Alternatives

1. **Deterministic-First Scoring vs. Pure LLM Prompt Evaluation**:
   - *Decision*: Page count, ATS headings, link presence, typography metrics, and typo dictionaries are computed deterministically in Python code.
   - *Reason*: Pure LLM prompts for resume scoring suffer from hallucinations, inconsistent scoring (scoring 85 on run 1 and 70 on run 2), and token costs. Deterministic code guarantees score variance = 0 across repeated runs and runs completely offline.
   - *Rejected*: Asking the LLM to count pages or check URLs directly in free-form text.
2. **Local Heuristic Layout Fallback vs. Vision-Only Dependency**:
   - *Decision*: Implemented PyMuPDF block dictionary inspection (font families, bbox margins, spacing, dates) as the layout validator, with rendering to PNG for vision models.
   - *Reason*: Allows the app to run fully locally with small models like `smollm:135m` or offline without paid multimodal APIs while maintaining strict layout inspection.
   - *Rejected*: Failing or skipping layout analysis when no vision model is available.
3. **Planted-Flaw Test Fixtures vs. Random Test Resumes**:
   - *Decision*: Created 4 deterministic test resumes with exact planted flaws (`resume_good.pdf`, `resume_2page.pdf`, `resume_missing_links_typos.pdf`, `resume_image_only.pdf`).
   - *Reason*: Enables automated regression tests asserting each planted flaw is caught and good resumes score strictly higher.
   - *Rejected*: Using arbitrary real resumes without known flaw baselines.

---

## 4. Shortcuts, Placeholders, or Faked Parts
- **None**: All 8 checks, scoring mathematics, database storage, preview image rendering (PyMuPDF), and frontend checklist dashboard are fully functional and verified with real files.

---

## 5. Verify It Yourself

### Step 1: Run the Backend & Resume Review Unit Tests
```bash
make test
```
**Expected Output**: `36 passed in ~1.5s` with 0 failures.

### Step 2: Run the Consistency Test
```bash
backend/venv/bin/pytest -v -s backend/tests/test_resume_review.py -k test_consistency_five_runs
```
**Expected Output**:
```
[CONSISTENCY TEST] 5 Consecutive Review Scores: [100, 100, 100, 100, 100]
[CONSISTENCY TEST] Max Score: 100, Min Score: 100, Diff: 0
PASSED
```

### Step 3: Test Review Endpoints via curl
```bash
# Register student & login
curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_student@mirai.dev","password":"password123","role":"student"}'

TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_student@mirai.dev","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

# Grant consent
curl -s -X POST http://127.0.0.1:8000/api/profile/consent \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"consent_given": true}'

# Upload good resume
curl -s -X POST http://127.0.0.1:8000/api/profile/resume \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@backend/tests/fixtures/resume_good.pdf"

# Trigger review
curl -s -X POST http://127.0.0.1:8000/api/reviews/resume \
  -H "Authorization: Bearer $TOKEN"
```
**Expected Output**: JSON response with `"score": 100`, `"review_type": "resume"`, 8 checks with `"pass": true`, factual evidence, and specific fixes.

### Step 4: Verify in the Browser
1. Start the app: `make dev` (or access running servers at http://localhost:5173).
2. Log in with `student_ui_demo@mirai.dev` / `password123`.
3. Click **Benchmark Reviews** in the left sidebar navigation.
4. Confirm overall score displays `100/100`, Tier `Placement Ready (Tier 1)`, 8 criteria passed.
5. Click **Show Visual Layout Preview** to see the 150 DPI rendered document preview.
6. Click **Upload New Resume** and choose `backend/tests/fixtures/resume_missing_links_typos.pdf`.
7. Observe immediate score update to `65/100` (`Needs Revision (Tier 3)`) with 4 `FIX REQUIRED` badges displaying exact evidence (typos, missing LeetCode, weak verbs) and specific actionable fixes.

---

## Changes

### 2026-10-16: Module 06 Readiness Score Trigger Integration
- Integrated `compute_and_save_readiness_score` into `POST /api/reviews/resume` in `backend/app/routers/resume_review.py`.
- Whenever a student uploads or re-runs a resume review, the overall placement readiness score automatically recalculates and records a timestamped snapshot in `models.ReadinessScoreSnapshot`.
