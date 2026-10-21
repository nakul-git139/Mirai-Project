# Verification Report: Module 16 — Ollama Queue Resilience & Stateful Progress

**Date**: 2026-10-20  
**Environment**: macOS (Apple M2), Python 3.11.17, Vite 8.3.4, Remote Ollama LAN Host (`http://10.134.74.41:11434`, model `qwen2.5:3b`)

---

## 1. Problem Diagnosis & Resolution

### Problem 1: Resume Review Job Routing & Remote Ollama
- **Diagnosis Output**:
  - Investigated network route to previously configured IP (`http://10.134.74.156:11434`): `curl -s --connect-timeout 2 http://10.134.74.156:11434/api/tags` returned `No route to host`.
  - User provided new active IP: `10.134.74.41:11434`.
  - Verified remote Ollama connectivity on `http://10.134.74.41:11434/api/tags`: Returned models `qwen2.5:7b` (7.6B) and `qwen2.5:3b` (3.1B).
  - Executed test generation: `curl -s --connect-timeout 5 http://10.134.74.41:11434/api/generate -d '{"model": "qwen2.5:3b", "prompt": "Hi", "stream": false}'` completed in 9.8s generating 28 tokens (`"Hello! How can I assist you today?..."`).
  - Identified why reviews previously did not reach Ollama: `payload` passed to `create_job` did not store `provider` and `model`, so `job_dispatchers.py` evaluated `adapter = None` and skipped LLM generation.
- **Resolution**:
  - Updated `backend/data/settings.json` to `"provider": "ollama"`, `"model": "qwen2.5:3b"`, `"ollama_base_url": "http://10.134.74.41:11434"`.
  - `JobQueueService.create_job` resolves effective provider and model, stores them in `BackgroundJob.provider` and `BackgroundJob.model` as well as `job.payload`, guaranteeing that worker dispatchers always receive the active provider and model.
  - Implemented 1.5s fail-fast preflight check (`check_ollama_connectivity`) inside `create_job`.

### Problem 2: Progress Timer Resetting on Section Navigation
- **Diagnosis Output**:
  - The frontend previously maintained a local interval counting from `0` inside component state. Navigating between tabs unmounted the component and wiped local state, causing the timer to reset to `0.0s`.
- **Resolution**:
  - Shifted timestamp origin to the server-side `started_at` or `created_at` timestamp: `(Date.now() - new Date(started_at || created_at).getTime()) / 1000`.
  - Created global `JobContext.jsx` wrapped around `App.jsx`, maintaining active job telemetry in memory, `sessionStorage`, and `localStorage`.
  - Added global running job mini-widget in `Sidebar.jsx`, providing live continuous elapsed timer display regardless of active route.

---

## 2. Verification Commands & Real Output

### Check 1: Provider Precedence & Environment Override Transparency
- **Command**:
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
import os
from app.services.settings_service import get_public_settings
os.environ.pop('LLM_PROVIDER', None)
s1 = get_public_settings()
print('[CASE 1 - Stored Settings Win]')
print('Provider:', s1['provider'], 'env_forced:', s1['env_forced'], 'env_forced_provider:', s1['env_forced_provider'])

