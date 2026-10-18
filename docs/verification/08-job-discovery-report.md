# Verification Report: Module 08 Job Discovery from Permitted Sources

**Date**: 2026-10-17  
**Module**: Module 08 — Job Discovery & Open Search Engine  
**Status**: PASSED (0 failures, 88 total tests passed)

---

## 1. Commands Run and Real Terminal Outputs

### A. Dedicated Module 08 Test Suite (`backend/tests/test_job_discovery.py`)
```bash
backend/venv/bin/pytest backend/tests/test_job_discovery.py -v -s
```
**Output**:
```text
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Users/nakulmirai/Mirai Project/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/nakulmirai/Mirai Project/backend
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 11 items                                                             

backend/tests/test_job_discovery.py::test_query_generation_frontend_profile PASSED
backend/tests/test_job_discovery.py::test_query_generation_backend_profile PASSED
backend/tests/test_job_discovery.py::test_query_generation_data_profile PASSED
backend/tests/test_job_discovery.py::test_deduplication_merges_cross_source_duplicates PASSED
backend/tests/test_job_discovery.py::test_live_source_fetching_and_counts 
[LIVE SOURCE CHECK] Greenhouse (Cloudflare) count: 435
[LIVE SOURCE CHECK] RSS Feeds count: 38
PASSED
backend/tests/test_job_discovery.py::test_graceful_handling_when_source_is_down PASSED
backend/tests/test_job_discovery.py::test_ranking_20_jobs_for_frontend_profile 
=======================================================
 TOP 10 RANKED JOBS FOR FRONTEND PROFILE (READINESS 85)
=======================================================

#1 [80% Match] Vercel - Senior Frontend Engineer (Remote)
   Matched Skills: ['React', 'Next.js', 'TypeScript']
   Why it matched:
     • Matched 3 verified profile skill(s): React, Next.js, TypeScript
     • Job title aligns directly with your target role 'Frontend Engineer'
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Remote) matches preferred work flexibility

#2 [70% Match] Atlassian - Associate Frontend Engineer (Bangalore)
   Matched Skills: ['React', 'TypeScript']
   Why it matched:
     • Matched 2 verified profile skill(s): React, TypeScript
     • Job title aligns directly with your target role 'Frontend Engineer'
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Bangalore) matches preferred work flexibility

#3 [70% Match] GitLab - Frontend Software Engineer (Remote)
   Matched Skills: ['React', 'TypeScript']
   Why it matched:
     • Matched 2 verified profile skill(s): React, TypeScript
     • Job title aligns directly with your target role 'Frontend Engineer'
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Remote) matches preferred work flexibility

#4 [63% Match] Coinbase - React Native Mobile Engineer (Remote)
   Matched Skills: ['React', 'TypeScript']
   Why it matched:
     • Matched 2 verified profile skill(s): React, TypeScript
     • Shares role domain tokens: engineer
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Remote) matches preferred work flexibility

#5 [60% Match] Shopify - Junior Web Developer (Bangalore)
   Matched Skills: ['React']
   Why it matched:
     • Matched 1 verified profile skill(s): React
     • Job title aligns directly with your target role 'Web Developer'
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Bangalore) matches preferred work flexibility

#6 [58% Match] Stripe - Frontend Developer Intern (Bangalore)
   Matched Skills: ['React', 'Tailwind CSS']
   Why it matched:
     • Matched 2 verified profile skill(s): React, Tailwind CSS
     • Shares role domain tokens: frontend
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Bangalore) matches preferred work flexibility

#7 [58% Match] Figma - UI/UX Frontend Specialist (Remote)
   Matched Skills: ['Next.js', 'Tailwind CSS']
   Why it matched:
     • Matched 2 verified profile skill(s): Next.js, Tailwind CSS
     • Shares role domain tokens: frontend
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Remote) matches preferred work flexibility

#8 [53% Match] Airbnb - Full Stack Engineer (React/Node) (Remote)
   Matched Skills: ['React']
   Why it matched:
     • Matched 1 verified profile skill(s): React
     • Shares role domain tokens: engineer
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Remote) matches preferred work flexibility

#9 [38% Match] Dropbox - Backend Python Engineer (Remote)
   Matched Skills: []
   Why it matched:
     • Shares role domain tokens: engineer
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
     • Location (Remote) matches preferred work flexibility

#10 [33% Match] Snowflake - Data Platform Engineer (San Francisco)
   Matched Skills: []
   Why it matched:
     • Shares role domain tokens: engineer
     • Your readiness score (85/100 - Placement Ready) satisfies benchmark
=======================================================

PASSED
backend/tests/test_job_discovery.py::test_anti_scraping_and_robots_txt_enforcement PASSED
backend/tests/test_job_discovery.py::test_api_jobs_discover_endpoint PASSED
backend/tests/test_job_discovery.py::test_api_jobs_query_endpoint PASSED
backend/tests/test_job_discovery.py::test_api_jobs_sources_endpoint PASSED

======================= 11 passed, 5 warnings in 36.79s ========================
```

---

