# Module 05: GitHub Codebase Review & Playwright Live Link Checker

## 1. What the Module Does

Module 05 implements an automated placement readiness evaluation of a student's public GitHub developer presence, codebase craftsmanship, security posture, and production live deployment stability:
1. **GitHub Profile & Momentum Verification**: Evaluates the candidate's developer identity on GitHub, checking for a profile README (`<username>/<username>`), pinned showcase repositories, and recent public commit events (last 90 days).
2. **Repository & Codebase Quality Analysis**: Deterministically audits target repositories for comprehensive README documentation (with concrete local setup instructions and visual screenshots), clean directory structures with `.gitignore`, conventional imperative commit messages, automated test suites (e.g. pytest, Jest), and an LLM-powered review of primary entry files at `temperature=0` for readability, modularity, and potential bugs.
3. **Deterministic Multi-Pattern Secret Scanner**: Scans all repository source files for committed AWS access keys, private keys, GitHub PATs, Slack tokens, OpenAI API keys, and database connection strings, with built-in exclusion rules preventing false positives on documentation placeholders.
4. **Headless Playwright Live Link Checker**: Launches headless Chromium to load the candidate's live application URL within a strict 15-second timeout, monitoring for fatal HTTP status codes, network drops, and runtime JavaScript `console.error` logs, checking mobile viewport responsiveness (`375x667`), and capturing full desktop and mobile screenshots for student and evaluator inspection.

---

## 2. How It Works: Step-by-Step Flow

```
[Student in UI / API Client]
       │
       ▼
POST /api/reviews/github (backend/app/routers/github_review.py)
       │
       ├─► 1. Consent Gate Check (Rule 4: profile.consent_given == True)
       │
       ├─► 2. Input Resolution: Request params > Stored profile GitHub URL & Projects
       │
       ▼
evaluate_github_and_live() (backend/app/services/github_reviewer.py)
       │
       ├─► GitHubScanner (backend/app/services/github_scanner.py)
       │     ├─► GET /users/{username} (profile info)
       │     ├─► GET /repos/{username}/{username}/readme (Profile README check)
       │     ├─► GET /users/{username}/events/public (Commit momentum last 90d)
       │     ├─► GET /repos/{owner}/{repo} & /readme (Repo metadata & Setup/Visuals)
       │     ├─► GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1 (Folder structure & tests)
       │     └─► GET /repos/{owner}/{repo}/commits (Commit message quality)
       │
       ├─► scan_repository_files() (backend/app/services/secret_scanner.py)
       │     └─► Regex match against AWS keys, private keys, PATs, tokens, database URIs
       │
       ├─► perform_llm_code_review() (backend/app/services/github_reviewer.py)
       │     └─► LLM Adapter at temperature=0 with CodeReviewLLMSchema
       │
       ├─► check_live_link() (backend/app/services/live_link_checker.py)
       │     ├─► Headless Playwright Chromium (max 15s timeout)
       │     ├─► Desktop Viewport (1280x720) -> console error tracker & screenshot
       │     ├─► Mobile Viewport (375x667) -> overflow inspection & screenshot
       │     └─► Visible text extraction & content keyword overlap ratio
       │
       ▼
Compute 0–100 Weighted Score & Tier Badge
       │
       ▼
Persist in SQLite DB (models.ReviewResult, review_type="github")
       │
       ▼
Return JSON Response to Frontend (GitHubReviewResponse)
       │
       ▼
React UI (frontend/src/pages/GitHubReviewTab.jsx)
       ├─► Score Gauge (0–100) & Placement Tier Badge
       ├─► Critical Leaked Secrets Warning Banner (if detected)
       ├─► Playwright Live Preview Card (Desktop vs. Mobile switch)
       ├─► Filterable Benchmark Checks List (All, Needs Fix, Passed)
       └─► Specific, non-generic actionable fixes
```

### Exact Files and Functions

