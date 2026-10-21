# Module 16 — Ollama Queue Resilience, Fail-Fast Preflight & Stateful Progress Tracking

## What the Module Does

Module 16 resolves two core operational defects in the placement readiness pipeline:

1. **Ollama Provider Routing & Dispatch Resilience**:
   - **Diagnosis & Resolution of Past Disconnect**: Diagnosed why Resume Benchmark Review jobs previously never reached Ollama (the remote Ollama host IP had shifted from `10.134.74.156` to `10.134.74.41`, and the queue payload omitted explicit provider/model parameters, causing dispatchers to evaluate `adapter` as `None`).
   - **Environment Variable Transparency**: When `LLM_PROVIDER` is set in the runtime environment, the Settings API explicitly returns `env_forced: true` and `env_forced_provider`, and the Settings UI renders a prominent persistent alert banner informing the user that environment variable overrides take precedence over UI selections.
   - **Fail-Fast Preflight Connectivity**: Before any job is accepted into the background queue, `JobQueueService.create_job` executes a 1.5-second socket preflight check (`check_ollama_connectivity`) against the resolved Ollama base URL (`http://<OLLAMA_HOST>:11434/api/tags`). If unreachable or returning errors, the API rejects the request immediately with `HTTP 400 Bad Request`, preventing deadlocks or ghost jobs from occupying concurrency slots.
   - **Deterministic Review Execution with LLM Takeaway**: All 8 benchmark checks in `resume_reviewer.py` remain 100% deterministic code calculations (page count, ATS headings, contact links, action verbs, project metrics, GPA format, etc.). When Ollama is active, the single subjective placement executive summary takeaway is generated via remote Ollama (`qwen2.5:3b`). The response metadata explicitly records `reviewed_with: "ollama / qwen2.5:3b"` and `code_only_checks: [1, 2, 3, 4, 5, 6, 7, 8]`.

2. **Stateful Progress & Continuous Elapsed Timer Tracking**:
   - **Server-Side Timestamp Origin**: Fixed the timer reset defect where switching views restarted the progress timer from `0.0s`. The client calculates elapsed duration strictly as `(Date.now() - new Date(started_at || created_at).getTime()) / 1000`.
   - **Global Application-Level Job Context**: Implemented `JobContext.jsx` wrapped around the entire React component hierarchy, maintaining active job ID and state across client-side router navigation, tab switching, and browser page reloads (persisted in `sessionStorage` and `localStorage`).
   - **Global Sidebar Mini-Widget**: A compact running job widget sits in `Sidebar.jsx`, displaying live running elapsed time, provider/model badges, and one-click navigation back to the active review.
   - **Clean Polling Cleanup**: Terminal job states (`done`, `failed`, `cancelled`) automatically terminate polling intervals and release UI state.

---

## How It Works

### Execution Flow: From Job Trigger to Result

```
[Student in UI]
       │
       ▼ Click "Run Benchmark Review" / Upload PDF
[Frontend: ResumeReviewPage.jsx]
       │ calls api.triggerResumeReviewAsync()
       ▼
[Backend: POST /api/reviews/resume/async]
       │
       ├──► [settings_service.py: load_raw_settings()]
       │         Reads effective provider ('ollama') and model ('qwen2.5:3b')
       │         Checks env override LLM_PROVIDER
       │
       ├──► [job_queue.py: create_job()]
       │         Executes check_ollama_connectivity(base_url, timeout=1.5s)
       │         If unreachable: raises ValueError -> HTTP 400 Bad Request (fail fast)
       │         If healthy: writes BackgroundJob (status="queued", provider="ollama", model="qwen2.5:3b")
       │
       ├──► [job_queue.py: enqueue_and_dispatch()]
       │         Submits job to ThreadPoolExecutor
       │         Worker thread acquires threading.Semaphore(1) for Ollama
       │
       ▼ [Background Worker Thread: run_resume_review()]
       │         1. Executes 8 deterministic code rubric checks in resume_reviewer.py
       │         2. Initializes OllamaAdapter(base_url="http://10.134.74.41:11434", model="qwen2.5:3b")
       │         3. Calls generate_structured_output() for 1-sentence placement takeaway
       │         4. Logs token counts and inference timing to timing_logger.py
       │         5. Attaches reviewed_with: "ollama / qwen2.5:3b" and code_only_checks: [1..8]
       │         6. Commits ReviewResult and marks BackgroundJob status="done"
       │         7. Finally releases Ollama concurrency slot
       ▼
[Frontend: JobProgressIndicator.jsx & Sidebar.jsx]
       │ Continuous polling /api/jobs/status/{id}
       │ Computes elapsed time from started_at / created_at (no reset on tab switch)
       ▼
[Student Views Result in UI]
       Displays score gauge, 8 benchmark checks, LLM summary note, and
       "Reviewed with: ollama / qwen2.5:3b | 8 benchmark checks evaluated in code (deterministic)"
```

### Key Files & Functions

