# Module 08: Job Discovery & Open Search Engine

## 1. What the Module Does

Module 08 delivers an ethical, privacy-first placement job discovery engine and outbound search generator for MSOT students:
1. **Permitted Public Ingestion Only**:
   - Ingests public job listings from **Greenhouse Public Board APIs** (`https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`) for configured company slugs.
   - Ingests public job listings from **Lever Public Board APIs** (`https://api.lever.co/v0/postings/{slug}?mode=json`) for configured company slugs.
   - Ingests syndicated remote opportunities from **RSS XML feeds** (We Work Remotely) and open feed APIs (Remotive).
   - Ingests internal direct campus job postings created in the local SQLite database by MSOT placement staff.
2. **Zero-Scraping Policy & Student Privacy**:
   - Strictly enforces a complete prohibition against scraping walled gardens (LinkedIn, Naukri, Internshala, Indeed, Glassdoor).
   - Never requests, stores, or uses student login credentials or browser cookies for career platforms.
   - For all generic web fetches, automatically verifies `robots.txt` compliance using standard Python `urllib.robotparser` and enforces domain-level rate limiting and request delays.
3. **Boolean Search Query & Outbound Deep Link Generator**:
   - Compiles exact, standardized Boolean search strings from the student's declared skills and target role (e.g., `("React" OR "Next.js") AND (intern OR internship) AND (Bangalore OR remote)`).
   - Formats outbound deep search links for LinkedIn, Naukri, Internshala, and Google Jobs that students can launch manually in their own browser.
4. **Cross-Source Deduplication**:
   - Normalizes company names and job titles across multiple boards (handling punctuation, legal suffixes like Inc/LLC, and bracketed tags like `[Remote]`).
   - Merges identical job postings that appear on multiple sources into a single canonical posting with aggregated source tags, primary/alternate URLs, and the most descriptive job content.
5. **Deterministic Profile & Readiness Score Matching**:
   - Scores job alignment on a 0–100 scale combining:
     - Verified profile skill overlap (0–50 points)
     - Target role and title alignment (0–30 points)
     - Readiness score benchmark tier fit (0–15 points)
     - Location and remote work preference (0–5 points)
   - Decorates every job card with explicit, human-readable match reasons (e.g. *"Matched 3 verified profile skill(s): React, Next.js, TypeScript"*, *"Job title aligns directly with your target role 'Frontend Engineer'"*, *"Your readiness score (85/100 - Placement Ready) satisfies benchmark"*).
6. **Configurable Ingestion Slugs**:
   - Provides a settings drawer where students and staff can inspect active company slugs and test live connectivity with latency reporting.

---

## 2. How It Works: Step-by-Step Flow

```
[Student in React UI / Client]
       │
       ├─► 1. Trigger Discovery:
       │      Student visits Jobs tab in JobDiscoveryPage.jsx
       │      GET /api/jobs/discover (backend/app/routers/jobs.py)
       │        ├─► Extracts verified profile skills, target roles, and readiness score
       │        └─► Calls job_discovery_service.discover_jobs()
       │
       ├─► 2. Query & Outbound Deep Link Synthesis:
       │      build_boolean_query() & build_open_search_links()
       │      (backend/app/services/job_discovery/query_builder.py)
       │        ├─► Formats skills clause: ("React" OR "Next.js")
       │        ├─► Formats role type: (intern OR internship)
       │        ├─► Formats location: (Bangalore OR remote)
       │        └─► Generates outbound URLs for LinkedIn, Naukri, Internshala, Google
       │
       ├─► 3. Permitted Multi-Source Ingestion:
       │      fetch_all_raw_jobs() (backend/app/services/job_discovery/discovery_service.py)
       │        ├─► GreenhouseFetcher.fetch_jobs() (Cloudflare, GitLab, Stripe, Figma, Automattic)
       │        ├─► LeverFetcher.fetch_jobs() (Netflix, Palantir, Coursera, Atlassian)
       │        ├─► RSSFeedFetcher.fetch_jobs() (We Work Remotely RSS, Remotive API)
       │        ├─► MSOT DB Query: models.Job (active campus postings)
       │        └─► robots_checker.py validates domain permissions & robots.txt
       │
       ├─► 4. Cross-Source Deduplication:
       │      deduplicate_jobs() (backend/app/services/job_discovery/deduplicator.py)
       │        ├─► Normalizes company name (strips Inc, LLC, Corp) & title
       │        ├─► Combines sources, merges URLs into canonical & alternate_urls
       │        └─► Retains longest description and richest location
       │
       ├─► 5. Multi-Factor Ranking & Match Reasoning:
       │      rank_jobs() (backend/app/services/job_discovery/ranker.py)
       │        ├─► Computes skill overlap (0-50 pts) & extracts matched/missing skills
       │        ├─► Computes role title alignment (0-30 pts)
       │        ├─► Factors readiness score (0-15 pts) & location (0-5 pts)
       │        └─► Generates explicit bullet points explaining why the job matched
       │
       └─► 6. Frontend Presentation:
              JobDiscoveryPage.jsx displays:
                - Outbound Open Search Launchpad with copyable Boolean string
                - LinkedIn / Naukri / Internshala / Google launch buttons
                - Keyword and source filter chips
                - Job cards with match score badge and "Why this matched" breakdown
```

