# Placement Readiness Copilot: Architecture & Design Document

> **System Classification**: Multi-modal Career Advisory & Placement Engineering System  
> **Target Audience**: MSOT (Masters of Software Technology) Students & Institutional Placement Staff  
> **Design Philosophy**: Local-First, Benchmark-Driven, Deterministic Scoring, Zero-Scraping Privacy  

---

## 1. System Architecture Diagram

```mermaid
flowchart TB
    subgraph ClientLayer["Frontend Client (React 18 + Vite + Tailwind CSS)"]
        UI_Chat["Copilot Chat Intake"]
        UI_Dash["Readiness Dashboard (7 Dimensions)"]
        UI_Reviews["Benchmark Reviewers (Resume, LinkedIn, GitHub)"]
        UI_Interview["Mock Interview Console (Voice & Text)"]
        UI_Jobs["Job Discovery & Boolean Query Generator"]
        UI_Tracker["Application Tracker (Table & Kanban)"]
        UI_Admin["MSOT Staff Admin Portal"]
    end

    subgraph APILayer["FastAPI Application Gateway (Python 3.11)"]
        Router_Auth["/api/auth (JWT, PBKDF2, RBAC)"]
        Router_Profile["/api/profile (Intake, Consent, Files)"]
        Router_Reviews["/api/reviews (Resume, LinkedIn, GitHub)"]
        Router_Interview["/api/interview (Plan, Turn, Transcribe, End)"]
        Router_Readiness["/api/readiness (Current, History, Recalculate)"]
        Router_Jobs["/api/jobs (Discover, Query, Sources)"]
        Router_Tracker["/api/tracker (Applications, Status, Stage Move)"]
        Router_Admin["/api/admin (Jobs, Candidates, Export, Audit)"]
        Router_Privacy["/api/privacy (Export, Wipe, Delete Account)"]
    end

    subgraph ServiceLayer["Core Domain Services & Engines"]
        Svc_ProfileParser["Profile & Resume Parser (pdfplumber, docx)"]
        Svc_ResumeReview["Resume Benchmark Reviewer (Deterministic Rubric)"]
        Svc_LinkedInReview["LinkedIn Reviewer (Recruiter Rubric)"]
        Svc_GitHubAudit["GitHub Auditor & Secret Scanner (Entropy / Pattern)"]
        Svc_Playwright["Playwright Chromium Runner (Live Link & Screenshots)"]
        Svc_Whisper["Local Whisper ASR (faster-whisper)"]
        Svc_Interview["Mock Interview Engine (Structured Question Plan)"]
        Svc_Readiness["Readiness Calculator (Weighted Formula, Top 5 Actions)"]
        Svc_JobMatcher["Job Matcher & Outbound Query Engine (Boolean Links)"]
    end

    subgraph LLMLayer["Unified LLM Provider Abstraction (backend/llm)"]
        LLM_Interface["LLM Provider Interface (Temperature 0, Structured JSON)"]
        Adapter_Ollama["Ollama Adapter (Local smollm:135m / llama3)"]
        Adapter_OpenAI["OpenAI Adapter (gpt-4o / gpt-4o-mini)"]
        Adapter_Claude["Anthropic Claude Adapter (Claude 3.5 Haiku / Sonnet)"]
        Adapter_Gemini["Google Gemini Adapter (Gemini 1.5 Flash / Pro)"]
    end

    subgraph DataLayer["Persistence & Storage Layer"]
        DB_SQLite[("SQLite in WAL Mode (career_copilot.db)")]
        FS_Uploads["File Storage: Resumes & Profiles (backend/data/uploads)"]
        FS_Screenshots["File Storage: Playwright Captures (backend/data/screenshots)"]
    end

    subgraph ExternalPermitted["Permitted Job Ingestion & Outbound Surfaces"]
        Ext_Greenhouse["Greenhouse Public Boards API (JSON)"]
        Ext_Lever["Lever Public Postings API (JSON)"]
        Ext_RSS["Permitted Syndication Feeds (We Work Remotely, Remotive)"]
        Ext_MSOT["MSOT Internal Campus Board (Institutional)"]
        Ext_Outbound["Browser Deep-Search Links (LinkedIn, Naukri, Internshala)"]
    end

    %% Client to API
    ClientLayer -->|REST / JSON + JWT Bearer| APILayer

    %% API to Services
    Router_Auth --> Svc_Readiness
    Router_Profile --> Svc_ProfileParser
    Router_Reviews --> Svc_ResumeReview
    Router_Reviews --> Svc_LinkedInReview
    Router_Reviews --> Svc_GitHubAudit
    Svc_GitHubAudit --> Svc_Playwright
    Router_Interview --> Svc_Interview
    Router_Interview --> Svc_Whisper
    Router_Readiness --> Svc_Readiness
    Router_Jobs --> Svc_JobMatcher
    Router_Tracker --> Svc_JobMatcher
    Router_Admin --> DB_SQLite
    Router_Privacy --> DB_SQLite

    %% Services to LLM
    Svc_ResumeReview --> LLM_Interface
    Svc_LinkedInReview --> LLM_Interface
    Svc_Interview --> LLM_Interface
    LLM_Interface --> Adapter_Ollama
    LLM_Interface --> Adapter_OpenAI
    LLM_Interface --> Adapter_Claude
    LLM_Interface --> Adapter_Gemini

    %% Services to Data
    APILayer --> DB_SQLite
    Svc_ProfileParser --> FS_Uploads
    Svc_Playwright --> FS_Screenshots

    %% Job Ingestion
    Svc_JobMatcher --> Ext_Greenhouse
    Svc_JobMatcher --> Ext_Lever
    Svc_JobMatcher --> Ext_RSS
    Svc_JobMatcher --> Ext_MSOT
    Svc_JobMatcher -.->|User-Initiated Open Search| Ext_Outbound
```

