# Placement Readiness Copilot for MSOT Students

A single, unified application with an AI chat interface and career copilot where MSOT students upload their resume, LinkedIn, GitHub, LeetCode, and projects, receive automated benchmark-based reviews, participate in mock interviews (voice & text), calculate an institutional placement readiness score, and discover, apply to, and track jobs. MSOT placement staff can post institutional openings directly to students with automated eligibility gating.

---

## System Architecture

```
├── backend/
│   ├── app/
│   │   ├── llm/               # Unified LLM provider abstraction (Ollama, OpenAI, Claude, Gemini)
│   │   │   ├── adapters/      # Local-first Ollama adapter & cloud adapters
│   │   │   ├── factory.py     # Provider instantiation & failover logic
│   │   │   └── structured.py  # JSON self-correction retry loop (temp=0)
│   │   ├── routers/           # Auth, Profile, Reviews, Interview, Readiness, Jobs, Tracker, Admin, Privacy
│   │   ├── services/          # Parsers, Reviewers, GitHub Auditor, Whisper ASR, Job Discovery, Matcher
│   │   ├── models.py          # SQLAlchemy models (User, Profile, Reviews, Interview, Applications)
│   │   ├── schemas.py         # Pydantic v2 schemas
│   │   ├── auth.py            # PBKDF2 password hashing & JWT role auth
│   │   └── main.py            # FastAPI entrypoint & secure log sanitizer
│   ├── scripts/
│   │   └── seed_data.py       # Seed script (Admin, Demo Student, 5 Diverse Sample Students)
│   ├── data/                  # SQLite DB (WAL mode), uploads, and screenshots
│   └── tests/                 # Module unit & integration tests
├── frontend/                  # React 18 + Vite + Tailwind CSS
│   ├── src/
│   │   ├── components/        # Sidebar, ChatShell, VoiceControls, KanbanBoard
│   │   ├── pages/             # Dashboard, Reviews, Interview, Jobs, Tracker, Admin, Profile, Privacy
│   │   └── api.js             # API client with JWT bearer handling
│   └── package.json
├── tests/                     # Challenge & E2E verification test suite
│   ├── test_consistency.py        # 5-run deterministic score repeatability (±3 pts)
│   ├── test_github_livelinks.py    # Secret scanner & Playwright live deployment verification
│   ├── test_job_matching.py       # Multi-profile ranking & cross-source deduplication
│   ├── test_tracker_msot_e2e.py    # Admin post -> student apply -> candidate triage lifecycle
│   ├── test_privacy_deletion.py   # Consent gating, data wipe, and permanent account deletion
│   ├── locustfile.py              # Locust load test simulating 100 concurrent users
│   └── calculate_token_cost.py    # Real token accounting & API cost per student journey
├── docs/                      # Architecture, benchmarks, module specifications, and test reports
│   └── screenshots/           # High-resolution application UI screenshots
└── Makefile                   # One-command build, launch, test, and seed
```

---

## One-Command Quickstart

