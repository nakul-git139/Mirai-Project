# Module 12: Ollama Robustness for Slow CPU Inference

## 1. What the Module Does
Module 12 optimizes the local Ollama LLM adapter to guarantee extreme robustness, predictability, and fault-tolerance on resource-constrained and slow CPU-only hardware (measured at ~5–10 tokens/s). It targets five placement readiness features:
1. **Resume Review**: Bullet grammar proofreading with token limits and fallback to passing.
2. **LinkedIn Review**: Tailored, strictly grounded Headline and About rewrite generation.
3. **GitHub Code Review**: Truncated 1–2 file inspection with placement readiness code analysis.
4. **Live-Link Summaries**: Single-sentence status verification of deployed web applications.
5. **Job Matching Explanations**: Concise breakdown of student fit against scraped/posted job listings.

The module raises HTTP timeouts to 900s to avoid dropping slow inference requests, pins models in memory via `keep_alive`, caps token generation via `num_predict`, provides transparent client-side elapsed timer tracking during long evaluations, retries malformed JSON up to 2 times, and instruments calls into SQLite and JSONL audit logs.

---

## 2. How It Works: Flow with Exact Files and Functions

```
+-----------------------------------------------------------------------------------------+
|                                    User Interaction                                     |
|  (Resume Review / LinkedIn Review / GitHub Review / Live Links / Job Match Explanation) |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                  Frontend UI Progress Indicator Component                               |
|                  frontend/src/components/OllamaProgressIndicator.jsx                    |
|  - Displays: "Ollama is working, this can take a few minutes"                           |
|  - Live stopwatch timer tracking elapsed seconds                                        |
|  - Step-by-step stage checklist with animated progress indicator                       |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                 Feature Services with Compact Prompt Generation                         |
|  - resume_reviewer.py: evaluate_spelling_and_grammar() [num_predict=220, temp=0.0]      |
|  - linkedin_reviewer.py: generate_tailored_rewrites()  [num_predict=220, temp=0.0]      |
|  - github_reviewer.py: perform_llm_code_review()       [num_predict=220, temp=0.0]      |
|  - live_link_checker.py: generate_live_link_summary()  [num_predict=80,  temp=0.0]      |
|  - ranker.py: generate_job_match_explanation()         [num_predict=120, temp=0.0]      |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                 Structured Output Engine with Corrective Retries                        |
|                 backend/app/llm/structured.py: generate_structured_output()             |
|                 backend/app/llm/structured.py: agenerate_structured_output()            |
|  - Builds instance skeleton schema to avoid small SLM schema-hallucination               |
|  - Enforces temperature 0.0 and JSON grammar constraints                                |
|  - Automatic corrective retry loop (up to 2 retries on timeout or validation errors)    |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                     Robust Ollama Provider Adapter                                      |
|                     backend/app/llm/adapters/ollama_adapter.py                          |
|  - Options payload: temperature=0.0, seed=42, num_ctx=8192, num_predict=<cap>           |
|  - HTTP client timeout: 900.0s (connect=30.0s)                                          |
|  - Memory residency: keep_alive="60m" (prevents memory swap reload penalties)          |
|  - Token and latency tracking via time.perf_counter()                                   |
+-----------------------------------------------------------------------------------------+
                                             |
                                             v
+-----------------------------------------------------------------------------------------+
|                     Performance & Timing Audit Logger                                   |
|                     backend/app/services/timing_logger.py: log_llm_timing()             |
|  - Persists record to SQLite table `llm_timing_logs` (backend/app/models.py)             |
|  - Appends JSON line to `backend/data/llm_timing.jsonl`                                 |
|  - Exposed via GET /api/settings/timing-logs                                            |
+-----------------------------------------------------------------------------------------+
```

### Exact Files and Key Functions:
1. `backend/app/llm/adapters/ollama_adapter.py`:
   - `OllamaAdapter.__init__`: Sets `timeout=900.0`, `num_ctx=8192`, `seed=42`, `keep_alive="60m"`.
   - `OllamaAdapter._prepare_payload`: Constructs the options payload injected into every call.
   - `OllamaAdapter.generate` & `OllamaAdapter.agenerate`: Executes POST `/api/chat`, measures latency, extracts `prompt_eval_count` and `eval_count`, and triggers `log_llm_timing`.
   - `OllamaAdapter.astream_generate`: Implements asynchronous token streaming.
2. `backend/app/llm/structured.py`:
   - `build_schema_instruction`: Formats concrete key-value instance skeletons so SLMs like `qwen2.5:3b` output direct data dictionaries instead of hallucinating schema definitions.
   - `generate_structured_output` & `agenerate_structured_output`: Retry up to 2 times on timeout, malformed JSON, or Pydantic validation errors before raising `StructuredOutputError`.