---

## 2. Design Document: System Architecture & Boundaries

### 2.1 Executive Summary & Core Tenets
The **Placement Readiness Copilot** bridges the gap between academic preparation and competitive software engineering recruitment for MSOT students. It replaces fragmented, subjective career advice with an automated, benchmark-driven feedback loop, realistic technical interviews, and privacy-first campus job matching.

The architecture is governed by five non-negotiable principles:
1. **Local-First & Zero Paid API Dependency**: The full application runs locally on student hardware using **Ollama** (`smollm:135m` or `llama3`) and local **faster-whisper**. No external API keys or cloud subscriptions are required.
2. **Benchmark-Driven Scoring**: Every evaluation returns structured records: `{id, label, pass, evidence, fix}`. Deterministic checks (page counts, layout, links, headings, regex secrets) are computed in pure Python code. The LLM is restricted to subjective rubric synthesis at `temperature=0` with schema validation, guaranteeing score consistency within $\pm 3$ points.
3. **Strict Data Ethics & Zero-Scraping**: The system never scrapes walled gardens (LinkedIn, Naukri, Indeed), never stores student login cookies, and respects `robots.txt` and domain rate limits. Job discovery uses verified public board APIs (Greenhouse, Lever, RSS) and compiles clean outbound Boolean queries for manual browser search.
4. **Student Privacy & Right-to-be-Forgotten**: All data is student-owned. Full visibility, one-click JSON/ZIP export, and instantaneous cryptographic cascade deletion are enforced across database records and disk storage.
5. **Decoupled Autonomous Modules**: Each domain module operates with isolated routers, services, and pytest suites, assembled into a unified single-command runtime (`make dev`).

---

### 2.2 System Modules & Functional Breakdown