os.environ['LLM_PROVIDER'] = 'openai'
s2 = get_public_settings()
print('[CASE 2 - Env Var Override Wins]')
print('Provider:', s2['provider'], 'env_forced:', s2['env_forced'], 'env_forced_provider:', s2['env_forced_provider'])
os.environ.pop('LLM_PROVIDER', None)
"
```
- **Real Output**:
```
[CASE 1 - Stored Settings Win]
Provider: ollama env_forced: False env_forced_provider: None
[CASE 2 - Env Var Override Wins]
Provider: openai env_forced: True env_forced_provider: openai
```
- **Status**: PASSED

---

### Check 2: Live Resume Benchmark Review with Remote Ollama (`qwen2.5:3b`)
- **Command**:
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
import time
from app.services.job_queue import job_queue_service
from app.services.job_dispatchers import run_resume_review
from app.database import SessionLocal
from app.models import BackgroundJob, User, Profile
from tests.create_fixtures import create_clean_1page_pdf

with SessionLocal() as db:
    u = db.query(User).filter(User.role == 'student').first()
    uid = u.id

pdf_path = create_clean_1page_pdf()
with open(pdf_path, 'rb') as f:
    pdf_bytes = f.read()

import base64
payload = {
    'user_id': uid,
    'file_b64': base64.b64encode(pdf_bytes).decode('ascii'),
    'filename': 'clean_1page_resume.pdf'
}

with SessionLocal() as db:
    job = job_queue_service.create_job(user_id=uid, task_type='resume_review', payload=payload, db=db)
    jid = job.id
    print('Created job:', jid, 'provider:', job.provider, 'model:', job.model)

t0 = time.time()
job_queue_service.enqueue_and_dispatch(jid, run_resume_review, job.provider)

for _ in range(60):
    time.sleep(1.0)
    with SessionLocal() as db:
        rec = db.query(BackgroundJob).filter(BackgroundJob.id == jid).first()
        print('Job status:', rec.status, 'elapsed:', round(time.time() - t0, 1))
        if rec.status in ['done', 'failed', 'cancelled']:
            print('\n[RESULT]')
            print('Final Result summary:', rec.result.get('summary') if rec.result else None)
            print('Reviewed With:', rec.result.get('reviewed_with') if rec.result else None)
            print('Code Only Checks:', rec.result.get('code_only_checks') if rec.result else None)
            break
"
```
- **Real Output**:
```
Created job: 7d6cd2fb4eda432d provider: ollama model: qwen2.5:3b
Job status: running elapsed: 1.0
Job status: running elapsed: 2.0
Job status: running elapsed: 3.0
Job status: running elapsed: 4.0
Job status: running elapsed: 5.0
Job status: running elapsed: 6.0
Job status: running elapsed: 7.0
Job status: running elapsed: 8.0
Job status: running elapsed: 9.1
Job status: running elapsed: 10.1
Job status: done elapsed: 11.1

[RESULT]
Final Result summary: Strong technical foundation scoring 78/100 (Tier 2 (Interview Ready with Minor Fixes)). Passed 5 of 8 checks. Priority fix: Add measurable impact metrics (e.g., latency, active users, throughput) to 'Readiness Copilot'. Placement Note: Student's resume score is strong at 78/100, but target roles are not specified for placement readiness assessment.
Reviewed With: ollama / qwen2.5:3b
Code Only Checks: [1, 2, 3, 4, 5, 6, 7, 8]
```
- **Timing Logger Verification**:
```json
{
  "id": 303,
  "feature": "resume_review_takeaway",
  "provider": "ollama",
  "model": "qwen2.5:3b",
  "prompt_tokens": 135,
  "output_tokens": 37,
  "duration_seconds": 10.66,
  "status": "success",
  "created_at": "2026-10-20T12:42:57.033854"
}
```
- **Status**: PASSED

---

### Check 3: Fail-Fast on Unreachable Remote Ollama Host
- **Command**:
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
import time
from app.services.job_queue import job_queue_service
from app.services.settings_service import save_raw_settings, load_raw_settings
from app.database import SessionLocal
from app.models import User

with SessionLocal() as db:
    u = db.query(User).filter(User.role == 'student').first()
    uid = u.id

raw = load_raw_settings()
orig_url = raw.get('ollama_base_url')
raw['ollama_base_url'] = 'http://192.0.2.1:11434'
save_raw_settings(raw)

t0 = time.time()
caught_err = None
try:
    with SessionLocal() as db:
        job_queue_service.create_job(user_id=uid, task_type='resume_review', payload={}, provider='ollama', db=db)
except Exception as e:
    caught_err = str(e)
elapsed = time.time() - t0

raw['ollama_base_url'] = orig_url
save_raw_settings(raw)

print(f'[VERIFICATION - FAIL FAST]')
print(f'Elapsed until rejection: {elapsed:.2f}s')
print(f'Error message: {caught_err}')
assert elapsed < 3.0
assert 'unreachable' in caught_err.lower()
print('SUCCESS: Verified fail-fast rejection without holding queue slots.')
"
```
- **Real Output**:
```
[VERIFICATION - FAIL FAST]
Elapsed until rejection: 1.52s
Error message: Remote Ollama host at 'http://192.0.2.1:11434' is unreachable (ConnectTimeout). Please verify the Ollama machine is running on your network.
SUCCESS: Verified fail-fast rejection without holding queue slots.
```
- **Status**: PASSED

---

### Check 4: Watchdog Timeout & Restart Safety Net
- **Command**:
```bash
backend/venv/bin/pytest -v -s backend/tests/test_job_cancellation.py -k "test_per_job_maximum_run_time_releases_hung_slot or test_startup_cleanup_marks_leftover_jobs_failed_interrupted_by_restart"
```
- **Real Output**:
```
backend/tests/test_job_cancellation.py::test_startup_cleanup_marks_leftover_jobs_failed_interrupted_by_restart 
[VERIFICATION 4] Startup cleanup verification:
  - Stale running job status: failed, error_message: 'interrupted by restart'
  - Stale queued job status: failed, error_message: 'interrupted by restart'
  - Fresh job status after restart: done
PASSED

