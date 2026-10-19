# Module 14: Final Submission Preparation, Challenge Test Consolidation & Concurrency Audit

## 1. What the Module Does
Module 14 prepares the complete **Placement Readiness Copilot** for institutional submission and evaluation:
1. **Challenge Test Consolidation Matrix**: Consolidates all 7 challenge test areas (±3 score repeatability, GitHub security & live links, multi-profile job matching, tracker/MSOT end-to-end, right-to-be-forgotten privacy lifecycle, background job queue/concurrency, and server load testing) with real verified outputs in [docs/test-report.md](file:///Users/nakulmirai/Mirai%20Project/docs/test-report.md).
2. **High-Concurrency Load Testing (Mock LLM Mode)**: Evaluates application capacity under 125 concurrent users (between 100–150 users) with Locust, hitting composite readiness calculations, profile retrieval, job feeds, and tracker boards. Verifies **3,499 requests** handled at **118.03 req/s** with **0.00% error rate**, median latency (**p50**) of **3 ms**, and 95th percentile (**p95**) of **18 ms**. Explains why load tests must run against the Mock LLM rather than Ollama (evaluates server architecture, connection pooling, and SQLite WAL concurrency without saturating slow CPU hardware).
3. **Empirical API Cost Accounting**: Computes real token usage and cost per student journey directly from 151 empirical execution records in `backend/data/llm_timing.jsonl`. Demonstrates that active reviews cost **$0.00020 per student** on Gemini 1.5 Flash (~5,000 students / $1.00) and **$0.00** on local Ollama.
4. **Architecture & System Design Documentation**: Expands [docs/architecture.md](file:///Users/nakulmirai/Mirai%20Project/docs/architecture.md) with clean Mermaid diagrams, the unauthenticated job-source strategy (Greenhouse, Lever, RSS, MSOT, outbound Boolean links), and a comprehensive "Deployment and Performance" section. Documents empirical CPU inference speeds on AMD Ryzen 7 3700U with 16 GB RAM (~5 tokens/s with `qwen2.5:3b`), the queue/rate limiting architecture, and concrete sizing questions for institutional leadership. Confirms the mock interview is built but paused behind `ENABLE_MOCK_INTERVIEW=False`, applying the 80% readiness rescaling formula ($Score / 0.80$).
5. **Benchmark Rubrics Verification**: Audits [docs/benchmarks.md](file:///Users/nakulmirai/Mirai%20Project/docs/benchmarks.md) confirming all Resume, LinkedIn, GitHub, Live-Link, and Interview checks are explicitly detailed with weights, criteria, and concrete fixes.
6. **Final Documentation & Ergonomics**: Updates [README.md](file:///Users/nakulmirai/Mirai%20Project/README.md) with Python 3.11 requirements, single-command setup, and both local and remote Ollama configuration.
7. **Idempotent Seed Script**: Updates [backend/scripts/seed_data.py](file:///Users/nakulmirai/Mirai%20Project/backend/scripts/seed_data.py) to reliably populate and reset demo student (`student@msot.edu`), admin (`admin@msot.edu`), and 5 sample students across placement tiers (Ananya Sharma 88, Rohan Patel 78, Priya Nair 68, Vikram Verma 58, Sneha Reddy 38).
8. **Privacy & Git Secrets Verification**: Confirms physical disk file unlinking on data wipe and verifies that zero `.env` files, real resumes, or live API keys exist in git history.

---

## 2. How It Works: Flow from User Action to Result

### A. Load Testing Against Mock LLM
1. **Server Launch**: The backend is started with `LLM_PROVIDER=mock OFFLINE_MODE=1` (`uvicorn app.main:app`). `backend/app/services/settings_service.py` checks `os.environ.get("LLM_PROVIDER")` and forces `MockLLMAdapter`, completely bypassing remote/local Ollama network calls.
2. **Stampede-Protected Job Discovery**: In `backend/app/services/job_discovery/discovery_service.py`, `fetch_external_jobs()` uses `self._lock = asyncio.Lock()` and checks `OFFLINE_MODE=1` to prevent 125 concurrent requests from triggering external HTTP timeout loops to Greenhouse/Lever.
3. **Locust Simulation**: `backend/venv/bin/locust -f tests/locustfile.py` spins up 125 concurrent virtual student users. `get_seeded_student_tokens()` dynamically queries valid JWT tokens for seeded student users. The users execute weighted tasks against readiness, profile, job discovery, tracker, and login endpoints over a 30-second sustained run.
4. **Metrics Collection**: Requests, failures, RPS, and latency percentiles (p50, p95, p99, max) are aggregated and exported to `tests/load_test_results_*.csv`.

### B. Empirical Token & Cost Accounting
1. **Log Aggregation**: `tests/calculate_token_cost.py` parses `backend/data/llm_timing.jsonl` where `TimingAuditLogger` recorded 151 live inference calls.
2. **Category Averages**: Computes exact prompt and output token averages across `resume_review_grammar` (370/84), `resume_review_takeaway` (136/26), `linkedin_review_rewrites` (230/77), `github_code_review` (336/78), `job_matching_explanation` (188/90), and `structured_llmanswerevaluation` (686/299).
3. **Scenario Modeling**: Evaluates two distinct journeys:
   - *Active Reviews (Interview Disabled)*: 1,258 prompt tokens, 353 completion tokens (1,611 total).
   - *Full Journey (Interview Enabled)*: 4,688 prompt tokens, 1,848 completion tokens (6,536 total).
4. **Pricing Matrix**: Applies published API rates per 1M tokens across Ollama ($0.00), Gemini 1.5 Flash ($0.075 / $0.30), OpenAI gpt-4o-mini ($0.15 / $0.60), Claude 3.5 Haiku ($0.80 / $4.00), and OpenAI gpt-4o ($2.50 / $10.00).

### C. Seed Script Idempotency
1. `backend/scripts/seed_data.py` connects via `SessionLocal()`.
2. For each sample student, if the user account already exists, it resets the password, updates the full name, removes existing reviews, interviews, applications, and readiness snapshots, and re-creates the exact rubric reports and score snapshots.
3. Ensures `make seed` consistently yields the exact score profile across all 5 candidates regardless of prior database state.

---

## 3. Key Design Decisions & Alternatives Rejected

1. **Running Load Test Against Mock LLM (Accepted) vs. Ollama (Rejected)**:
   - *Rejected*: Running 100–150 concurrent users against Ollama on CPU.
   - *Rationale*: A CPU-bound SLM running at ~5 tokens/s with single-worker concurrency (`LLM_CONCURRENCY_OLLAMA=1`) would immediately queue 150 requests into multi-hour wait times. Testing application throughput against the Mock LLM tests the true server architecture (FastAPI event loop, SQLite WAL concurrency, JSON serialization, and memory pooling) without artificial external inference stalls.
2. **`asyncio.Lock()` Stampede Protection in Job Discovery (Accepted) vs. Unsynchronized External Requests (Rejected)**:
   - *Rejected*: Allowing every concurrent incoming request to spawn outbound Greenhouse/Lever HTTP requests.
   - *Rationale*: When 125 concurrent students log in simultaneously, cold caches caused 125 parallel requests to external corporate job boards, triggering timeouts and rate-limiting. Adding double-checked locking with `asyncio.Lock()` ensures exactly one fetch executes while other concurrent requests wait on the warm cache.
3. **Dynamic JWT Token Resolution in `locustfile.py` (Accepted) vs. Static Hardcoded User IDs (Rejected)**:
   - *Rejected*: Hardcoding `sub="11"` or `sub="82"` in `locustfile.py`.
   - *Rationale*: If a database is cleaned or re-created, autoincrement primary keys may change. Dynamically querying the database for seeded student emails ensures tokens always correspond to real database records.

---

## 4. Shortcuts, Placeholders & Faked Parts
- **Mock Interview Disabled**: In accordance with project instructions, `ENABLE_MOCK_INTERVIEW` is set to `False` in `backend/app/config.py`. The voice and text mock interview code remains fully implemented in `app/routers/interview.py` and `app/services/interview_engine.py`, but is paused for the core submission, with readiness rescaled over the active 80%.
- **Locust Load Test**: Run against `LLM_PROVIDER=mock` as explicitly mandated by challenge instructions.
- **Cost Calculations**: Clearly marked as an **ESTIMATE** derived from empirical timing logs and public provider token pricing.

---

## 5. Verify It Yourself

### Step 1: Run Fast Offline Backend Tests
```bash
make test
```
**Expected Result**: All 128 offline tests pass cleanly with 0 failures in under 90 seconds.

### Step 2: Run Challenge Test Suite
```bash
backend/venv/bin/pytest tests/ -v
```
**Expected Result**: All 10 challenge tests pass (consistency, secret scanner, live links, job matching, privacy deletion, tracker lifecycle).

### Step 3: Run Isolated Playwright E2E Flow
```bash
make test-e2e
```
**Expected Result**: Spins up backend on isolated DB (`test_e2e.db`), verifies all 5 dual-session browser steps (admin post, ineligible student blocked, eligible student applied, admin triage, student movement history), and wipes test DB cleanly.

### Step 4: Run Locust Load Test
```bash
# In Terminal 1:
LLM_PROVIDER=mock OFFLINE_MODE=1 backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --app-dir backend

# In Terminal 2:
backend/venv/bin/locust -f tests/locustfile.py --headless -u 125 -r 25 --run-time 30s --host http://127.0.0.1:8000
```
**Expected Result**: 125 concurrent users complete ~3,500 requests at ~118 req/s with 0 failures (0.00% error rate) and p50 under 10 ms.

### Step 5: Run Token Accounting & Cost Analysis
```bash
PYTHONPATH=backend backend/venv/bin/python3 tests/calculate_token_cost.py
```
**Expected Result**: Outputs empirical token breakdown and cost estimate table showing Gemini 1.5 Flash at ~$0.00020/student and local Ollama at $0.00.
