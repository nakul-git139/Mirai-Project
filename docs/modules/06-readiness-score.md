# Module 06: Placement Readiness Score & Progression Analytics

## 1. What the Module Does

Module 06 synthesizes student performance across all 7 placement dimensions into a single benchmark-driven index out of 100 points:
1. **Weighted Composite Index (0–100)**: Evaluates student readiness using fixed institutional weights: Resume (25), Projects (25), Mock Interview (20), GitHub (10), Coding Practice (10), LinkedIn (5), and Co-curricular Achievements (5).
2. **Placement Tier Classification**: Maps scores deterministically into three readiness tiers:
   - `0–49`: **Not ready** (amber/rose)
   - `50–74`: **Almost ready** (amber/gold)
   - `75–100`: **Placement ready** (emerald green)
3. **Missing Component Transparency**: Explicitly tracks uncompleted dimensions (e.g., mock interview not taken, GitHub review pending). Missing components contribute 0 earned points, are flagged with `status: "missing"`, and never trigger `NaN` or application crashes.
4. **Top 5 High-Impact Action Items**: Ranks the top 5 concrete fixes by overall point gain ($\Delta \text{Overall}$), with specific evidence, targeted instructions, and direct navigation links.
5. **Interactive Score Progression History**: Automatically captures a timestamped snapshot whenever a student completes or re-runs any benchmark review, updating an interactive SVG progression chart with threshold lines at 50 and 75 points.

---

## 2. How It Works: Step-by-Step Flow

```
[Student in React UI / Client]
       │
       ├─► GET  /api/readiness/current    (backend/app/routers/readiness.py)
       ├─► POST /api/readiness/recalculate
       └─► GET  /api/readiness/history
              │
              ├─► 1. Consent Gate Check (Rule 4: profile.consent_given == True)
              │
              ▼
get_current_readiness_score() / compute_and_save_readiness_score()
(backend/app/services/readiness_service.py)
       │
       ├─► Query Student Profile & Reviews (models.Profile, models.ReviewResult, models.MockInterviewSession)
       │
       ├─► evaluate_resume_component() ──────────► Weight 25: Pulls latest resume review (0-100)
       ├─► evaluate_projects_component() ────────► Weight 25: Audits profile projects (GitHub, live links, writeups)
       ├─► evaluate_mock_interview_component() ──► Weight 20: Pulls latest completed mock interview
       ├─► evaluate_github_component() ──────────► Weight 10: Pulls latest GitHub review
       ├─► evaluate_coding_practice_component() ─► Weight 10: Audits LeetCode handle, streaks & problem targets
       ├─► evaluate_linkedin_component() ────────► Weight 5:  Pulls latest LinkedIn review
       ├─► evaluate_cocurricular_component() ────► Weight 5:  Audits hackathons, certifications & leadership
       │
       ▼
calculate_readiness_formula(component_results)
       │
       ├─► raw_score = sum(score_i * weight_i / 100 for scored components)
       ├─► overall_score = int(round(raw_score)) clamped [0, 100]
       ├─► level = "Not ready" (< 50) | "Almost ready" (50..74) | "Placement ready" (>= 75)
       │
       ▼
generate_top_actions(component_results)
       │
       ├─► Missing component actions: points_gained = component.weight
       ├─► Failed check actions: points_gained = check.points * component.weight / 100
       ├─► Sort descending by points_gained -> slice[:5]
       │
       ▼
Persist Snapshot (models.ReadinessScoreSnapshot)
       │
       ▼
Return JSON Response (schemas.ReadinessResponse)
       │
       ▼
React Dashboard (frontend/src/pages/ReadinessScorePage.jsx)
       ├─► Circular Score Gauge (0–100) with Tier Badge & points-to-target indicator
       ├─► Interactive SVG Trend Chart with 50 and 75 threshold guide lines
       ├─► Missing Components Callout Banner with direct "Start" action buttons
       ├─► Top 5 Action Items Cards with point gain pills and step-by-step guidance
       └─► 7 Component Breakdown Cards with status chips, weights, and detailed summaries
```