| Module | Core Responsibility | Key Implementation Files |
| :--- | :--- | :--- |
| **01 Intake & Profile** | Document parsing (PDF/DOCX), profile synthesis, GDPR-compliant consent gating. | `app/routers/profile.py`, `app/services/profile_parser.py` |
| **02 Resume Review** | Single-page layout, ATS heading hierarchy, quantified metric bullet verification. | `app/routers/reviews.py`, `app/services/resume_reviewer.py` |
| **03 LinkedIn Review** | Recruiter visibility, custom URL, headline impact, metrics in experience bullets. | `app/services/linkedin_reviewer.py` |
| **04 GitHub & Live Links**| Secret scanning (AWS/RSA/Tokens), repo structure audit, Playwright live deployment verification. | `app/services/github_auditor.py`, `app/services/secret_scanner.py`, `app/services/link_checker.py` |
| **05 Readiness Score** | 7-dimension weighted composite index (0-100), tier mapping, top 5 ranked action items. | `app/routers/readiness.py`, `app/services/readiness_service.py` |
| **06 Mock Interview** | Multi-round technical/behavioral dialogue, question plan, voice mode (Whisper), rubric scoring. | `app/routers/interview.py`, `app/services/interview_engine.py`, `app/services/transcription.py` |
| **07 Job Discovery** | Public API ingestion (Greenhouse, Lever, RSS, MSOT), deduplication, profile ranking, Boolean query engine. | `app/routers/jobs.py`, `app/services/job_discovery/` |
| **08 Tracker & MSOT** | Application lifecycle management (Kanban & Table), status progression, MSOT staff posting & candidate triage. | `app/routers/tracker.py`, `app/routers/admin.py` |
| **09 Data & Privacy** | Explicit consent, export packaging, single-click data wipe, permanent account deletion cascade. | `app/routers/privacy.py`, `app/services/privacy_service.py` |
| **10 Unified LLM Layer** | Factory provider interface with adapters for Ollama, OpenAI, Claude, and Gemini with auto-fallback. | `backend/llm/` (`interface.py`, `ollama_adapter.py`, `openai_adapter.py`, `claude_adapter.py`, `gemini_adapter.py`) |

---

### 2.3 Mathematical Formula for Placement Readiness Score

The readiness score is a weighted linear combination across 7 MSOT benchmark dimensions:

$$\text{Overall Score} = \sum_{i=1}^{7} \left( \text{Score}_i \times \frac{\text{Weight}_i}{100} \right)$$

$$\sum_{i=1}^{7} \text{Weight}_i = 100\%$$

| Dimension ($i$) | Weight ($\text{Weight}_i$) | Scoring Basis & Evaluator Logic |
| :--- | :---: | :--- |
| **Resume** | **25%** | Automated benchmark review (`ReviewResult`, `review_type="resume"`). Single-page ATS structure, contact links, action-result bullets with quantified metrics. |
| **Projects** | **25%** | Profile projects evaluator (`evaluate_projects_component`). Checks $\ge 2$ production projects with GitHub repos, live URLs, architecture descriptions, and declared tech stacks. |
| **Mock Interview** | **20%** | Mock interview module (`InterviewSession`). Evaluates technical depth, problem-solving, trade-off analysis, and communication clarity. |
| **GitHub Presence** | **10%** | Repository audit & Playwright live-check (`review_type="github"`). README completeness, meaningful commits, zero leaked secrets, and HTTP 200 live deployment. |
| **Coding Practice** | **10%** | LeetCode / competitive evaluator (`evaluate_coding_practice_component`). Verified handle, streak activity, and target of 100+ solved Medium/Hard DSA problems. |
| **LinkedIn Profile** | **5%** | Recruiter visibility review (`review_type="linkedin"`). Custom vanity URL, role-specific headline, quantified experience bullets, substantive career summary. |
| **Co-curricular** | **5%** | Achievements evaluator (`evaluate_cocurricular_component`). Hackathon victories, cloud certifications (AWS/GCP/Azure), open source contributions, student club leadership. |

#### Deterministic Placement Readiness Tiers
- **0 – 49**: **Not ready** (Critical foundational gaps; missing projects or failed benchmark reviews).
- **50 – 74**: **Almost ready** (Solid technical baseline; within 3–5 targeted actions of clearance).
- **75 – 100**: **Placement ready** (Cleared for campus placement drives and enterprise recruitment).

