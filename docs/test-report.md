# Test Reports Log

## [2026-10-15] Module 01: Scaffold & LLM Interface
- **Command**: `make test`
- **Output**: 20 passed in 0.42s
- **Coverage**:
  - LLM Mock adapter and message handling
  - Structured output helper with valid JSON
  - Structured output multi-turn corrective retry on malformed JSON
  - Structured output persistent error raising clear `StructuredOutputError` with schema validation error details
  - Structured output field validation error retry
  - OllamaAdapter options (`num_ctx: 8192`, `format: "json"`, timeout 120s)
  - Ollama actionable error for unreachable server (`ollama serve`)
  - Ollama actionable error for missing model (`ollama pull`)
  - Cloud adapters requiring API keys
  - Student & Admin registration and login
  - Duplicate registration rejection
  - RBAC: Student token rejected on admin-only route with 403 Forbidden
  - Admin job creation
  - Settings retrieval contains zero API keys
  - Settings update persists keys locally without leaking in API responses
  - Log sanitizer actively redacts API keys from logs
- **Real End-to-End Checks**:
  - Live local inference via Ollama (`smollm:135m`) with structured JSON
  - Full browser navigation and settings persistence verified via browser automation
  - Clean-state `make dev` bootstrap verified from scratch
- **Status**: PASSED (0 failures)

## [2026-10-15] Module 02: Profile Intake & Privacy
- **Command**: `make test`
- **Output**: 31 passed in 1.17s
- **Coverage**:
  - Deterministic PDF text, links, and page count parsing via PyMuPDF
  - Word DOCX text, table, and links parsing via python-docx
  - Robust handling of corrupt / malformed resume files returning clean HTTP 400 (no 500)
  - Mandatory consent gate enforcement across all profile intake endpoints
  - Clean 1-page PDF fixture asserts page_count == 1, sections, skills, and links
  - Messy 3-page PDF fixture asserts page_count == 3, multi-page sections, skills, and links
  - DOCX resume fixture asserts page count, sections, skills, and links
  - LinkedIn PDF and pasted text parsing into headline, about, experience, and skills
  - Chat intake heuristic extraction for GitHub / LeetCode URLs and project links
  - Profile field editing persistence verified across page reloads
  - Physical disk file unlinking from `backend/data/uploads/` on profile data wipe
  - Physical disk file unlinking and database row cascading on account deletion
  - Tenant isolation: Student A cannot read Student B profile data (403 Forbidden)
- **Real End-to-End Checks**:
  - Live curl integration suite verifying registration, consent gate rejection, consent grant, corrupt file rejection, clean resume upload, field persistence, disk file presence, disk file deletion, and student isolation
  - Browser automation verifying full student registration, consent toggle, resume upload, ATS badge rendering, headline editing, persistence across refresh, and "My Data" file wipe
- **Status**: PASSED (0 failures)