### Prerequisites
- **Python**: 3.11 (default in Makefile; `python3.11` required)
- **Node.js**: 18+ and npm
- **Playwright Chromium**: installed automatically during setup via `playwright install chromium` (or manually with `./backend/venv/bin/playwright install chromium`)
- **Ollama** *(optional for local-first offline inference)*: [ollama.com](https://ollama.com/)

### 1. Launch Everything (`make dev`)
```bash
make dev
```
This single command automatically:
1. Bootstraps the Python virtual environment in `backend/venv` with Python 3.11.
2. Installs all backend dependencies (`requirements.txt`).
3. Installs Playwright Chromium headless browser binary (`playwright install chromium`).
4. Installs frontend dependencies (`npm install`).
5. Configures SQLite in Write-Ahead Logging (WAL) mode.
6. Concurrently launches:
   - **FastAPI Backend**: `http://localhost:8000` (Swagger Docs: `http://localhost:8000/docs`)
   - **React Frontend**: `http://localhost:5173`

### 2. Seed Demo Data (`make seed`)
> ⚠️ **DEMO ENVIRONMENT WARNING**: Demo credentials (`admin@msot.edu` / `admin123`, `student@msot.edu` / `student123`) and sample student profiles are **strictly synthetic demo data** intended for local development and demonstration only. NEVER expose these default accounts or passwords to production environments.
>
> **Real Pipeline Execution**: All seeded readiness scores across the 5 sample candidates are **computed by running the real scoring pipeline** (`compute_and_save_readiness_score`) against synthetic fake resumes in `backend/tests/fixtures/`, rather than being inserted directly with arbitrary numbers.

In a separate terminal, populate the database with staff credentials, a demo student, and 5 diverse sample students across all placement readiness tiers:
```bash
make seed
```

### 3. Run Test Suites
- **Fast Offline Tests (`make test`)**:
  Executes fast offline unit and integration tests (under 2 minutes):
  ```bash
  make test
  ```
- **Isolated Browser E2E Tests (`make test-e2e`)**:
  Spawns backend with an isolated temporary database, launches frontend dev server, executes the complete Playwright browser flow (`test_browser_tracker_flow.py`), stops both servers, and wipes the temporary database:
  ```bash
  make test-e2e
  ```
- **Live Ollama Inference Tests (`make test-live`)**:
  Executes live remote Ollama tests against `http://<OLLAMA_HOST>:11434` (configurable via `OLLAMA_BASE_URL`):
  ```bash
  make test-live
  ```
- **Challenge Verification Suite**:
  ```bash
  ./backend/venv/bin/pytest tests/ -v
  ```

---

## Environment Configuration & Production Security

Environment variables are loaded from the shell or `.env` file (template provided in `.env.example`):
- **Development Mode (`APP_ENV=development`)**: If `SECRET_KEY` is not provided, the application auto-generates a secure 32-byte urlsafe key on startup and appends it to `.env` (gitignored).
- **Production Mode (`APP_ENV=production`)**: The application **strictly refuses to start** with a fatal `RuntimeError` if `SECRET_KEY` is missing or empty.
- **Compromised Key Blacklist**: The legacy development fallback key (`mirai_placement_copilot_secret_jwt_key_2026`) is treated as compromised and rejected with an immediate fatal error if supplied.

---

## Local-First Offline & Remote Ollama Setup

The Placement Readiness Copilot is engineered from the ground up to run **100% locally with zero paid API keys** using Ollama:

### Option A: Local Ollama on Your Machine
```bash
# 1. Install Ollama (macOS example: brew install ollama)
# 2. Start the local daemon
ollama serve

# 3. Pull recommended models
ollama pull qwen2.5:3b
ollama pull qwen2.5:7b
```

### Option B: Remote Ollama Host (Network GPU / Server)
If Ollama is hosted on a separate server or laptop (e.g. `http://<OLLAMA_HOST>:11434` or custom URL):
1. In the Copilot UI, open **Settings & Models** (`#nav-settings`).
2. Set **Ollama Base URL** to `http://<OLLAMA_HOST>:11434`.
3. Set **Model** to `qwen2.5:3b` or `qwen2.5:7b`.
4. Click **Save Settings** (or export `OLLAMA_BASE_URL=http://<OLLAMA_HOST>:11434` in your shell).
5. All resume reviews, LinkedIn audits, and placement scores will now execute via Ollama at `$0.00` API cost.

> **Note on Mock Interview**: The voice & text mock interview module is fully built, but intentionally disabled behind `ENABLE_MOCK_INTERVIEW=False` for the submission. The Placement Readiness Score automatically applies the **80% Rescaling Rule** across the active 6 dimensions ($Score / 0.80$).

---

## Demo Credentials

The seed script creates the following pre-configured accounts:

| Role | Email | Password | Details |
| :--- | :--- | :--- | :--- |
| **MSOT Placement Admin** | `admin@msot.edu` | `admin123` | Institutional access, post campus jobs, triage student applicants. |
| **Demo Student** | `student@msot.edu` | `student123` | Alex Rivera (Full Stack, Score: 78 - Placement Ready). |

### 5 Sample Student Profiles (Across Placement Readiness Tiers)

| Student Name | Email | Password | Target Roles | Readiness Score | Placement Tier |
| :--- | :--- | :--- | :--- | :---: | :--- |
| **Ananya Sharma** | `ananya.sharma@msot.edu` | `student123` | Backend, Cloud Infrastructure | **88 / 100** | **Placement ready** |
| **Rohan Patel** | `rohan.patel@msot.edu` | `student123` | Frontend, Full Stack | **78 / 100** | **Placement ready** |
| **Priya Nair** | `priya.nair@msot.edu` | `student123` | Data Science, ML Engineer | **68 / 100** | **Almost ready** |
| **Vikram Verma** | `vikram.verma@msot.edu` | `student123` | DevOps, Site Reliability (SRE) | **58 / 100** | **Almost ready** *(Missing Interview)* |
| **Sneha Reddy** | `sneha.reddy@msot.edu` | `student123` | Software Intern | **38 / 100** | **Not ready** *(Missing Projects & Flaws)* |

---

## Application UI Walkthrough

### 1. Placement Readiness Dashboard
Visualizes the student's real-time readiness score out of 100 across 7 weighted dimensions, deterministic placement tier classification, historical progression SVG chart, and top 5 ranked high-impact action items.

![Placement Readiness Dashboard](docs/screenshots/01_readiness_dashboard.png)

---

### 2. Automated Benchmark Reviewers
Automated rubrics for Resume, LinkedIn, and GitHub public presence. Code-first checks compute page count, contact links, ATS structure, and secret absence, while LLM synthesis operates at `temperature=0` with structured schema validation.

![Benchmark Reviews](docs/screenshots/02_benchmark_reviews.png)

---

### 3. Voice & Text Mock Interview Console
Conducts dynamic, role-tailored technical and behavioral interview sessions with realistic time limits, structured question plans, real-time voice speech-to-text (using local `faster-whisper`), and multi-dimensional rubric scoring.

![Mock Interview Console](docs/screenshots/03_mock_interview.png)

---

### 4. Permitted Job Discovery Feed
Ingests public job boards from Greenhouse, Lever, RSS feeds, and internal MSOT postings. Deduplicates listings, computes candidate match scores based on verified skills and target roles, and generates 1-click outbound Boolean deep links for LinkedIn, Naukri, and Internshala.

![Job Discovery](docs/screenshots/04_job_discovery.png)

---

### 5. Application Tracker (Kanban & Table)
Full-lifecycle job tracker with interactive Kanban board and tabular views. Tracks application status progression (`Saved` $\to$ `Applied` $\to$ `Interview` $\to$ `Offer` $\to$ `Rejected`), captures interview dates, and records follow-up notes.

![Application Tracker](docs/screenshots/05_job_tracker.png)

---

### 6. MSOT Placement Staff Admin Portal
Institutional portal for placement officers to post verified campus job openings, set eligibility gating (minimum placement readiness score), triage student applicants, and promote candidates across interview stages.

![MSOT Admin Board](docs/screenshots/06_admin_board.png)

---

## Challenge Verification & Test Results

### 1. Challenge Test Suite (`tests/`)
All challenge verification scripts reside in the root `tests/` directory:

| Test Script | Test Focus | Result |
| :--- | :--- | :---: |
| `tests/test_consistency.py` | 5 consecutive runs on Resume & LinkedIn; verifies delta $\le \pm 3$ pts. | **PASSED** (Delta = 0) |
| `tests/test_github_livelinks.py` | Secret scanner detects AWS/RSA keys; Playwright verifies live deployment HTTP 200 and captures screenshots. | **PASSED** |
| `tests/test_job_matching.py` | Role-specific rankings for Frontend, Backend, and Data Science; cross-source deduplication. | **PASSED** |
| `tests/test_tracker_msot_e2e.py` | Admin post $\to$ student eligibility gating $\to$ application $\to$ interview triage $\to$ stage movement. | **PASSED** |
| `tests/test_privacy_deletion.py` | Explicit consent gate, data wipe, and physical file unlinking on account deletion. | **PASSED** |

Run verification:
```bash
./backend/venv/bin/pytest tests/ -v
```

---

### 2. High-Concurrency Load Testing (Locust)

The load testing suite (`tests/locustfile.py`) evaluates application capacity under concurrent student traffic against a **Mock LLM** (zero traffic sent to Ollama):

#### Scenario A: Read-Only Browsing Traffic (125 Concurrent Users)
> *Note: These numbers covered read-only endpoints exclusively.*
- **Concurrent Users**: **125 concurrent users** (spawn rate 25/s over 30s)
- **Total Requests Handled**: **3,499 requests**
- **Throughput (RPS)**: **118.03 req/s** sustained
- **Error Rate**: **0.00%** (0 failures across all 3,499 requests)
- **Response Times (Aggregated)**:
  - Median (**p50**): **3 ms**
  - 95th Percentile (**p95**): **18 ms**
  - 99th Percentile (**p99**): **46 ms**
  - Max Response Time: **76 ms**
- **Core Endpoints Breakdown**:
  - `GET /api/readiness/current`: 680 reqs, 0 failures, p50: **2 ms**, p95: **8 ms**
  - `GET /api/jobs/discover`: 568 reqs, 0 failures, p50: **3 ms**, p95: **7 ms**
  - `GET /api/profile/me`: 552 reqs, 0 failures, p50: **2 ms**, p95: **28 ms**
  - `GET /api/health`: 395 reqs, 0 failures, p50: **1 ms**, p95: **8 ms**
  - `GET /api/readiness/history`: 377 reqs, 0 failures, p50: **2 ms**, p95: **9 ms**
  - `GET /api/reviews/{type}/latest`: 373 reqs, 0 failures, p50: **2 ms**, p95: **33 ms**
  - `GET /api/tracker/applications`: 346 reqs, 0 failures, p50: **2 ms**, p95: **27 ms**
  - `POST /api/auth/login`: 208 reqs, 0 failures, p50: **15 ms**, p95: **23 ms**

#### Scenario B: Review-Submission & Background Queue Processing (125 Concurrent Users)
Simulates **125 students concurrently submitting real resume reviews** through the asynchronous job queue (`POST /api/jobs/trigger`) and polling for completion (`GET /api/jobs/status/{id}`), with the Mock LLM configured to sleep **1.0 second** per review and provider concurrency limits enforced (`LLM_CONCURRENCY_MOCK=10`):
- **Concurrent Users**: **125 concurrent students**
- **Total Requests Handled**: **9,825 requests** (125 review submissions + 9,700 queue status polls)
- **Review Submissions Completed**: **125 of 125** (100% completion)
- **Error Rate**: **0.00%** (0 failures across all 9,825 requests)
- **Submit Latency (`POST /api/jobs/trigger`)**:
  - Median (**p50**): **49 ms**
  - 95th Percentile (**p95**): **94 ms**
  - Min / Max: **27 ms** / **123 ms**
- **Queue Wait Time (Time in queue before worker pick-up)**:
  - Median (**p50**): **11.1 ms**
  - 95th Percentile (**p95**): **1,233.6 ms** (~1.23 s)
  - Min / Max: **0.7 ms** / **12,455.3 ms**
- **Total Review Completion Time (Submit + Queue Wait + 1s LLM Inference)**:
  - Median (**p50**): **1,019.6 ms** (~1.02 s)
  - 95th Percentile (**p95**): **2,045.1 ms** (~2.05 s)
  - Min / Max: **1.9 ms** / **14,809.4 ms**

---

### 3. Empirical Token Accounting & API Cost per Student Journey

Measured with `tests/calculate_token_cost.py` directly from empirical token logs recorded in `backend/data/llm_timing.jsonl` across live model execution runs.

> ⚠️ **UNVERIFIED PLACEHOLDER DISCLAIMER**: All provider pricing rates below are **UNVERIFIED PLACEHOLDERS** loaded from `backend/app/pricing_config.json` for the user to confirm against official billing consoles (`verified: false`, `date_checked: null`). No verification date is claimed or invented.
> **Prompt Note**: Token counts reflect compact prompts used in our deterministic, code-first pipelines. Hosted prompts or alternative prompt templates with extensive system instructions may be larger.

#### Empirical Token Breakdown:
- **Active Review Journey** (Interview Disabled behind `ENABLE_MOCK_INTERVIEW`):
  - Resume Review (Grammar + Takeaways): 506 prompt / 109 completion
  - LinkedIn Review (Rewrites & Audit): 229 prompt / 76 completion
  - GitHub Code Review (Modularity): 335 prompt / 78 completion
  - Job Match Fit & Explanation: 188 prompt / 90 completion
  - **Subtotal**: **1,258 prompt tokens** / **353 completion tokens** (1,611 tokens total)
- **Full Journey with Mock Interview** (when enabled):
  - 5-turn interactive interview + grading: 3,430 prompt / 1,495 completion
  - **Total**: **4,688 prompt tokens** / **1,848 completion tokens** (6,536 tokens total)

#### Placeholder Cost per Student by Provider:
| Provider & Model | Input / 1M | Output / 1M | Active Reviews Cost | Full Journey Cost | Active Students / $1.00 | Placeholder Source URL (To Confirm) |
| :--- | :---: | :---: | :---: | :---: | :---: | :--- |
| **Local Ollama (`qwen2.5:3b/7b`)** | **$0.00** | **$0.00** | **$0.00000** | **$0.00000** | **Unlimited ($0.00)** | Self-hosted weights (Private LAN) |
| **Google Gemini 1.5 Flash** | $0.075 | $0.30 | **$0.00020** | **$0.00091** | **~5,000 students** | [ai.google.dev/pricing](https://ai.google.dev/pricing) |
| **OpenAI GPT-4o-mini** | $0.15 | $0.60 | **$0.00040** | **$0.00181** | **~2,500 students** | [openai.com/api/pricing](https://openai.com/api/pricing/) |
| **Anthropic Claude 3.5 Haiku** | $0.80 | $4.00 | **$0.00242** | **$0.01114** | **~410 students** | [anthropic.com/pricing](https://www.anthropic.com/pricing) |
| **OpenAI GPT-4o** | $2.50 | $10.00 | **$0.00668** | **$0.03020** | **~150 students** | [openai.com/api/pricing](https://openai.com/api/pricing/) |

---

## Clean-Clone Verification Procedure

To verify this project from scratch:
```bash
# 1. Clone repository into a fresh workspace
git clone <repo-url> fresh-copilot
cd fresh-copilot

# 2. Boot dependencies and launch application
make dev

# 3. In a separate terminal, seed demo data
make seed

# 4. Run full test suite
make test
```
All dependencies, virtual environments, SQLite database schemas, and Node modules configure automatically with zero manual file editing.