### B. Live API Curl Checks
```bash
# 1. Inspect Sources Endpoint
curl -s http://localhost:8000/api/jobs/sources
```
**Output**:
```json
{
  "greenhouse": {
    "slugs": ["cloudflare", "gitlab", "stripe", "figma", "automattic"],
    "endpoint_template": "https://boards-api.greenhouse.io/v1/boards/{slug}/jobs"
  },
  "lever": {
    "slugs": ["netflix", "palantir", "coursera", "atlassian"],
    "endpoint_template": "https://api.lever.co/v0/postings/{slug}?mode=json"
  },
  "rss": {
    "feeds": ["WeWorkRemotely", "Remotive"]
  },
  "internal_msot": {
    "description": "Direct institutional job postings from MSOT placement staff"
  }
}
```

```bash
# 2. Query Generation Endpoint
curl -s -X POST http://localhost:8000/api/jobs/query \
  -H "Content-Type: application/json" \
  -d '{"skills":["React","Next.js"],"job_types":["intern","internship"],"locations":["Bangalore","remote"]}'
```
**Output**:
```json
{
  "boolean_query": "(\"React\" OR \"Next.js\") AND (intern OR internship) AND (Bangalore OR remote)",
  "open_search_links": {
    "linkedin": "https://www.linkedin.com/jobs/search/?keywords=%28%22React%22+OR+%22Next.js%22%29+AND+%28intern+OR+internship%29+AND+%28Bangalore+OR+remote%29&location=Bangalore",
    "naukri": "https://www.naukri.com/jobs-in-india?k=%28%22React%22+OR+%22Next.js%22%29+AND+%28intern+OR+internship%29+AND+%28Bangalore+OR+remote%29",
    "internshala": "https://internshala.com/internships/keywords-React+OR+Next.js/",
    "google": "https://www.google.com/search?q=%28%22React%22+OR+%22Next.js%22%29+AND+%28intern+OR+internship%29+AND+%28Bangalore+OR+remote%29+jobs"
  }
}
```

---

### C. Full Regression Test Run Across All Modules (`backend/venv/bin/pytest -v`)
```bash
backend/venv/bin/pytest -v
```
**Output**:
```text
================== 88 passed, 5 warnings in 69.88s (0:01:09) ===================
```

---

### D. Production Bundle Compilation (`npm run build`)
```bash
cd frontend && npm run build
```
**Output**:
```text
vite v8.3.4 building client environment for production...
✓ 1933 modules transformed.
rendering chunks (1)...computing gzip size...
dist/index.html                   0.45 kB │ gzip:   0.29 kB
dist/assets/index-yQHiDtQ2.css   47.29 kB │ gzip:   8.56 kB
dist/assets/index-BjNefc3D.js   442.75 kB │ gzip: 114.29 kB
✓ built in 593ms
```

---

## 2. Requirement Verification Matrix

| Prompt 8 Requirement | Verification Method | Status | Real Output / Evidence |
| :--- | :--- | :---: | :--- |
| **1. Unit-test boolean query generation for 3 profiles** | `test_query_generation_frontend_profile`, `test_query_generation_backend_profile`, `test_query_generation_data_profile` | **PASSED** | Exact boolean strings validated: `("React" OR "Next.js") AND (intern OR internship) AND (Bangalore OR remote)`, `("Python" OR "FastAPI") AND (intern OR internship) AND (Bangalore OR remote)`, `("Python" OR "SQL") AND (intern OR internship) AND (Bangalore OR remote)` |
| **2. Unit-test deduplication across 2 sources** | `test_deduplication_merges_cross_source_duplicates` | **PASSED** | Merged Greenhouse and RSS records for Cloudflare into 1 canonical item with both sources and URLs captured. |
| **3. Live fetching & graceful timeout handling** | `test_live_source_fetching_and_counts`, `test_graceful_handling_when_source_is_down` | **PASSED** | Greenhouse returned 435 live jobs; RSS returned 38 jobs. Mocked timeout on Greenhouse degraded gracefully while returning healthy records. |
| **4. Test ranking with 20 jobs for test profile** | `test_ranking_20_jobs_for_frontend_profile` | **PASSED** | Top 10 jobs printed with match percentages (80% down to 33%) and why-it-matched reasons. Top 3 are frontend/React roles. |
| **5. Anti-scraping grep audit & robots.txt check** | `test_anti_scraping_and_robots_txt_enforcement` & ripgrep | **PASSED** | Requests to LinkedIn, Naukri, Internshala, Indeed immediately throw `DisallowedDomainError`. No scraping logic in codebase. `robots.txt` verification active on `BaseFetcher`. |
| **6. Every job card in UI shows "why it matched"** | Inspect `JobDiscoveryPage.jsx` & JSX build | **PASSED** | Every card prominently features `<CheckCircle2 /> Why this opportunity matched your profile` with explicit reasons and skill tags. |
| **7. Re-run all earlier tests** | Full pytest run across all 8 modules | **PASSED** | All 88 tests in the repository passed with 0 failures. |

---

## 3. What Could Not Be Verified and Why

- **Automated Browser Subagent Click Flow**: The automated browser subagent encountered an environment-level CDP protocol error (`playwright: Protocol error (Browser.setDownloadBehavior): Browser context management is not supported`).
- **Mitigation**: The entire frontend codebase was validated via `npm run build` (all 1933 modules built cleanly in 593ms), and all underlying endpoints (`/api/jobs/discover`, `/api/jobs/query`, `/api/jobs/sources`) were verified using live HTTP curl requests and FastAPI test client assertions.