### Exact Files and Functions

1. **`backend/app/services/readiness_service.py`**:
   - `calculate_readiness_formula(component_results)`: Pure mathematical function calculating raw score, rounded integer score, and tier boundaries.
   - `evaluate_projects_component(profile)`: Deterministically checks for $\ge 2$ production projects, live links, and descriptive writeups.
   - `evaluate_coding_practice_component(profile)`: Audits LeetCode handle presence and problem-solving targets.
   - `evaluate_cocurricular_component(profile)`: Evaluates hackathon participations, certifications, and leadership roles.
   - `evaluate_resume_component(latest_review)`: Maps the latest completed resume review score and failed checks to points.
   - `evaluate_linkedin_component(latest_review)`: Maps the latest LinkedIn review.
   - `evaluate_github_component(latest_review)`: Maps the latest GitHub & live link review.
   - `evaluate_mock_interview_component(latest_session)`: Evaluates mock interview performance.
   - `generate_top_actions(component_results)`: Calculates point gains and returns the top 5 ranked actions.
   - `compute_and_save_readiness_score(db, user_id)`: Orchestrates all evaluators, saves a new snapshot to SQLite, and returns the response.
   - `get_current_readiness_score(db, user_id)`: Fetches latest snapshot or computes fresh score if none exists.
   - `get_readiness_history(db, user_id)`: Returns ordered snapshots for time-series chart rendering.

2. **`backend/app/models.py`**:
   - `ReadinessScoreSnapshot`: Stores `id`, `user_id`, `overall_score`, `level`, `breakdown` (JSON), and `created_at`.

3. **`backend/app/schemas.py`**:
   - `ComponentBreakdown`, `ActionItem`, `ReadinessResponse`, and `ReadinessHistoryItem`.

4. **`backend/app/routers/readiness.py`**:
   - `GET /api/readiness/current`: Returns current score and breakdown with consent verification.
   - `POST /api/readiness/recalculate`: Forces an immediate re-evaluation and creates a snapshot.
   - `GET /api/readiness/history`: Returns historical snapshots for trend visualization.

5. **Review Routers Integration**:
   - `backend/app/routers/resume_review.py`: Auto-invokes `compute_and_save_readiness_score` after successful resume review.
   - `backend/app/routers/linkedin_review.py`: Auto-invokes `compute_and_save_readiness_score` after successful LinkedIn review.
   - `backend/app/routers/github_review.py`: Auto-invokes `compute_and_save_readiness_score` after successful GitHub review.

6. **Frontend**:
   - `frontend/src/pages/ReadinessScorePage.jsx`: Main dashboard featuring animated SVG score gauge, polyline trend chart, missing component alerts, and action items.
   - `frontend/src/api.js`: Added `getReadinessScore()`, `recalculateReadinessScore()`, and `getReadinessHistory()`.
   - `frontend/src/App.jsx`: Registered route in student navigation.

---

## 3. Design Decisions & Rejected Alternatives

| Decision | Rationale | Alternatives Rejected |
| :--- | :--- | :--- |
| **Strict Linear Weights (Sum = 100)** | Provides completely transparent, predictable arithmetic where students can directly see how fixing a 10-point rubric item raises their overall score by exactly $\Delta \times \frac{\text{Weight}}{100}$. | **Dynamic Non-linear Scaling**: Considered curved percentile scaling, but rejected because students cannot calculate their own scores or trust the predictability of fixes. |
| **Zero Contribution for Missing Components** | Accurately reflects placement readiness—a student who has not taken a mock interview is not yet interview-ready. | **Normalized Rescaling (dividing by sum of completed weights)**: Rejected because a student with only a 100/100 resume would falsely appear 100% "Placement Ready" without having written code or practiced interviews. |
| **Snapshot History Model** | Every review run creates an immutable snapshot in `ReadinessScoreSnapshot`. This allows historical trend visualization without mutating past records. | **Single Current-Score Field in User Table**: Rejected because it loses the student's improvement trajectory over time. |
| **Lightweight Pure SVG Curve** | Custom SVG line/area chart with hover tooltips and milestone guides ensures zero external chart library overhead, lightning-fast Vite builds (<400ms), and full styling control. | **Heavy Charting Library (Chart.js / Recharts)**: Rejected to keep bundle sizes lean, dependencies minimal, and eliminate bundle version conflicts. |