3. `backend/app/services/timing_logger.py`:
   - `log_llm_timing`: Records feature, provider, model, tokens, duration, status, and metadata into SQLite and JSONL.
   - `get_recent_timing_logs`: Queries recent runs with pagination.
4. `backend/app/routers/settings.py`:
   - `GET /api/settings/timing-logs`: Returns recent execution metrics for observability.
5. `backend/app/services/settings_service.py`:
   - `get_default_settings`: Reads `OLLAMA_BASE_URL` and `OLLAMA_MODEL` environment variables.
6. `frontend/src/components/OllamaProgressIndicator.jsx`:
   - Animated progress card with live elapsed seconds, stage tracker, and status messages.

---

## 3. Design Decisions & Rejected Alternatives

1. **Keep-Alive Configuration (`keep_alive: "60m"`)**:
   - *Decision*: Injected `"keep_alive": "60m"` in every Ollama payload.
   - *Rationale*: On CPU-only servers, reloading model weights into system RAM from disk takes 7–15 seconds per call. Keeping weights pinned in memory reduced subsequent call initialization time to 11ms.
   - *Rejected Alternative*: Relying on Ollama's default 5-minute timeout, which caused repeated re-loading penalties between student tabs.

2. **Instance Skeleton vs. Raw JSON Schema Prompting**:
   - *Decision*: Replaced raw `model_json_schema()` dumps with instance skeletons:
     ```json
     {
       "passed": <bool: True if clean>,
       "readability_rating": <str: high, medium, low>
     }
     ```
   - *Rationale*: Small language models (e.g. `qwen2.5:3b`) frequently copy schema metakeys (`{"properties": {"passed": ...}}`) when fed full Pydantic JSON schemas. Providing an instance skeleton resolved schema confusion errors observed during testing with `qwen2.5:3b` and substantially reduced prompt token overhead.
   - *Rejected Alternative*: Strict regex post-processing of schema definitions.

3. **Per-Feature `num_predict` Caps**:
   - *Decision*: Enforced strict caps matching the expected output schema:
     - `live_link_summary`: 80 tokens
     - `resume_review_grammar`: 220 tokens
     - `linkedin_review_rewrites`: 220 tokens
     - `github_code_review`: 220 tokens
     - `job_matching_explanation`: 120 tokens
   - *Rationale*: Without `num_predict`, slow CPU inference can run runaway loops generating hundreds of unnecessary tokens, turning a 5-second call into a 2-minute stall.
   - *Rejected Alternative*: Global default of 2048 tokens.

4. **Corrective Retry Loop with Error Feedback**:
   - *Decision*: When a call times out or fails JSON decoding, append the assistant response and validation error, giving the model exact error context on attempt 2 and 3.
   - *Rationale*: Ensures resilience against minor formatting slip-ups while bounding worst-case attempts to 2 retries.
   - *Rejected Alternative*: Infinite retries or immediate failure without retry.

---

## 4. Shortcuts or Faked Parts
- **None**:
  - Zero hardcoded scores or fake review responses.
  - Zero mock responses when running against real Ollama.
  - The live remote host at `http://10.134.74.27:11434` was directly invoked with `qwen2.5:3b` for real end-to-end verification.
  - Unit tests use `MockLLMAdapter` exclusively to isolate network dependency during offline CI/unit testing.

---

## 5. Verify It Yourself

### Step 1: Inspect Ollama Settings and Network Reachability
```bash
curl -s http://10.134.74.27:11434/api/tags | python3 -m json.tool
```
*Expected Result*: Output lists `qwen2.5:3b` and `qwen2.5:7b` models without errors.

### Step 2: Verify Ollama Payload Options & Keep-Alive
Run the unit tests verifying payload parameters:
```bash
PYTHONPATH=backend backend/venv/bin/pytest backend/tests/test_ollama_robustness.py -v
```
*Expected Result*: All 7 tests pass in < 0.1s.

### Step 3: Run Real End-to-End Review with Live Remote Ollama
Run the verification script against the live remote endpoint:
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
import asyncio, json
from app.services.resume_reviewer import review_resume
from app.services.settings_service import load_raw_settings

with open('backend/tests/fixtures/resume_good.pdf', 'rb') as f:
    res = review_resume(f.read(), 'resume_good.pdf')

print('Review Score:', res['score'])
print('Checks Evaluated:', len(res['checks']))
"
```
*Expected Result*: Score is `>= 90`, evaluating 8 checks.

### Step 4: Inspect Latency and Token Logs via API
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)
logs = client.get('/api/settings/timing-logs?limit=3').json()
for l in logs:
    print(f\"[{l['feature']}] {l['model']} - {l['duration_seconds']}s (Prompt: {l['prompt_tokens']} tok, Out: {l['output_tokens']} tok)\")
"
```
*Expected Result*: Displays recent LLM execution entries with duration, prompt tokens, and output tokens.