backend/tests/test_job_cancellation.py::test_per_job_maximum_run_time_releases_hung_slot 
[VERIFICATION 5] Max Run Time Watchdog:
  - Configured watchdog timeout: 1.0s
  - Total elapsed until next job completed: 1.00s
  - Hung job aborted event: False
  - Hung job final status: failed, error: 'Job timed out: exceeded maximum execution time of 1s.'
  - Next job final status: done
PASSED
```
- **Status**: PASSED

---

### Check 5: Cross-Section Navigation & Continuous Elapsed Timer (Playwright Browser Test)
- **Command**: Automated Playwright test verifying student intake, resume upload, live timer progress, navigation from Benchmark Reviews -> Profile -> Jobs -> Benchmark Reviews, and page reload persistence.
- **Real Output**:
```
[STEP 1] Navigating to frontend...
[STEP 2] Registering fresh student student_nav_1792500539@msot.ac.in...
  - Registered and logged in successfully!
  - Clicked #consent-checkbox. Consent status: Consent Granted
[STEP 3] Navigating to Benchmark Reviews (#nav-reviews)...
  - Uploaded resume PDF via file input.
  - Waiting for job progress indicator...
  - Job progress card visible! Initial elapsed timer: 0.0s
[STEP 4] Navigating to Profile tab while review is running in background...
  - Sidebar active job widget visible in Profile tab? True
  - Sidebar widget text: Resume Review | 3.0s | RUNNING | ollama / qwen2.5:3b
[STEP 5] Navigating to Jobs tab while review is running...
  - Sidebar active job widget visible in Jobs tab? True
  - Sidebar widget text in Jobs tab: Resume Review | 4.1s | RUNNING | ollama / qwen2.5:3b
[STEP 6] Returning to Benchmark Reviews tab...
  - In Resume Review: timer reads continuous progress (did NOT reset to 0s!)
[STEP 7] Waiting for review completion...
  - Completed review metadata banner appeared!
  - Banner text: Reviewed with: ollama / qwen2.5:3b | 8 benchmark checks evaluated in code (deterministic), placement summary via LLM
[STEP 8] Reloading page (refresh check)...
  - After reload, completed review metadata banner persists and renders!

[E2E VERIFICATION RESULT: 100% PASSED]
```
- **Status**: PASSED

---

### Check 6: Full Regression Test Suite (`make test`)
- **Command**: `backend/venv/bin/pytest`
- **Real Output**:
```
============================= test session starts ==============================
platform darwin -- Python 3.11.17, pytest-9.1.1, pluggy-1.7.0
rootdir: .
configfile: pytest.ini
testpaths: backend/tests, tests
plugins: asyncio-1.4.0, locust-2.46.7, anyio-4.15.1
collected 141 items / 5 deselected / 136 selected

backend/tests/test_auth.py ......                                        [  4%]
backend/tests/test_browser_tracker_flow.py .                             [  5%]
backend/tests/test_concurrency_and_queue.py ......                       [  9%]
backend/tests/test_github_review.py ..........                           [ 16%]
backend/tests/test_interview.py ......                                   [ 21%]
backend/tests/test_job_cancellation.py .....                             [ 25%]
backend/tests/test_job_discovery.py ...........                          [ 33%]
backend/tests/test_linkedin_review.py ......                             [ 37%]
backend/tests/test_llm.py ..........                                     [ 44%]
backend/tests/test_ollama_robustness.py ........                         [ 50%]
backend/tests/test_profile.py ...........                                [ 58%]
backend/tests/test_readiness_score.py .........................          [ 77%]
backend/tests/test_resume_review.py ......                               [ 81%]
backend/tests/test_settings.py ......                                    [ 86%]
backend/tests/test_tracker_msot.py .....                                 [ 89%]
backend/tests/test_voice.py ....                                         [ 92%]
tests/test_consistency.py ..                                             [ 94%]
tests/test_github_livelinks.py ..                                        [ 95%]
tests/test_job_matching.py ....                                          [ 98%]
tests/test_privacy_deletion.py .                                         [ 99%]
tests/test_tracker_msot_e2e.py .                                         [100%]

========== 136 passed, 5 deselected, 7 warnings in 177.31s (0:02:57) ===========
```
- **Status**: PASSED (0 failures, 0 regressions)

---

## 3. Items Not Verifiable & Why

- **Physical External Browser Video Capture via Builtin Agent**: The Antigravity IDE `browser_subagent` encountered a CDP context management protocol limitation (`failed to create browser context via CDP: Protocol error Browser.setDownloadBehavior`). Direct browser execution was instead verified via Playwright Chromium headless engine running against the live frontend on `http://localhost:5173` and backend on `http://localhost:8000`.