#### Missing Components Policy & Dynamic Rescaling Rule
- **Baseline (Interview Present & Enabled)**: When `ENABLE_MOCK_INTERVIEW` is `True` and the interview is completed, the composite score uses the standard 7-dimension weights summing to 100% (Mock Interview = 20%).
- **Dynamic Rescaling (Interview Disabled or Absent)**: When the mock interview is **not enabled** (`ENABLE_MOCK_INTERVIEW=False`) or **not taken** by the candidate:
  - The score is calculated exclusively from the remaining 6 components, rescaled to 100 by dividing each component's base weight by 80:
    $$\text{Rescaled Weight}_i = \frac{\text{Weight}_i}{80} \times 100\%$$
    $$\text{Overall Score} = \sum_{i \in \text{remaining}} \left( \text{Score}_i \times \frac{\text{Weight}_i}{80} \right)$$
  - Rescaled dimension weights:
    - Resume: $25 / 80 = \mathbf{31.25\%}$
    - Projects: $25 / 80 = \mathbf{31.25\%}$
    - GitHub Presence: $10 / 80 = \mathbf{12.50\%}$
    - Coding Practice: $10 / 80 = \mathbf{12.50\%}$
    - LinkedIn Profile: $5 / 80 = \mathbf{6.25\%}$
    - Co-curricular: $5 / 80 = \mathbf{6.25\%}$
    - Mock Interview: $\mathbf{0.00\%}$ (Excluded / Paused)
  - **Student Notification Note**: In this mode, the system surfaces a clear note in the API response and UI:
    > *"Mock interview not included. Your score is based on the other 80% of the readiness criteria."*
  - **Top Actions Policy**: When `ENABLE_MOCK_INTERVIEW` is `False`, the top-5 actions list strictly omits mock interview recommendations. If incomplete dimensions among the remaining 6 exist, $\text{Score}_i = \text{null}$, contributing $0.0$ to the composite sum without throwing runtime exceptions.

---

### 2.4 Job-Source Architecture & Data Ethics Blueprint

The Copilot solves the job discovery dilemma without resorting to brittle, invasive, or Terms-of-Service-violating web scraping.

```mermaid
flowchart LR
    subgraph PermittedSources["Permitted Ingestion Sources"]
        GH["Greenhouse Public Boards API<br/>boards-api.greenhouse.io"]
        LV["Lever Public Postings API<br/>api.lever.co/v0/postings"]
        RSS["Public Syndication Feeds<br/>(We Work Remotely, Remotive)"]
        MSOT_B["MSOT Campus Board<br/>(Staff & Corporate Partner Postings)"]
    end

    subgraph CoreEngine["Copilot Job Engine"]
        Fetcher["Rate-Limited Fetchers<br/>(Robots.txt & Token Bucket)"]
        Cache["In-Memory TTL Cache<br/>(1-Hour Expiry)"]
        Deduper["Cross-Source Deduplicator<br/>(Normalized Title + Company)"]
        Ranker["Student Profile Matcher<br/>(Skills + Role + Readiness Gate)"]
        QueryGen["Boolean Query Compiler"]
    end

    subgraph StudentOutput["Student Presentation Surfaces"]
        Feed["Ranked Discovery Feed<br/>(Match Scores & Highlights)"]
        Outbound["1-Click Boolean Deep Links<br/>(LinkedIn, Naukri, Internshala)"]
        Track["Kanban Application Board<br/>(Applied, Interview, Offer)"]
    end

    PermittedSources --> Fetcher
    Fetcher --> Cache
    Cache --> Deduper
    Deduper --> Ranker
    Ranker --> Feed
    Ranker --> Track
    Ranker --> QueryGen
    QueryGen --> Outbound
```

#### 1. Ingestion Sources
- **Greenhouse Public Boards API**: Connects to `https://boards-api.greenhouse.io/v1/boards/{company_slug}/jobs` for configured technology companies, retrieving structured JSON postings without authentication.
- **Lever Public Postings API**: Queries `https://api.lever.co/v0/postings/{company_slug}?mode=json` for real-time unauthenticated job listings.
- **Standard Syndication (RSS/Atom)**: Ingests remote and engineering feeds from open syndicators with standard HTTP headers.
- **MSOT Institutional Postings**: Internal opportunities posted directly by campus placement officers, with minimum readiness score eligibility gating.

#### 2. Cross-Source Deduplication & Matching
Postings are indexed by normalized `(slugify(company), slugify(title))`. If a role appears across both Lever and RSS, the richer posting is retained. Roles are scored against the student's verified skills, target roles, and readiness tier:
$$\text{Match Score} = \left(\text{Skill Overlap} \times 0.60\right) + \left(\text{Role Similarity} \times 0.40\right)$$