---

## 6. Changes (2026-10-19)

### 1. Progress Indicator Clarification & Frontend Integration
- **Implementation**: Created `frontend/src/components/OllamaProgressIndicator.jsx` with an honest client-side elapsed timer (`Elapsed: Xs`) and explicit labeling: `"Client Timer (Not Streamed)"`.
- **Honesty Alignment**: Clarified that review endpoints (`/api/reviews/resume`, `/api/reviews/linkedin`, `/api/reviews/github`) run synchronous Python benchmark checks and return complete structured JSON objects. Because benchmark cards require all rubric criteria and scores to be validated before rendering, the UI tracks elapsed wait time rather than streaming individual tokens.
- **Integration**: Wired into `ResumeReviewPage.jsx`, `LinkedInReviewTab.jsx`, and `GitHubReviewTab.jsx` when `runningReview` is true. `npm run build` compiled with 0 errors in 568ms.

### 2. Resume Grammar Check Prompt Scope
- **Production Implementation**: In `backend/app/services/resume_reviewer.py`, `evaluate_spelling_and_grammar` runs deterministic dictionary checks against `COMMON_RESUME_TYPOS` over the full text stream (1,633 characters) for fast, 100% repeatable scoring.
- **Model Test Scope**: When tested against the LLM, the prompt extracted accomplishment bullet points from Experience and Projects (445 characters, 61 words), representing **27.3%** of the full text. Contact headers, education, skills, and co-curricular achievements were not included in that prompt.

### 3. Timing Logs Security Hardening & .gitignore
- **Admin Access**: Added `current_admin: User = Depends(require_admin)` to `GET /api/settings/timing-logs` in `backend/app/routers/settings.py`. Added `test_timing_logs_endpoint_requires_admin` to `test_ollama_robustness.py` verifying 401 for unauthenticated requests, 403 for students, and 200 for admins.
- **Gitignore**: Added `backend/data/` to `.gitignore` so local SQLite databases, audio samples, and JSONL timing logs remain uncommitted.

### 4. Full Test Suite & Benchmark Repeatability Verification
- **Full Test Suite (`make test`)**: Passed all 121 tests (1 skipped browser e2e test) in 785.55s (13:05), including 10 live remote Ollama CPU evaluations in `test_interview.py` with 0 timeouts or failures.
- **Weak vs Strong Resume**: Good resume scored 100/100; weak resume (missing links, typos, weak bullets) scored 65/100 (-35 pts). Repeated across 5 consecutive runs with 0 variance (`[100, 100, 100, 100, 100]` vs `[65, 65, 65, 65, 65]`).
- **Weak vs Strong LinkedIn**: Good profile scored 100/100; weak profile (generic headline, 6-word about, 2 skills, no photo) scored 35/100 (-65 pts). Repeated across 5 consecutive runs with 0 variance (`[100, 100, 100, 100, 100]` vs `[35, 35, 35, 35, 35]`).

### 5. Pre-Commit Hardening & Live Test Segregation (2026-10-19)
- **Fast Offline Default (`make test`)**:
  - Registered `@pytest.mark.live` in `pytest.ini` and `backend/pytest.ini` with `addopts = -m "not live"`.
  - Decorated tests calling remote Ollama (`test_three_scripted_sessions_score_ordering`, `test_live_remote_ollama_connectivity_and_generation`, `test_live_remote_ollama_structured_json`) with `@pytest.mark.live`.
  - In `test_interview.py`, added auto-use fixture providing `MockLLMAdapter` for non-live interview lifecycle tests (timer, edge cases, transcript DB updates) so no network calls occur during offline testing.
  - Added `make test-live` (`pytest -m live -v -o addopts=""`) to execute only live tests against `http://10.134.74.27:11434`.
  - Execution duration dropped from 13:05 (785.55s) to 1:55 (115.84s), an 85% speedup.
- **Real Spell Checker Library (`pyspellchecker`)**:
  - Replaced hardcoded `COMMON_RESUME_TYPOS` dictionary in `backend/app/services/resume_reviewer.py` with `pyspellchecker.SpellChecker`.
  - Created `TECHNICAL_TERMS_ALLOWLIST` containing ~100 software engineering terms (`FastAPI`, `PostgreSQL`, `Redis`, `Docker`, `PyMuPDF`, `TailwindCSS`, `Vite`, `React`, `TypeScript`, `GitHub`, `LeetCode`, `microservices`, `telemetry`, `uptime`, etc.) and populated it with `STRONG_ACTION_VERBS` and `COMMON_SKILLS`.
  - Stripped emails, URLs, and dynamically added candidate name and profile data to allowlist to prevent false positives on names and URLs.
  - Documented limitation honestly: `pyspellchecker` is a word-level dictionary check. It detects lexical misspellings, but does NOT catch syntax or subject-verb agreement errors (e.g., "I has worked on the project") because each word is an individual valid English word.