| File Path | Function / Component | Purpose |
| :--- | :--- | :--- |
| `backend/app/services/settings_service.py` | `check_ollama_connectivity()`, `get_public_settings()` | Validates network connectivity to Ollama `/api/tags` in $\le 1.5$s; exposes `env_forced` status. |
| `backend/app/services/job_queue.py` | `create_job()`, `_worker_thread()`, `cleanup_stale_jobs_on_startup()` | Preflight validation, re-entrant lock synchronization (`threading.RLock`), safe model retention, and process boot time scoping. |
| `backend/app/services/job_dispatchers.py` | `run_resume_review()` | Dispatches the 8 code checks, initializes remote Ollama adapter, queries takeaway LLM note, logs timing, and packages `reviewed_with` metadata. |
| `backend/app/routers/resume_review.py` | `trigger_resume_review_async()`, `get_latest_resume_review()` | REST endpoints accepting async reviews and returning review results with engine metadata. |
| `frontend/src/context/JobContext.jsx` | `JobProvider`, `useJobContext()` | App-wide React context storing active job ID, status polling, and elapsed timer. |
| `frontend/src/components/Sidebar.jsx` | `Sidebar()` | Global running job mini-widget rendering elapsed time and status across all tabs. |
| `frontend/src/components/JobProgressIndicator.jsx` | `JobProgressIndicator()` | Section-level job progress tracker computing elapsed time strictly from server timestamps. |
| `frontend/src/pages/ResumeReviewPage.jsx` | `ResumeReviewPage()` | Handles resume file intake, review triggering, metadata banner rendering, and scorecard display. |
| `frontend/src/pages/SettingsPage.jsx` | `SettingsPage()` | Renders environment variable override warning banner when `envForced` is active. |

---

## Design Decisions & Rejected Alternatives

1. **Preflight Socket Check vs. Queued Inference Failure**:
   - *Chosen*: Perform an instant 1.5-second preflight check (`check_ollama_connectivity`) inside `create_job()` before a job is persisted.
   - *Rejected Alternative*: Accepting the job into SQLite and waiting for a background worker thread to fail minutes later during inference. Preflight gives students instant actionable feedback ("Remote Ollama host unreachable") and prevents phantom jobs from polluting queue telemetry.

2. **Server-Side Timestamps vs. Local State Timers**:
   - *Chosen*: Calculate elapsed seconds as `Math.max(0, (Date.now() - new Date(started_at || created_at).getTime()) / 1000)`.
   - *Rejected Alternative*: Initializing `const [elapsed, setElapsed] = useState(0)` and running `setInterval(() => setElapsed(e => e + 1))`. Local timers reset to 0 whenever React unmounts and remounts components during tab navigation.

3. **Re-entrant Lock (`threading.RLock`) vs. Plain Lock (`threading.Lock`)**:
   - *Chosen*: Use `threading.RLock()` for `JobQueueService` and `JobExecutionHandle`.
   - *Rejected Alternative*: `threading.Lock()`. When `_ensure_semaphore` entered `with self._lock:` and called `self.get_provider_limit()`, it acquired `self._lock` a second time on the same thread, causing an immediate deadlock. `RLock` allows safe recursive acquisition within the same thread.

4. **Lazy Adapter Imports vs. Top-Level Imports**:
   - *Chosen*: Import `get_current_job_handle` inside adapter execution methods (`generate`, `generate_stream`).
   - *Rejected Alternative*: Top-level `from app.services.job_queue import get_current_job_handle` in `ollama_adapter.py`, which caused a fatal circular import when `job_queue.py` imported `from app.llm.base import JobCancelledError`.

---

## Shortcuts or Faked Parts

- **Zero Mocking in Production Paths**: Remote Ollama connectivity is real (`http://10.134.74.41:11434` with model `qwen2.5:3b`).
- **Timing Log Persistence**: Every remote Ollama inference generates a real timing log entry in `llm_timing_logs` (verified duration ~10.66s, 135 prompt tokens, 37 output tokens).
- **Unit Test Isolation**: In automated tests (`make test`), mock adapters are used for speed and offline predictability. Live remote tests are isolated under `make test-live`.

---

## Verify It Yourself

Follow these 4 manual steps to verify everything yourself:

### Step 1: Verify Settings & Active Remote Host
```bash
curl -s http://localhost:8000/api/settings | python3 -m json.tool
```
*Expected Output*:
```json
{
    "provider": "ollama",
    "model": "qwen2.5:3b",
    "ollama_base_url": "http://10.134.74.41:11434",
    "env_forced": false,
    "env_forced_provider": null
}
```

### Step 2: Test Fail-Fast on Unreachable Ollama Host
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
from app.services.settings_service import check_ollama_connectivity
ok, err = check_ollama_connectivity('http://192.0.2.1:11434', timeout=1.5)
print('Reachable:', ok)
print('Error:', err)
"
```
*Expected Output*:
`Reachable: False`
`Error: Remote Ollama host at 'http://192.0.2.1:11434' is unreachable (ConnectTimeout)...`

### Step 3: Run Full Fast Offline Backend Test Suite
```bash
make test
```
*Expected Output*:
`136 passed, 5 deselected, 7 warnings in ~177s` (Zero failures, zero regressions).

### Step 4: Run End-to-End Headless Playwright Verification
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
from playwright.sync_api import sync_playwright
import time
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    page = b.new_page()
    page.goto('http://localhost:5173')
    print('Frontend Title:', page.title())
    b.close()
"
```
*Expected Output*:
`Frontend Title: Placement Readiness Copilot`