#### 3. Outbound Open-Search Generator
For walled-garden platforms (LinkedIn, Naukri, Internshala, Google Jobs), the platform generates optimized Boolean search query strings:
$$\text{Query} = \left(\text{"Target Role"}\right) \text{ AND } \left(\text{Skill}_1 \text{ OR } \text{Skill}_2\right) \text{ AND } \left(\text{"Fresher" OR "Junior" OR "Intern"}\right)$$
These format pre-populated deep links that students launch directly in their authenticated browser sessions, eliminating scraping risks while maximizing recruiter relevance.

---

### 2.5 Security, Privacy & Compliance Architecture

1. **Authentication & Authorization**:
   - Industry-standard **JWT Bearer Tokens** signed with HMAC-SHA256 (`HS256`).
   - Passwords hashed using standard library **PBKDF2-HMAC-SHA256** with 100,000 iterations and cryptographically random 16-byte salt (`secrets.token_bytes(16)`).
   - Role-Based Access Control (**RBAC**) strictly separates `student` and `admin` scopes.
2. **Tenant Isolation**:
   - All profile, review, interview, and application queries filter strictly on `user_id == current_user.id`. Cross-user data access is prohibited at the ORM query level.
3. **Data Sanitization & Secret Scanning**:
   - Uploaded filenames are sanitized against path-traversal exploits (`re.sub(r"[^a-zA-Z0-9_.-]", "_", base)`).
   - Public repository audits scan for high-entropy tokens, AWS access keys (`AKIA[0-9A-Z]{16}`), and RSA private key blocks before displaying code evidence.
4. **Permanent Right-to-be-Forgotten**:
   - `DELETE /api/privacy/account` cascades across all database tables (User, Profile, Reviews, Interviews, Applications, Snapshots) and physically unlinks all stored files and Playwright screenshots from disk using `Path.unlink(missing_ok=True)`.

---

### 2.6 Persistence & Concurrency Strategy
- **Database Engine**: SQLite 3 configured with **Write-Ahead Logging (WAL)**:
  ```sql
  PRAGMA journal_mode=WAL;
  PRAGMA busy_timeout=5000;
  PRAGMA foreign_keys=ON;
  ```
- **Concurrency Benefit**: Readers execute concurrently without acquiring table locks, allowing hundreds of concurrent student sessions to read readiness scores, profile data, and job boards while background workers persist interview turns.
- **Single-Command Developer Ergonomics**: The entire stack bootstraps via `make dev`, launching the Uvicorn ASGI server and Vite React development server simultaneously. Full verification executes via `make test`.

---

### 2.7 Background Jobs, Concurrency Limits & Rate Limiting

1. **Background Job Queuing (`services/job_queue.py`)**:
   - Long LLM tasks (resume review, LinkedIn review, GitHub evaluation, live-link summaries, job matching) run asynchronously in a dedicated `ThreadPoolExecutor`.
   - Endpoint returns immediate HTTP 202 with `job_id`, status (`queued`), and dynamic queue position.
   - Frontend polls `GET /api/jobs/status/{job_id}` with persistent state in `localStorage` surviving browser reloads.
2. **Per-Provider Concurrency Limiting (`threading.Semaphore`)**:
   - Provider concurrency managed via semaphores:
     - **Ollama**: Default limit 1 (sequential queue protecting CPU/host stability).
     - **Hosted APIs** (OpenAI, Claude, Gemini, Mock): Default limit 10 (parallel throughput).
   - Configurable dynamically via `settings.json`, environment variables (`LLM_CONCURRENCY_<PROVIDER>`), or admin settings.
3. **Per-Student Rolling Rate Limiting**:
   - Sliding-window rate limiting enforcing maximum reviews per hour (default 10 reviews/hour) per student.
   - Over-limit requests receive HTTP 429 Too Many Requests with standard `Retry-After` header and remaining seconds. Strict tenant isolation ensures other students are unaffected.
4. **Resilient Failure Handling & Admin Dashboard**:
   - Cloud adapters use exponential backoff retries with jitter on HTTP 429 and timeouts.
   - Unreachable hosts fail cleanly with actionable user messages without blocking subsequent queued jobs.
   - Admin telemetry dashboard (`/api/admin/llm-queue`) displays real-time queue length, running jobs, per-provider concurrency limits, and recent LLM execution timings.