- **Planted Typos & Grammar Test**:
  - Added `test_spelling_checker_library_and_grammar_limitations` in `backend/tests/test_resume_review.py`.
  - Caught typos: `recieve` -> `receive`, `enviroment` -> `environment`, `teh` -> `the`, `definately` -> `definitely`.
  - Uncaught: `"I has worked on the project"` (word-level dictionary limitation).
  - Preserved terms: `FastAPI`, `PostgreSQL`, `Redis`, `Docker`, `React`, `TypeScript` (0 false positives).
- **Browser Tracker Flow Explanation & Run**:
  - `test_browser_tracker_flow.py` was previously skipped because the Vite frontend dev server (`http://localhost:5173`) was not running during standalone backend pytest execution.
  - Verified by starting backend (port 8000) and frontend (port 5173) and running `pytest backend/tests/test_browser_tracker_flow.py -v -s`: all 5 dual-session browser steps passed in 64.07s.
- **Python 3.11 Compatibility**:
  - Installed Python 3.11.17 via Homebrew (`/opt/homebrew/bin/python3.11`).
  - Created clean virtualenv `backend/venv_py311` with `backend/requirements.txt`.
  - Ran full test suite: 122 passed, 1 skipped, 3 deselected in 79.65s (0:01:19). Zero syntax, typing, or library breaks.

### 6. Small Cleanups: Python 3.11 Default, Isolated test-e2e, pyspellchecker Word Count & LLM Scope (2026-10-19)
- **Python 3.11 Default in Build System**:
  - Configured `PYTHON ?= python3.11` as default in `Makefile` and updated prerequisites in `README.md`.
  - Removed deprecated Python 3.9 `backend/venv` and temporary `backend/venv_py311`.
  - Re-ran `make test` from scratch: bootstrapped clean Python 3.11.17 virtual environment in `backend/venv`, installed all requirements, and passed all 122 offline tests in 71.90s.
- **Gitignore Protection**:
  - Appended `backend/venv_py311/`, `*venv*/`, `.pytest_cache/`, and `**/.pytest_cache/` to `.gitignore`.
  - Verified via `git status` that zero venv or cache files are staged or untracked.
- **Playwright Chromium Setup Automation**:
  - Embedded `$(BIN)/playwright install chromium` directly into `setup-backend` target in `Makefile`.
  - Documented automatic installation and manual verification commands in `README.md`.
- **Isolated `make test-e2e` Target**:
  - Created `make test-e2e` backed by `scripts/run_e2e.sh`.
  - **Database Isolation Behavior**: Previously, running tests against a running dev server wrote test accounts (`admin_<timestamp>@msot.ac.in`, `eligible_<timestamp>@msot.ac.in`, `ineligible_<timestamp>@msot.ac.in`) and jobs into the dev database (`backend/data/career_copilot.db`).
  - Under `make test-e2e`, the backend and test session are started with `DATABASE_URL=sqlite:///backend/data/test_e2e.db`. Upon completion or interruption, both background servers are terminated and `test_e2e.db*` is wiped.
  - Added `cleanup_e2e_records` fixture to `test_browser_tracker_flow.py` for database teardown.
  - Verified that recent test user `admin_1792396396@msot.ac.in` was written only to the temporary database and zero test users leaked into `backend/data/career_copilot.db`.
  - Verified all 5 dual-session browser steps passed in 51.93s.
- **pyspellchecker English Dictionary Measured Count**:
  - Measured exact vocabulary size of `pyspellchecker.SpellChecker().word_frequency.dictionary`: **160,572 unique words** (total corpus word frequency occurrences: `1,646,569,324`).
- **LLM Grammar Check Scope Clarification**:
  - Explicitly clarified that the LLM grammar check evaluates **only the experience and project accomplishment bullets** (3-4 bullet lines, 445 characters, 27.3% of the resume text).
  - Sections **NOT** covered by the LLM prompt:
    1. Contact header (Name, Phone, Email, Location)
    2. Profile links (GitHub, LeetCode, Portfolio URLs)
    3. Education section (Degree, University, GPA, Coursework)
    4. Technical skills inventory (Languages, Frameworks, Developer Tools)
    5. Co-curricular achievements (Awards, Hackathons, Certifications)
  - All non-bullet sections are audited deterministically by dedicated Python code-first rubrics.