| Component | File Path | Key Functions / Classes |
| :--- | :--- | :--- |
| **API Router** | [backend/app/routers/github_review.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/routers/github_review.py) | `trigger_github_review`, `get_latest_github_review`, `trigger_live_link_check`, `get_screenshot` |
| **Review Orchestrator** | [backend/app/services/github_reviewer.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/github_reviewer.py) | `evaluate_github_and_live`, `perform_llm_code_review`, `WEIGHTS` |
| **GitHub REST Client** | [backend/app/services/github_scanner.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/github_scanner.py) | `GitHubScanner`, `check_response_rate_limit`, `parse_github_repo_url`, `GitHubRateLimitError`, `GitHubNotFoundError` |
| **Secret Scanner** | [backend/app/services/secret_scanner.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/secret_scanner.py) | `scan_repository_files`, `scan_file_content`, `SECRET_PATTERNS`, `mask_secret` |
| **Live Link Checker** | [backend/app/services/live_link_checker.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/services/live_link_checker.py) | `check_live_link`, `SCREENSHOT_DIR` |
| **Pydantic Schemas** | [backend/app/schemas.py](file:///Users/nakulmirai/Mirai%20Project/backend/app/schemas.py) | `GitHubReviewRequest`, `GitHubReviewResponse`, `LiveLinkCheckRequest`, `ReviewCheck` |
| **Frontend UI** | [frontend/src/pages/GitHubReviewTab.jsx](file:///Users/nakulmirai/Mirai%20Project/frontend/src/pages/GitHubReviewTab.jsx) | `GitHubReviewTab`, `handleRunReview`, `getScoreBadge` |
| **Frontend Parent** | [frontend/src/pages/ResumeReviewPage.jsx](file:///Users/nakulmirai/Mirai%20Project/frontend/src/pages/ResumeReviewPage.jsx) | `subtab-github`, tab switching logic |
| **API Client** | [frontend/src/api.js](file:///Users/nakulmirai/Mirai%20Project/frontend/src/api.js) | `api.triggerGitHubReview`, `api.getLatestGitHubReview`, `api.checkLiveLink`, `api.getScreenshotUrl` |

---

## 3. Key Design Decisions & Alternatives Rejected

1. **Deterministic-First Checks vs. Pure LLM Code Review**:
   - *Decision*: Compute repository tree statistics, test presence, `.gitignore`, commit message lengths, and regex secrets scanning deterministically in Python. Use the LLM only for subjective evaluation of primary entry files.
   - *Alternative Rejected*: Asking an LLM to evaluate the whole repository. LLMs hallucinate file counts, leak secrets in context windows, are non-deterministic, and hit context limits on larger codebases.
2. **Playwright Headless Browser vs. Simple HTTP Requests (e.g. `requests.get`)**:
   - *Decision*: Use headless Playwright Chromium. Modern student applications are client-side Single Page Applications (React, Vue, Next.js) that require JavaScript execution to render. Playwright captures real runtime console errors, evaluates mobile viewports, and captures desktop/mobile screenshots.
   - *Alternative Rejected*: Plain HTTP `requests.get()`. Cannot evaluate client-side crashes, blank screen hydration failures, or capture screenshots.
3. **Dual-Viewport Screenshot Generation**:
   - *Decision*: Playwright evaluates both desktop (`1280x720`) and mobile (`375x667`) viewports, checking for horizontal scroll overflow (`scrollWidth > innerWidth`).
   - *Alternative Rejected*: Single viewport desktop capture. Over 60% of modern recruiters and reviewers test candidate demos on mobile devices.
4. **Graceful Rate Limiting & Optional GitHub Token**:
   - *Decision*: Support an optional `GITHUB_TOKEN` from Settings or environment to raise rate limits from 60 to 5,000 req/hr. If unauthenticated rate limits are hit, intercept HTTP 403/429 and present helpful instructions rather than crashing with an unhandled 500 error.

---

## 4. Shortcuts, Placeholders & Faked Parts

1. **Sampling Large Repositories**:
   - For repositories with thousands of files, `GitHubScanner` inspects the recursive git tree metadata up to GitHub's REST limit (100k tree items) and samples up to 15 key source code files for deep secret scanning and LLM review to remain within rate and token limits.
2. **Pinned Repositories Heuristic**:
   - When querying unauthenticated GitHub REST API, the user's top starred and most recently updated repositories with descriptions and defined topics are evaluated to assess curation.
3. **No Logged-In Pages Scraped**:
   - Strictly conforms to Rule 4: only public profile data and public repositories are evaluated; no private student credentials are ever requested.

---

## 5. "Verify It Yourself" Steps

### Step 1: Run the Backend Test Suite
```bash
make test
```
**Expected Result**: All 52 tests pass cleanly across all modules (including 10 dedicated GitHub & Live Link review tests in `backend/tests/test_github_review.py`).

### Step 2: Test Playwright Live Link Verification with curl
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_student_mod05@msot.edu","password":"Password123!"}' | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/reviews/live-link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","project_title":"Example Domain"}' | jq '{loaded: .loaded, load_time_ms: .load_time_ms, desktop_screenshot: .desktop_screenshot}'
```
**Expected Result**:
`loaded` is `true`, `load_time_ms` is positive integer, and `desktop_screenshot` contains a filename (e.g., `"..._desktop.png"`).

### Step 3: Run Full Benchmark Review on Real GitHub Profile
```bash
curl -s -X POST http://127.0.0.1:8000/api/reviews/github \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"pallets","repo_url":"pallets/flask","live_url":"https://flask.palletsprojects.com"}' | jq '{score: .score, summary: .summary, checks_count: (.checks | length)}'
```
**Expected Result**:
Returns Score `85`, 13 benchmark checks, and a Tier 2 Interview Ready verdict.

### Step 4: Verify in the Browser
1. Open `http://127.0.0.1:5173` in your browser.
2. Log in as `curl_student_mod05@msot.edu` with password `Password123!`.
3. In the sidebar, click **Benchmark Reviews**, then click the **GitHub & Live** subtab.
4. Observe the score gauge (85/100), Tier 2 badge, Playwright preview screenshots (toggle between Desktop and Mobile), and filter pills (**Needs Fix** vs. **All Checks**).

---

## Changes

### 2026-10-16: Module 06 Readiness Score Trigger Integration
- Integrated `compute_and_save_readiness_score` into `POST /api/reviews/github` in `backend/app/routers/github_review.py`.
- Whenever a student runs or re-runs a GitHub & live link review, the overall placement readiness score automatically recalculates and records a timestamped snapshot in `models.ReadinessScoreSnapshot`.