---

## 4. Shortcuts & Faked Parts

- **Mock Interview Component**: Module 07 (Mock Interview) has not yet been built. In this module, the mock interview dimension correctly queries the database for completed interview sessions; when none are found, it behaves as designed by scoring `null`, contributing 0 points, and offering a high-priority `+20.0 pts` action item. No mock data is faked.
- **Projects & Co-curricular Evaluators**: Evaluated deterministically from the student's stored `Profile` record (projects list, LeetCode handle, and co-curricular achievements list).

---

## 5. Verify It Yourself

Follow these steps to manually verify the readiness score system:

### Step 1: Check Current Readiness Score via API
Run:
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@msot.edu","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -s http://127.0.0.1:8000/api/readiness/current \
  -H "Authorization: Bearer $TOKEN"
```
**Expected Result**:
- Returns HTTP 200 with JSON payload containing:
  - `overall_score`: 61
  - `level`: `"Almost ready"`
  - `breakdown`: 7 components with exact weights
  - `missing_components`: `["mock_interview", "github", "linkedin"]`
  - `top_actions`: 5 prioritized actions ranked in descending order (+20.0 pts, +10.0 pts, +5.0 pts, +1.0 pts, +0.5 pts)

### Step 2: Query Score Progression History
Run:
```bash
curl -s http://127.0.0.1:8000/api/readiness/history \
  -H "Authorization: Bearer $TOKEN"
```
**Expected Result**:
- Returns an array of historical snapshots showing the score progression from initial baseline (36) to post-resume upload (61).

### Step 3: View the Dashboard in the Browser
1. Open `http://localhost:5173/` in your browser.
2. Log in with `alex@msot.edu` / `password123`.
3. Click **Readiness Score** in the left navigation sidebar.
4. Verify:
   - The circular gauge displays **61 / 100** with the gold **Almost ready** badge.
   - The trend chart plots historical points with guide lines at 50 and 75.
   - The missing components banner alerts: *"3 Components Not Yet Scored: Complete these to unlock up to +35 pts"*.
   - The Top 5 actions list displays each item with a point gain tag (`+20.0 pts`, `+10.0 pts`, etc.).
   - All 7 component breakdown cards appear at the bottom.

### Step 4: Run the Complete Automated Test Suite
Run:
```bash
make test
```
**Expected Result**:
- All 67 tests pass cleanly (15 formula and readiness tests, 52 earlier module tests, 0 failures).

---

## [2026-10-18] Changes: Mock Interview Paused & Score Rescaling

### 1. Summary of Changes
- Integrated `ENABLE_MOCK_INTERVIEW` configuration flag (default: `False`).
- Updated `calculate_readiness_formula` in `backend/app/services/readiness_service.py` to handle the mock interview being paused or not taken.
- When `ENABLE_MOCK_INTERVIEW` is `False` or the interview is absent:
  - Rescales the remaining 6 criteria weights to 100 by dividing each component's base weight by 80 ($W_i / 80 \times 100$):
    - Resume: 31.25%
    - Projects: 31.25%
    - GitHub Presence: 12.50%
    - Coding Practice: 12.50%
    - LinkedIn Profile: 6.25%
    - Co-curricular: 6.25%
    - Mock Interview: 0.00% (excluded)
  - Surfaces notification note: *"Mock interview not included. Your score is based on the other 80% of the readiness criteria."*
  - Suppresses mock interview actions from the Top 5 actions recommendations when flag is off.
- When `ENABLE_MOCK_INTERVIEW` is `True` and interview is taken:
  - Retains original 20% weight and 100-point sum without the note.