### Exact Files and Functions

1. **`backend/app/services/job_discovery/robots_checker.py`**:
   - `RobotsChecker`: Singleton class that caches site `robots.txt` using Python's standard `urllib.robotparser.RobotFileParser`.
   - `is_disallowed_domain(url)`: Rejects walled gardens (`linkedin.com`, `naukri.com`, `internshala.com`, `indeed.com`).
   - `check_allowed(url)`: Raises `DisallowedDomainError` for blocklisted domains and checks `robots.txt` for generic URLs.
   - `wait_for_rate_limit(url)`: Throttles requests per host to prevent abusive crawling.
2. **`backend/app/services/job_discovery/query_builder.py`**:
   - `build_boolean_query(skills, job_types, locations, target_roles)`: Formats deterministic Boolean search strings.
   - `build_open_search_links(query, location, primary_role)`: URL-encodes queries into outbound deep links for LinkedIn, Naukri, Internshala, and Google Jobs.
3. **`backend/app/services/job_discovery/fetchers/base.py`**:
   - `BaseFetcher`: Abstract base class enforcing robots.txt checks, rate limiting, and 10.0s HTTP timeout bounds.
4. **`backend/app/services/job_discovery/fetchers/greenhouse.py`**:
   - `GreenhouseFetcher`: Fetches public jobs from `https://boards-api.greenhouse.io/v1/boards/{slug}/jobs?content=true`.
5. **`backend/app/services/job_discovery/fetchers/lever.py`**:
   - `LeverFetcher`: Fetches public postings from `https://api.lever.co/v0/postings/{slug}?mode=json`.
6. **`backend/app/services/job_discovery/fetchers/rss.py`**:
   - `RSSFeedFetcher`: Parses XML feeds from We Work Remotely and JSON feeds from Remotive.
7. **`backend/app/services/job_discovery/deduplicator.py`**:
   - `deduplicate_jobs(jobs)`: Canonical key hashing (`normalize_company::normalize_title`), merges duplicate records, aggregates sources, and preserves alternate URLs.
8. **`backend/app/services/job_discovery/ranker.py`**:
   - `score_job_match(job, skills, target_roles, readiness_score, locations)`: Computes 0–100 match score and generates human-readable why-it-matched reasons.
   - `rank_jobs(jobs, ...)`: Decorates postings with scores and sorts them in descending relevance order.
9. **`backend/app/services/job_discovery/discovery_service.py`**:
   - `JobDiscoveryService`: Coordinates parallel ingestion, in-memory caching (5-minute TTL), deduplication, ranking, and search query generation.
10. **`backend/app/routers/jobs.py`**:
    - `GET /api/jobs/discover`: Main discovery endpoint.
    - `POST /api/jobs/query`: Query generation endpoint.
    - `GET /api/jobs/sources`: Source inspection endpoint.
    - `POST /api/jobs/sources/test`: Source diagnostic endpoint.