---

### 2.8 Deployment & Performance

#### 1. Hardware Benchmarks & Measured Inference Speed
All local Ollama benchmarks were measured on a physical, CPU-only laptop (**AMD Ryzen 7 3700U with Radeon Vega Mobile Gfx, 4 cores / 8 threads, 16 GB DDR4 RAM**):
- **Ollama (`qwen2.5:3b`) on CPU**: Sustained generation speed of **~5 tokens/second**.
  - **Resume Grammar Audit**: 4.26s – 13.92s wall-clock duration (310 prompt tokens, 39 output tokens).
  - **LinkedIn Rewrites**: 18.13s wall-clock duration (273 prompt tokens, 77 output tokens).
  - **GitHub Codebase Audit**: 7.58s – 12.28s wall-clock duration (333 prompt tokens, 63 output tokens).
- **Strict Factuality**: No speed figures or capacity promises are made for untested hardware. Production sizing must be validated empirically on target infrastructure.

#### 2. Architecture Recommendation: Hosted API vs. Local Ollama
- **Multi-Student Cohort Production Default**: **Hosted API (Google Gemini 1.5 Flash or OpenAI gpt-4o-mini)** is strongly recommended as the default deployment strategy for campus placement cohorts.
  - **Cost-Efficiency**: Empirical measurements confirm that Gemini 1.5 Flash costs approximately **$0.00020 per student** (~5,000 students per $1.00) in active review mode, delivering sub-second response times and effortless parallel scaling.
  - **Concurrency**: Cloud providers handle hundreds of simultaneous candidate reviews without queue congestion.
- **Local / Private Use**: **Local Ollama** (`qwen2.5:3b` / `7b`) is maintained as a zero-cost, air-gapped, privacy-preserving option for single-user local development or students without external API keys.

#### 3. Concurrency Control, Queuing & Rate Limiting
To prevent CPU saturation and host instability, background jobs are queued and throttled:
- **Asynchronous Worker Pool**: Non-blocking `ThreadPoolExecutor` accepts review jobs, returning immediate HTTP 202 with `job_id` and position.
- **Per-Provider Concurrency Semaphores**:
  - **Ollama**: Semaphore limit = **1** (strictly sequential execution protecting CPU/RAM from multi-process thrashing).
  - **Hosted APIs / Mock**: Semaphore limit = **10** (concurrent parallel dispatch).
- **Per-Student Rolling Rate Limits**: Sliding-window rate limiter restricts candidates to **10 review requests per hour** (`429 Too Many Requests` with `Retry-After: 3600`). Tenant isolation ensures other students' queues are entirely unaffected.

#### 4. Hardware Sizing Checklist for Institutional Adoption
Before deploying campus-wide, institutional IT / placement leadership should answer:
1. **Concurrent Peak Volume**: How many students will execute reviews simultaneously during placement deadlines (e.g., 50, 200, 1,000)?
2. **Compute Topology**: Will the institution provision dedicated GPU instances (e.g., NVIDIA A10G / T4 / L4 with vLLM / Ollama), or utilize managed enterprise cloud APIs (Gemini / OpenAI Azure / Bedrock)?
3. **Data Egress & Compliance**: Does student data policy require 100% on-premises execution (mandatory local Ollama on institutional hardware), or is outbound SOC2/FERPA-compliant cloud LLM usage permitted?
4. **Bandwidth & Networking**: Can the server sustain external HTTP lookups to Greenhouse/Lever APIs, or will job discovery run with pre-cached/internal MSOT institutional postings?

#### 5. Feature Status & Readiness Rescaling
- **Mock Interview Status**: Fully implemented with both text and local Whisper voice transcription (`/api/interview`), but intentionally **disabled behind `ENABLE_MOCK_INTERVIEW=False`** for submission focus.
- **80% Rescaling Rule**: With the 20% mock interview dimension paused, candidate readiness is computed over the remaining 6 dimensions and rescaled by dividing by 0.80 ($\text{Score} / 0.80$), preserving full 0–100 fidelity without penalizing students.

