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
- **Python**: 3.9+ (Python 3.11 recommended)
- **Node.js**: 18+ and npm
- **Playwright Chromium**: installed automatically in virtual environment
- **Ollama** *(optional for local-first offline inference)*: [ollama.com](https://ollama.com/)

### 1. Launch Everything (`make dev`)
```bash
make dev
```
This single command automatically:
1. Bootstraps the Python virtual environment in `backend/venv` (if missing).
2. Installs all backend dependencies (`requirements.txt`).
3. Installs frontend dependencies (`npm install`).
4. Configures SQLite in Write-Ahead Logging (WAL) mode.
5. Concurrently launches:
   - **FastAPI Backend**: `http://localhost:8000` (Swagger Docs: `http://localhost:8000/docs`)
   - **React Frontend**: `http://localhost:5173`

### 2. Seed Demo Data (`make seed`)
In a separate terminal, populate the database with staff credentials, a demo student, and 5 diverse sample students across all placement readiness tiers:
```bash
make seed
```

### 3. Run All Test Suites (`make test`)
Executes the complete test suite across all 10 modules:
```bash
make test
```
To run the challenge-specific test suite directly:
```bash
./backend/venv/bin/pytest tests/ -v
```

---

## Local-First Offline Setup with Ollama

The Placement Readiness Copilot is engineered from the ground up to run **100% locally with zero paid API keys**.

```bash
# 1. Install Ollama (macOS example)
brew install ollama

# 2. Start the local Ollama daemon
ollama serve

# 3. Pull the recommended local models
ollama pull smollm:135m       # Ultra-fast lightweight model for fast reviews & tests
ollama pull llama3            # Recommended for in-depth mock interview dialogues
```

In the Copilot UI:
1. Open **Settings & Models** (`#nav-settings`).
2. Select **Ollama** as the active LLM provider.
3. Set the model name to `smollm:135m` or `llama3`.
4. Click **Save Settings**.
5. All resume reviews, LinkedIn audits, mock interviews, and placement score calculations will now execute completely offline at `$0.00` cost.

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

### 2. High-Concurrency Load Test (Locust)
Simulates **100 concurrent student users** interacting with the backend across authentication, profile retrieval, composite readiness score calculation, historical analytics, job discovery feed, and application tracker.

```bash
PYTHONPATH=backend ./backend/venv/bin/locust -f tests/locustfile.py --headless -u 100 -r 25 --run-time 30s --host http://127.0.0.1:8000 --csv=tests/load_test_results
```

#### Measured Load Test Performance:
- **Concurrent Users**: 100 concurrent users (spawn rate 25/s)
- **Error Rate**: **0.00%** (zero failed requests across the entire run)
- **Median Response Time (p50)**: **95 ms**
- **Min Response Time**: **11 ms**
- **Core Endpoints p50**:
  - `GET /api/health`: **86 ms**
  - `GET /api/tracker/applications`: **91 ms**
  - `GET /api/readiness/history`: **91 ms**
  - `GET /api/profile/me`: **92 ms**
  - `GET /api/readiness/current`: **95 ms**

---

### 3. Token Accounting & API Cost per Student Journey

Measured with `tests/calculate_token_cost.py` across the full student lifecycle (Resume Review + LinkedIn Review + 3-turn Mock Interview):

| Metric | Measured Value |
| :--- | :--- |
| **Prompt Tokens (Input)** | 1,137 tokens |
| **Completion Tokens (Output)** | 557 tokens |
| **Total Student Journey Tokens** | **1,694 tokens** |

#### Estimated Cost per Student by Provider:
| Provider & Model | Input / 1M | Output / 1M | Cost per Student | Cost for 1,000 Students |
| :--- | :---: | :---: | :---: | :---: |
| **Ollama (smollm:135m / llama3)** | **$0.00** | **$0.00** | **$0.00000** | **$0.00** *(100% Free)* |
| **Google Gemini 1.5 Flash** | $0.075 | $0.30 | **$0.00025** | **$0.25** |
| **OpenAI gpt-4o-mini** | $0.15 | $0.60 | **$0.00050** | **$0.50** |
| **Anthropic Claude 3.5 Haiku** | $1.00 | $5.00 | **$0.00314** | **$3.14** |
| **OpenAI gpt-4o** | $2.50 | $10.00 | **$0.00841** | **$8.41** |

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