11. **`frontend/src/pages/JobDiscoveryPage.jsx`**:
    - Complete React UI featuring Outbound Launchpad, filter chips, configurable company slugs drawer, and job cards with match reason breakdown.

---

## 3. Key Design Decisions and Rejected Alternatives

| Decision | Chosen Approach | Rejected Alternative | Rationale |
| :--- | :--- | :--- | :--- |
| **Ingestion Protocol** | Public board APIs (Greenhouse/Lever) & Syndication (RSS) | Scraping LinkedIn, Naukri, or Indeed directly | Career platforms have aggressive anti-bot protections, and scraping them violates Terms of Service and user privacy. Public APIs are stable, fast, and 100% legal. |
| **Walled Garden Access** | Outbound "Open Search" launchpad with pre-compiled Boolean search links | Headless browser scraping using student login cookies | Storing student credentials introduces massive security and credential-theft risks. Outbound links empower students to view live search results with one click in their own authenticated browser session. |
| **Deduplication Key** | Normalized company + sanitized title (`strip_suffixes(company)::clean(title)`) | URL-only or exact ID matching | The same job is frequently cross-posted to Greenhouse, We Work Remotely, and LinkedIn with different URLs. Normalizing company names and titles catches cross-platform duplicates. |
| **Match Scoring Model** | Deterministic multi-factor code algorithm (skills + role + readiness + location) | Unbounded LLM prompt evaluating every job | Calling an LLM for 400+ job listings would take minutes and incur high compute costs. Pure code evaluation runs in milliseconds, is fully deterministic, and guarantees repeated consistency. |
| **Fault Isolation** | `asyncio.gather(*tasks, return_exceptions=True)` with 10s timeout | Sequential synchronous fetching | Network timeouts on one company board or RSS feed must never hang or crash the search response for other sources. |

---

## 4. Shortcuts or Faked Parts

- **No Faked Data**: All job postings originate from real, live public APIs (e.g. Cloudflare, GitLab on Greenhouse; Palantir on Lever; We Work Remotely RSS) and MSOT database records.
- **In-Memory Cache**: Discovered jobs are cached in-memory with a 5-minute TTL to reduce external network load. In a multi-worker production cluster, this would be backed by Redis or a scheduled background worker.

---

## 5. Verify It Yourself

You can verify all features manually in 4 simple steps:

### Step 1: Verify Boolean Query Generation via API
```bash
curl -s -X POST http://localhost:8000/api/jobs/query \
  -H "Content-Type: application/json" \
  -d '{"skills":["React","Next.js"],"job_types":["intern","internship"],"locations":["Bangalore","remote"]}' | jq .
```
**Expected Result**:
Returns exact boolean string: `("React" OR "Next.js") AND (intern OR internship) AND (Bangalore OR remote)` alongside pre-filled search URLs for LinkedIn, Naukri, Internshala, and Google Jobs.

### Step 2: Verify Anti-Scraping Blocklist Enforcement
```bash
PYTHONPATH=backend backend/venv/bin/python3 -c "
from app.services.job_discovery.robots_checker import robots_checker, DisallowedDomainError
try:
    robots_checker.check_allowed('https://www.linkedin.com/jobs')
    print('Failed - allowed disallowed domain')
except DisallowedDomainError:
    print('Success: LinkedIn scraping successfully blocked by policy')
"
```
**Expected Result**:
Prints `Success: LinkedIn scraping successfully blocked by policy`.

### Step 3: Run Full Job Discovery Test Suite
```bash
backend/venv/bin/pytest backend/tests/test_job_discovery.py -v -s
```
**Expected Result**:
All 11 tests pass, printing real live job counts from Greenhouse and RSS feeds, and printing the top 10 ranked jobs with match reasons.

### Step 4: Verify Frontend Build
```bash
cd frontend && npm run build
```
**Expected Result**:
Build completes in under 1 second with 0 errors (`dist/index.html` generated).