## [2026-10-15] Module 03: Resume Review (Benchmark Rubric)
- **Command**: `make test`
- **Output**: 36 passed in 1.46s
- **Coverage**:
  - Deterministic 8-point rubric benchmark checks implementation ([docs/benchmarks.md](file:///Users/nakulmirai/Mirai%20Project/docs/benchmarks.md))
  - Single-page format enforcement (`CHK-PAGE-COUNT`, 15 pts)
  - Clean visual layout & typography evaluation with heuristic fallback (`CHK-VISUAL-LAYOUT`, 10 pts)
  - Zero spelling & grammar mistakes check with precise typo dictionary (`CHK-SPELL-GRAMMAR`, 10 pts)
  - Project completeness: description, stack, impact, live & GitHub URLs (`CHK-PROJECT-DETAILS`, 15 pts)
  - Profile links check: LeetCode & GitHub presence (`CHK-PROFILE-LINKS`, 10 pts)
  - Co-curricular achievements, certifications, and leadership check (`CHK-ACHIEVEMENTS`, 10 pts)
  - Action verbs and quantifiable metrics bullet point parser (`CHK-ACTION-RESULTS`, 15 pts)
  - ATS-friendly digital text and standard heading check with image-only detection (`CHK-ATS-FRIENDLY`, 15 pts)
  - Planted flaw detection across 4 dedicated test resumes: (a) good, (b) 2 pages, (c) missing links & typos, (d) image-only PDF
  - 5x consistency verification asserting score variance <= 3 (scores: `[100, 100, 100, 100, 100]`, diff: 0)
  - Specific fix verification asserting every failed check provides a concrete, non-empty, non-generic recommendation
  - Consent gate enforcement rejecting reviews without student consent (HTTP 400)
  - End-to-end API test verifying review generation, persistence in DB, and 150 DPI PNG preview image retrieval
- **Real End-to-End Checks**:
  - Real local Ollama model (`smollm:135m`) inference on clean (100/100) vs. flawed (65/100) resumes
  - Full browser navigation in React UI verifying score gauge matching API, tier badge, evidence quotes, actionable fixes, filter toggles, visual PDF preview panel, and dynamic re-evaluation upon file upload
- **Status**: PASSED (0 failures)

## [2026-10-16] Module 04: LinkedIn Benchmark Review
- **Command**: `backend/venv/bin/pytest -v`
- **Output**: 42 passed in 1.96s
- **Coverage**:
  - LinkedIn benchmark specification added to [docs/benchmarks.md](file:///Users/nakulmirai/Mirai%20Project/docs/benchmarks.md) (Section 5–9)
  - Profile photo presence check via PDF image stream / profile metadata (`CHK-LI-PHOTO`, 10 pts)
  - Specific headline check with 220-character LinkedIn hard limit enforcement and generic pattern rejection (`CHK-LI-HEADLINE`, 20 pts)
  - Substantive About section check requiring >= 150 characters and >= 30 words with structured background and focus (`CHK-LI-ABOUT`, 20 pts)
  - Experience and projects cross-reference comparator against verified student resume detecting title/seniority contradictions and omissions (`CHK-LI-RESUME-MATCH`, 25 pts)
  - Role-based technical skills taxonomy matching for declared placement target roles (`CHK-LI-SKILLS-ROLE`, 25 pts)
  - Planted flaw and contradiction detection across 3 test profile fixtures: Strong (100) > Contradictory (55) > Weak (35), explicitly flagging the conflicting item (*"VP of Engineering at Acme Cloud Solutions"*)
  - 5x consistency verification asserting score variance <= 3 (scores: `[100, 100, 100, 100, 100]`, variance: 0)
  - Ready-to-paste profile rewrites generation: headline (strictly <= 220 chars) and 2-paragraph About summary grounded 100% in verified facts with zero hallucinations
  - Dual input modalities tested: official LinkedIn PDF export and pasted plain profile text
  - REST API endpoints tested: `POST /api/reviews/linkedin`, `POST /api/reviews/linkedin/paste`, and `GET /api/reviews/linkedin/latest`
  - Consent enforcement verified rejecting review requests without prior student consent (HTTP 400)
- **Real End-to-End Checks**:
  - Full browser subagent automation in React UI: navigated to Benchmark Reviews -> LinkedIn tab, selected paste input mode, submitted profile, verified 100/100 score gauge and Tier 1 badge, and verified that clicking **Copy Headline** and **Copy About** triggered clipboard writes and displayed the animated "Copied!" confirmation checkmarks
  - All 42 unit and integration tests across the monorepo pass cleanly
- **Status**: PASSED (0 failures)

## [2026-10-16] Module 05: GitHub Codebase Review & Live Link Checker
- **Command**: `make test`
- **Output**: 52 passed in 11.41s
- **Coverage**:
  - GitHub codebase and live link benchmark specification added to [docs/benchmarks.md](file:///Users/nakulmirai/Mirai%20Project/docs/benchmarks.md) (Sections 10–14)
  - Profile README check via GitHub REST API (`CHK-GH-PROFILE-README`, 5 pts)
  - Pinned / featured repositories check (`CHK-GH-PINNED-REPOS`, 5 pts)
  - Regular public commit events and momentum tracking over 90 days (`CHK-GH-COMMIT-ACTIVITY`, 10 pts)
  - Project repository README inspection with setup instructions and visual screenshots/media (`CHK-GH-REPO-README`, 10 pts)
  - Clean directory structure verification detecting `.gitignore` and rejecting committed build artifacts (`node_modules/`, `dist/`, `.DS_Store`) (`CHK-GH-FOLDER-STRUCTURE`, 5 pts)
  - Commit message quality analyzer rejecting single-word lazy commits (`CHK-GH-COMMIT-MESSAGES`, 5 pts)
  - Deterministic multi-pattern regex secret scanner catching AWS keys, private keys, PATs, tokens, and database credentials (`CHK-GH-NO-SECRETS`, 15 pts)
  - Zero false positives verified on clean repository containing `.env.example`, `package-lock.json`, and documentation placeholders
  - Automated test suite presence detection across test directories and file patterns (`CHK-GH-TESTS-PRESENT`, 10 pts)
  - LLM subjective code review at temperature 0 evaluating readability, modularity, and potential bugs (`CHK-GH-CODE-REVIEW`, 10 pts)
  - Playwright live link verification loading pages within strict 15-second maximum timeout (`CHK-LIVE-LOAD-STATUS`, 10 pts)
  - Playwright runtime JavaScript console error and uncaught exception listener (`CHK-LIVE-CONSOLE-HEALTH`, 5 pts)
  - Heuristic content keyword overlap comparator between live page text and declared project claims (`CHK-LIVE-CONTENT-MATCH`, 5 pts)
  - Dual viewport mobile responsiveness and screenshot capture for desktop 1280x720 and mobile 375x667 (`CHK-LIVE-MOBILE-VIEWPORT`, 5 pts)
  - Planted flaw and error detection across 6+ test cases: good repo, repo with no README, repo with planted AWS key/private key, nonexistent username 404, live link returning 404, and live link with JavaScript console error
  - Unauthenticated GitHub rate limit simulation (mock 403) providing actionable guidance to add a personal access token in settings
  - Unreachable URL timeout enforcement (1.5s timeout) failing cleanly without hanging
  - Consent gate enforcement rejecting unconsented reviews with clean HTTP 400
- **Real End-to-End Checks**:
  - Live GitHub REST API execution against 2 real public profiles: `pallets/flask` (Score: 85/100, Tier 2) and `torvalds/uemacs` (Score: 40/100, Tier 4)
  - Live Playwright execution capturing real desktop and mobile screenshot artifacts on disk (`backend/data/screenshots/`)
  - Full browser subagent automation in React UI verifying the GitHub & Live Review subtab, score gauge, tier badge, screenshot preview switcher (Desktop vs. Mobile), filter pills, and review triggering
  - All 52 unit and integration tests across the monorepo pass cleanly
- **Status**: PASSED (0 failures)

---

## 2026-10-16: Module 06 — Placement Readiness Score & Progression Analytics

- **Scope**: Implemented Prompt 6 — Placement Readiness Score, including:
  - 100-point composite formula with fixed institutional weights: Resume 25, Projects 25, Mock Interview 20, GitHub 10, Coding Practice 10, LinkedIn 5, Co-curricular Achievements 5
  - Placement tier boundaries: 0–49 `Not ready`, 50–74 `Almost ready`, 75–100 `Placement ready`
  - Explicit missing component handling (contribute 0 points, status `"missing"`, no crash, no NaN)
  - Top 5 high-impact recommended actions ranked by points gained ($\Delta \text{Overall} = \Delta \text{Component} \times \frac{\text{Weight}}{100}$)
  - Timestamped snapshot history tracking (`ReadinessScoreSnapshot`) auto-updated on review completion
  - Frontend interactive SVG trend chart with 50 and 75 milestone threshold lines, animated score gauge, missing component banner, and 7 component breakdown cards
  - Formula documentation in `docs/architecture.md`
- **Tests Implemented**:
  - `backend/tests/test_readiness_score.py`: 15 test cases covering:
    - Formula hand-calculated cases: all 100 $\to$ 100, all 0 $\to$ 0, 3 mixed cases with explicit arithmetic
    - Boundary levels: 0, 49, 50, 74, 75, 100
    - Missing components without crash or NaN
    - Top 5 actions sorting and verification of claimed point gain
    - Progress tracking: review run increases score and appends history snapshot
    - API endpoints (`GET /current`, `POST /recalculate`, `GET /history`) and consent verification
- **Real End-to-End Checks**:
  - Live backend verification with `curl` hitting `/api/readiness/current` and `/api/readiness/history`
  - React UI verification in Chromium via browser subagent confirming score gauge (61/100), `Almost Ready` badge, SVG progression line chart (4 snapshots), missing components banner, and top 5 action cards
  - Full regression test suite: all 67 tests pass cleanly via `make test`
- **Status**: PASSED (0 failures)

---

## 2026-10-16: Module 07 — Mock Interview Simulator (Text Mode)

- **Scope**: Implemented Prompt 7 — Mock Interview Simulator (Text Mode), including:
  - Student-controlled 15-minute (standard, 5 questions) or 20-minute (comprehensive, 7 questions) interview simulations.
  - Resume-grounded question roadmap synthesizing technical questions, project deep-dives referencing actual student projects (*Readiness Copilot*, *Distributed Task Queue*), and STAR behavioral questions.
  - Adaptive follow-up interrogation based on candidate responses.
  - Strict countdown timer discipline auto-completing sessions and generating grades upon expiration.
  - Fixed 4-dimension per-answer rubric: `CRIT-TECH-DEPTH` (35 pts), `CRIT-CLARITY-COMM` (25 pts), `CRIT-GROUNDED-EXP` (25 pts), `CRIT-CRITICAL-THINK` (15 pts).
  - Arithmetic mean final scoring [0-100] feeding directly into the institutional Placement Readiness Score (Weight: 20 pts).
  - Permanent SQLite session persistence with full turn-by-turn replay transcripts, strengths, weak areas, and actionable tips.
  - Complete React UI (`MockInterviewPage.jsx`) with setup screen, real-time countdown timer bar, active conversation stream, and performance report with rubric bars.
  - Documented rubric in `docs/benchmarks.md`.
- **Tests Implemented**:
  - `backend/tests/test_interview.py`: 6 comprehensive test suites covering:
    - Question generation grounding: asserts candidate projects (*Readiness Copilot*, *Distributed Task Queue*) and skills (*Python*, *FastAPI*, *React*) are mentioned across technical, project deep-dive, and HR questions.
    - 3 scripted profiles (score ordering): strong answerer (81.0) > weak answerer (30.0) >= off-topic answerer (30.0), strong $\ge 75$, weak $\le 45$.
    - Timer expiration: short limit session auto-completes and yields valid score and feedback.
    - Edge cases: empty/whitespace answer rejected with HTTP 400, quitting mid-session cleanly grades completed answers, page refresh resumes active session via `GET /api/interview/active`.
    - Transcript persistence & readiness integration: saves full replayable transcript, shifts `mock_interview` from `missing` to `scored`, updating readiness score from 61 to 74.
    - Consent gate enforcement: unconsented session start rejected with HTTP 403.
- **Real End-to-End Checks**:
  - Live local Ollama (`smollm:135m`) multi-turn session executed and saved to `docs/samples/ollama_interview_transcript.json`.
  - Scripted benchmark session executed and saved to `docs/samples/scripted_interview_transcript.json`.
  - Full browser subagent automation in Chromium browser verifying setup, conversation flow, countdown timer, question answering, early completion, and replay report with score 66/100 and rubric progress bars.
  - Live backend verification with `curl` hitting `/api/readiness/current` showing `mock_interview` scored at 66/100 (13.2 weighted points), lifting overall score to 74.
  - Full monorepo regression test suite: all 73 tests pass cleanly via `make test`.
- **Status**: PASSED (0 failures)

---

## 2026-10-17: Module 07 — Mock Interview Simulator (Voice Mode: STT & TTS)

- **Scope**: Implemented Voice Mode for Mock Interview Simulator:
  - Speech-to-Text via `faster-whisper` (`tiny.en` on CPU, int8 quantization) with sub-second transcription latency.
  - Text-to-Speech via browser Web Speech API (`window.speechSynthesis`) with audio toggle (`#btn-toggle-tts`) and per-message replay buttons.
  - Graceful microphone denial fallback: catches `NotAllowedError`, automatically switches to Text Mode, and renders `#mic-denied-alert` warning banner while keeping text input fully functional.
  - Interactive UI with mode switcher (`#btn-toggle-mode`), glowing mic button (`#btn-start-voice-record`), animated audio visualizer bars, and recording timer.
  - Dedicated REST endpoints: `POST /api/interview/transcribe` and `POST /api/interview/{id}/voice-message`.
- **Tests Implemented**:
  - `backend/tests/test_voice.py`: 4 comprehensive tests covering:
    - `test_voice_service_transcription_accuracy`: Evaluates spoken test sentence with `faster-whisper`, achieving 100.0% accuracy (WER: 0.0).
    - `test_transcribe_api_endpoint`: Validates audio upload, transcription response, and empty audio 400 rejection.
    - `test_voice_message_interview_flow`: Full turn-by-turn spoken audio submission, rubric grading, and follow-up generation.
    - `test_voice_message_silent_audio_returns_clean_error`: Rejects silent audio with clean 400 error.
- **Real End-to-End Checks**:
  - Real 16kHz WAV spoken audio file transcribed and measured with `compute_transcription_accuracy` (100.0% accuracy).
  - Live backend verification with `curl` hitting `/api/interview/transcribe` and `/api/interview/{id}/voice-message`.
  - Browser subagent automation verifying mode selection, simulated mic denial fallback, warning banner rendering, and text answer submission.
  - Full monorepo regression test suite: all 77 tests pass cleanly via `make test`.
- **Status**: PASSED (0 failures)

---

## 2026-10-17: Module 08 — Job Discovery & Open Search Engine

- **Scope**: Implemented ethical job discovery engine from permitted public sources:
  - Authorized public APIs: Greenhouse public board API (`/v1/boards/{slug}/jobs?content=true`), Lever public API (`/v0/postings/{slug}?mode=json`), We Work Remotely RSS XML feed, Remotive feed API, and internal MSOT direct campus job postings.
  - Zero-scraping enforcement: Strict blocklist against scraping LinkedIn, Naukri, Internshala, Indeed. No student credentials stored or used.
  - Automated `robots.txt` verification via `urllib.robotparser` and domain-level rate limiting on `BaseFetcher`.
  - Boolean search query builder synthesizing student skills, target roles, and locations (e.g. `("React" OR "Next.js") AND (intern OR internship) AND (Bangalore OR remote)`).
  - Outbound "Open Search" deep link generator for LinkedIn, Naukri, Internshala, and Google Jobs.
  - Cross-source deduplicator normalizing company and title, aggregating sources and alternate URLs.
  - Multi-factor ranking engine (skills 50 pts, role 30 pts, readiness 15 pts, location 5 pts) generating explicit "Why this matched" reasons on every job card.
  - Interactive React UI (`JobDiscoveryPage.jsx`) featuring Outbound Launchpad, filter chips, configurable company slugs drawer, and rich job cards.
- **Tests Implemented**:
  - `backend/tests/test_job_discovery.py`: 11 comprehensive tests covering:
    - Boolean query generation for 3 profiles (frontend, backend, data) asserting exact strings.
    - Deduplication merging identical jobs from 2 sources (different URLs, same company/title).
    - Live source fetching: verified Greenhouse (Cloudflare: 435 jobs) and RSS feeds (38 jobs).
    - Fault isolation & graceful timeout handling: mocked timeout on one source retains healthy sources.
    - Ranking test with 20 diverse jobs for frontend profile: top 10 printed with match reasons.
    - Anti-scraping policy: asserts `DisallowedDomainError` on LinkedIn/Naukri and permits authorized APIs.
    - FastAPI endpoints: `/api/jobs/discover`, `/api/jobs/query`, `/api/jobs/sources`.
- **Regression Run**:
  - Full test suite: 88 passed, 0 failures across all 8 modules (`make test` / `pytest -v`).
  - Frontend production build: `npm run build` succeeded in 593ms (1933 modules transformed).
- **Status**: PASSED (0 failures, 88 total tests passing)

---

## [2026-10-17] Module 09: Application Tracker & MSOT Admin Job Board
- **Command**: `make test` & `./backend/venv/bin/python3 backend/tests/test_browser_tracker_flow.py`
- **Output**: 94 passed, 5 warnings in 341.33s (0:05:41); Playwright dual-session E2E: all 5 steps passed cleanly
- **Coverage**:
  - One-click "Open & Apply" opening external job portals in new tabs and triggering the tracking modal to log as `Applied` or `Saved`.
  - Application Tracker supporting date, company, role, link, notes, and 6 lifecycle statuses (`Saved`, `Applied`, `Shortlisted`, `Interview`, `Offer`, `Rejected`).
  - Interactive Table and Kanban views with drag/click status progression and historical audit timeline.
  - Movement detection (`has_movement` filter) and configurable inactivity follow-up reminders (`needs_followup` based on `last_status_change_at` and `followup_reminder_days`).
  - MSOT Admin Job Board portal with direct campus job and internship creation, benchmark eligibility gating (`min_readiness_score`, `required_skills`, `target_roles`), and pinning to the top of the job discovery feed for eligible students only.
  - Institutional applicant review drawer: admins view applicant readiness scores and profile skills, and promote candidate application statuses.
  - Strict RBAC: student accounts attempting to access admin endpoints are rejected with `HTTP 403 Forbidden`.
  - Duplicate protection: re-applying to an active application returns `HTTP 409 Conflict`.
- **Tests Implemented**:
  - `backend/tests/test_tracker_msot.py`: 5 comprehensive tests:
    - `test_e2e_admin_post_eligibility_apply_and_movement_flow`: Full admin post -> student eligibility filter -> apply -> admin promote -> student movement verification.
    - `test_permissions_student_cannot_post_or_view_applicants`: Confirms 403 Forbidden for students on admin endpoints.
    - `test_duplicate_application_handling`: Confirms 409 Conflict when submitting duplicate application.
    - `test_followup_reminders_fire_after_n_days`: Confirms inactivity reminders fire after $N$ days and reset on movement.
    - `test_tracker_crud_and_status_transitions`: Validates CRUD, status transitions, and timeline history.
  - `backend/tests/test_browser_tracker_flow.py`: Real dual-session browser automation executing all 5 user journeys in Chromium.
- **Regression Run**:
  - Full test suite: 94 passed, 0 failures across all 9 modules (`make test`).
  - Frontend production build: `npm run build` succeeded in 593ms (1934 modules transformed).
- **Status**: PASSED (0 failures, 94 total tests passing)

---

## [2026-10-17] Module 10: Challenge Verification, Load Testing & Final Submission
- **Command**: `pytest tests/ -v`, `make test`, `locust -f tests/locustfile.py ...`, and `python3 tests/verify_ollama_e2e.py`
- **Output**: 
  - Challenge test suite (`tests/`): 10 passed in 5.02s
  - Complete monorepo test suite: 104 passed in 72.61s
  - Locust 100-user load test: 100 concurrent users, 30s run time, 0.00% error rate, p50 = 95 ms, min = 11 ms
  - Offline Ollama verification: 100% completed locally with 0 API keys
- **Coverage**:
  - Repeatability verification (`tests/test_consistency.py`): 5 consecutive runs on Resume and LinkedIn profiles; verified delta = 0 (well within $\le \pm 3$ pts requirement).
  - GitHub & Live-link checks (`tests/test_github_livelinks.py`): Secret scanner detected planted AWS keys and RSA private keys with zero false positives on clean files; Playwright verified live link HTTP 200 and generated desktop/mobile screenshots.
  - Job matching & deduplication (`tests/test_job_matching.py`): Multi-profile ranking for Frontend (88), Backend (95), and Data Science (94); cross-source deduplication correctly merged Greenhouse and Lever postings.
  - End-to-end recruitment lifecycle (`tests/test_tracker_msot_e2e.py`): Admin job creation with eligibility gating $\to$ student eligibility filtering $\to$ application logging $\to$ admin applicant triage $\to$ promotion to `Interview` $\to$ movement detection.
  - GDPR privacy & cascade deletion (`tests/test_privacy_deletion.py`): Explicit consent gate enforced; physical uploaded file verified on disk; one-click profile wipe verified; permanent account deletion verified cascade deleting all database rows and unlinking all files from disk; tenant isolation verified.
  - High-concurrency load test (`tests/locustfile.py`): Simulated 100 concurrent student users; recorded 0.00% error rate, p50 = 95 ms across core reading endpoints (`/api/health`, `/api/profile/me`, `/api/readiness/current`, `/api/readiness/history`, `/api/tracker/applications`).
  - Token accounting & API cost model (`tests/calculate_token_cost.py`): Measured 1,694 total student journey tokens (1,137 prompt, 557 completion); calculated cost per student: Ollama ($0.00), Gemini 1.5 Flash ($0.00025), OpenAI gpt-4o-mini ($0.00050), Claude 3.5 Haiku ($0.00314), OpenAI gpt-4o ($0.00841).
  - Offline local-first execution (`tests/verify_ollama_e2e.py`): Executed complete student lifecycle with Ollama (`smollm:135m`) with zero paid API keys: resume upload $\to$ review (78/100) $\to$ mock interview (72/100) $\to$ placement readiness score calculation (44/100) with 7-dimension breakdown.
  - Clean clone check (`scratch/fresh_verification`): Followed README strictly (`make setup-backend`, `make seed`, `make test`) in a clean cloned folder.
  - Database seeding (`backend/scripts/seed_data.py` / `make seed`): Created Admin (`admin@msot.edu` / `admin123`), Demo Student (`student@msot.edu` / `student123`), and 5 sample students across Tiers 1-3.
- **Status**: PASSED (0 failures, 104 total tests passing across all 10 modules)

