from __future__ import annotations
import pytest
import asyncio
from unittest.mock import patch, AsyncMock
import httpx
from fastapi.testclient import TestClient

from app.main import app
from app.services.job_discovery.query_builder import (
    build_boolean_query,
    build_open_search_links,
)
from app.services.job_discovery.deduplicator import (
    deduplicate_jobs,
    normalize_company,
    normalize_title,
)
from app.services.job_discovery.ranker import rank_jobs, score_job_match
from app.services.job_discovery.robots_checker import (
    robots_checker,
    DisallowedDomainError,
)
from app.services.job_discovery.discovery_service import JobDiscoveryService
from app.services.job_discovery.fetchers.greenhouse import GreenhouseFetcher
from app.services.job_discovery.fetchers.lever import LeverFetcher
from app.services.job_discovery.fetchers.rss import RSSFeedFetcher

client = TestClient(app)


# =========================================================================
# 1. Unit-test Query Generation for 3 Profiles (Frontend, Backend, Data)
# =========================================================================

def test_query_generation_frontend_profile():
    """Verify exact boolean query for Frontend student profile."""
    skills = ["React", "Next.js"]
    job_types = ["intern", "internship"]
    locations = ["Bangalore", "remote"]

    query = build_boolean_query(skills=skills, job_types=job_types, locations=locations)
    expected = '("React" OR "Next.js") AND (intern OR internship) AND (Bangalore OR remote)'
    assert query == expected

    links = build_open_search_links(query, location="Bangalore, India", primary_role="Frontend Engineer")
    assert "linkedin.com/jobs/search" in links["linkedin"]
    assert "naukri.com/jobs-in-india" in links["naukri"]
    assert "internshala.com/internships" in links["internshala"]
    assert "google.com/search" in links["google"]


def test_query_generation_backend_profile():
    """Verify exact boolean query for Backend student profile."""
    skills = ["Python", "FastAPI"]
    job_types = ["intern", "internship"]
    locations = ["Bangalore", "remote"]

    query = build_boolean_query(skills=skills, job_types=job_types, locations=locations)
    expected = '("Python" OR "FastAPI") AND (intern OR internship) AND (Bangalore OR remote)'
    assert query == expected


def test_query_generation_data_profile():
    """Verify exact boolean query for Data student profile."""
    skills = ["Python", "SQL"]
    job_types = ["intern", "internship"]
    locations = ["Bangalore", "remote"]

    query = build_boolean_query(skills=skills, job_types=job_types, locations=locations)
    expected = '("Python" OR "SQL") AND (intern OR internship) AND (Bangalore OR remote)'
    assert query == expected


# =========================================================================
# 2. Unit-test Deduplication Across 2 Sources
# =========================================================================

def test_deduplication_merges_cross_source_duplicates():
    """
    Test dedupe with the same job from 2 sources (different URLs, same company/title)
    and confirm it merges them into 1 canonical record.
    """
    job_gh = {
        "id": "gh_101",
        "title": "Frontend Engineer [Remote]",
        "company": "Cloudflare, Inc.",
        "location": "Remote / Unspecified",
        "url": "https://boards.greenhouse.io/cloudflare/jobs/101",
        "description": "Short brief from Greenhouse",
        "source": "greenhouse",
        "metadata": {"gh_id": 101},
    }

    job_rss = {
        "id": "wwr_202",
        "title": "Frontend Engineer",
        "company": "Cloudflare",
        "location": "Remote - Worldwide",
        "url": "https://weworkremotely.com/jobs/cloudflare-frontend-engineer",
        "description": "Comprehensive and longer job description with full skill requirements",
        "source": "rss_weworkremotely",
        "metadata": {"wwr_id": 202},
    }

    raw_jobs = [job_gh, job_rss]
    merged = deduplicate_jobs(raw_jobs)

    # Must merge down to 1 job
    assert len(merged) == 1
    canonical = merged[0]

    # Must aggregate sources
    assert "greenhouse" in canonical["sources"]
    assert "rss_weworkremotely" in canonical["sources"]

    # Must capture primary URL and alternate URL
    assert canonical["url"] == "https://boards.greenhouse.io/cloudflare/jobs/101"
    assert "https://weworkremotely.com/jobs/cloudflare-frontend-engineer" in canonical["alternate_urls"]

    # Must preserve the richer description and specific location
    assert "Comprehensive and longer" in canonical["description"]
    assert "Worldwide" in canonical["location"]


# =========================================================================
# 3. Live Sources Fetching & Graceful Timeout Handling
# =========================================================================

@pytest.mark.asyncio
async def test_live_source_fetching_and_counts():
    """
    Fetch real jobs from at least 2 live sources (Greenhouse & RSS) and print counts.
    """
    # Source 1: Greenhouse public board (e.g. Cloudflare or GitLab)
    gh_fetcher = GreenhouseFetcher(company_slugs=["cloudflare"], timeout_seconds=10.0)
    gh_jobs = await gh_fetcher.fetch_jobs()

    # Source 2: WeWorkRemotely RSS feed
    rss_fetcher = RSSFeedFetcher(timeout_seconds=10.0)
    rss_jobs = await rss_fetcher.fetch_jobs()

    print(f"\n[LIVE SOURCE CHECK] Greenhouse (Cloudflare) count: {len(gh_jobs)}")
    print(f"[LIVE SOURCE CHECK] RSS Feeds count: {len(rss_jobs)}")

    # Assert at least one live source returns postings or gracefully handled
    total_live = len(gh_jobs) + len(rss_jobs)
    assert total_live > 0, "Expected at least one live source to return postings"


@pytest.mark.asyncio
async def test_graceful_handling_when_source_is_down():
    """
    Confirm graceful degradation when one source times out or fails (mocked timeout).
    The orchestrator should NOT raise an error and should return remaining sources.
    """
    service = JobDiscoveryService()

    # Mock Greenhouse to simulate a network timeout
    with patch.object(GreenhouseFetcher, "fetch_jobs", new_callable=AsyncMock) as mock_gh:
        mock_gh.side_effect = httpx.TimeoutException("Greenhouse connection timed out after 10.0s")

        # Mock Lever to return an isolated empty list
        with patch.object(LeverFetcher, "fetch_jobs", new_callable=AsyncMock) as mock_lv:
            mock_lv.return_value = []

            # Mock RSS to return 1 healthy job
            with patch.object(RSSFeedFetcher, "fetch_jobs", new_callable=AsyncMock) as mock_rss:
                mock_rss.return_value = [
                    {
                        "id": "mock_rss_1",
                        "title": "Junior Python Developer",
                        "company": "Healthy Co",
                        "location": "Remote",
                        "url": "https://example.com/job1",
                        "description": "Python, FastAPI",
                        "source": "rss_weworkremotely",
                    }
                ]

                # Fetch raw jobs
                raw = await service.fetch_all_raw_jobs(force_refresh=True)

                # Assert no crash and healthy jobs were preserved
                assert len(raw) == 1
                assert raw[0]["company"] == "Healthy Co"


# =========================================================================
# 4. Ranking Verification with 20 Jobs for One Test Profile
# =========================================================================

def test_ranking_20_jobs_for_frontend_profile():
    """
    Test ranking with 20 diverse jobs for a Frontend student profile.
    Asserts top results align with frontend technologies and prints top 10 with match reasons.
    """
    test_skills = ["React", "Next.js", "TypeScript", "Tailwind CSS"]
    test_target_roles = ["Frontend Engineer", "Web Developer"]
    test_readiness_score = 85

    twenty_jobs = [
        {"id": "j1", "title": "Senior Frontend Engineer", "company": "Vercel", "location": "Remote", "description": "React, Next.js, TypeScript architecture"},
        {"id": "j2", "title": "Frontend Developer Intern", "company": "Stripe", "location": "Bangalore", "description": "React, Tailwind CSS, JavaScript UI development"},
        {"id": "j3", "title": "Full Stack Engineer (React/Node)", "company": "Airbnb", "location": "Remote", "description": "React frontend, Node.js backend"},
        {"id": "j4", "title": "React Native Mobile Engineer", "company": "Coinbase", "location": "Remote", "description": "React, TypeScript mobile apps"},
        {"id": "j5", "title": "Junior Web Developer", "company": "Shopify", "location": "Bangalore", "description": "HTML, CSS, JavaScript, React components"},
        {"id": "j6", "title": "UI/UX Frontend Specialist", "company": "Figma", "location": "Remote", "description": "Tailwind CSS, Next.js, design systems"},
        {"id": "j7", "title": "Backend Python Engineer", "company": "Dropbox", "location": "Remote", "description": "Python, Django, PostgreSQL, Redis"},
        {"id": "j8", "title": "Data Platform Engineer", "company": "Snowflake", "location": "San Francisco", "description": "SQL, Spark, Python data pipelines"},
        {"id": "j9", "title": "Machine Learning Intern", "company": "OpenAI", "location": "Remote", "description": "PyTorch, Python, LLM evaluation"},
        {"id": "j10", "title": "DevOps / Infrastructure Engineer", "company": "Cloudflare", "location": "Austin", "description": "Kubernetes, Docker, Go, Terraform"},
        {"id": "j11", "title": "Associate Frontend Engineer", "company": "Atlassian", "location": "Bangalore", "description": "TypeScript, React, modern web standards"},
        {"id": "j12", "title": "iOS Developer", "company": "Apple", "location": "Cupertino", "description": "Swift, SwiftUI, iOS SDK"},
        {"id": "j13", "title": "Embedded Systems Engineer", "company": "Tesla", "location": "Palo Alto", "description": "C++, RTOS, firmware"},
        {"id": "j14", "title": "Staff Backend Architect", "company": "Netflix", "location": "Los Gatos", "description": "Java, Spring Boot, distributed microservices"},
        {"id": "j15", "title": "Frontend Software Engineer", "company": "GitLab", "location": "Remote", "description": "Vue, React, TypeScript, frontend testing"},
        {"id": "j16", "title": "Security Analyst", "company": "CrowdStrike", "location": "Remote", "description": "Threat hunting, SOC, SIEM"},
        {"id": "j17", "title": "Sales Development Representative", "company": "Salesforce", "location": "Chicago", "description": "Outbound pipeline, CRM, lead qualification"},
        {"id": "j18", "title": "Corporate Accountant", "company": "KPMG", "location": "New York", "description": "Financial reporting, GAAP auditing"},
        {"id": "j19", "title": "Product Marketing Manager", "company": "HubSpot", "location": "Boston", "description": "Go-to-market strategy, product positioning"},
        {"id": "j20", "title": "Executive Assistant", "company": "Google", "location": "Mountain View", "description": "Calendar management, travel coordination"},
    ]

    ranked = rank_jobs(
        jobs=twenty_jobs,
        skills=test_skills,
        target_roles=test_target_roles,
        readiness_score=test_readiness_score,
        preferred_locations=["remote", "bangalore"],
    )

    assert len(ranked) == 20

    # The top 3 ranked jobs must be frontend-related
    top_3_titles = [r["title"].lower() for r in ranked[:3]]
    for t in top_3_titles:
        assert "frontend" in t or "react" in t or "web" in t

    # Print top 10 with match reasons for manual verification
    print("\n=======================================================")
    print(" TOP 10 RANKED JOBS FOR FRONTEND PROFILE (READINESS 85)")
    print("=======================================================")
    for idx, r in enumerate(ranked[:10], start=1):
        print(f"\n#{idx} [{r['match_score']}% Match] {r['company']} - {r['title']} ({r['location']})")
        print(f"   Matched Skills: {r['matched_skills']}")
        print(f"   Why it matched:")
        for reason in r["match_reasons"]:
            print(f"     • {reason}")
    print("=======================================================\n")


# =========================================================================
# 5. Security & Anti-Scraping Grep Audit Verification
# =========================================================================

def test_anti_scraping_and_robots_txt_enforcement():
    """
    Assert that disallowed sites raise DisallowedDomainError and robots.txt check is active.
    """
    # 1. Disallowed sites must immediately raise DisallowedDomainError
    disallowed_urls = [
        "https://www.linkedin.com/jobs/search?keywords=react",
        "https://www.naukri.com/react-jobs",
        "https://internshala.com/internships",
        "https://www.indeed.com/jobs?q=frontend",
    ]
    for url in disallowed_urls:
        assert robots_checker.is_disallowed_domain(url) is True
        with pytest.raises(DisallowedDomainError):
            robots_checker.check_allowed(url)

    # 2. Permitted APIs must pass check
    assert robots_checker.is_disallowed_domain("https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs") is False
    assert robots_checker.check_allowed("https://boards-api.greenhouse.io/v1/boards/cloudflare/jobs") is True


# =========================================================================
# 6. FastAPI Router Endpoints Test
# =========================================================================

def test_api_jobs_discover_endpoint():
    """Test GET /api/jobs/discover endpoint returns formatted response."""
    response = client.get("/api/jobs/discover?skills=React,TypeScript&target_role=Frontend+Engineer")
    assert response.status_code == 200
    data = response.json()

    assert "total_unique" in data
    assert "boolean_query" in data
    assert "open_search_links" in data
    assert "jobs" in data
    assert isinstance(data["jobs"], list)

    if data["jobs"]:
        first_job = data["jobs"][0]
        assert "match_score" in first_job
        assert "match_reasons" in first_job
        assert "matched_skills" in first_job


def test_api_jobs_query_endpoint():
    """Test POST /api/jobs/query returns exact boolean query."""
    payload = {
        "skills": ["React", "Next.js"],
        "target_roles": ["Frontend Developer"],
        "locations": ["Bangalore", "remote"],
        "job_types": ["intern", "internship"],
    }
    response = client.post("/api/jobs/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert '("React" OR "Next.js")' in data["boolean_query"]
    assert "linkedin" in data["open_search_links"]


def test_api_jobs_sources_endpoint():
    """Test GET /api/jobs/sources returns configured slug settings."""
    response = client.get("/api/jobs/sources")
    assert response.status_code == 200
    data = response.json()
    assert "greenhouse" in data
    assert "lever" in data
    assert "rss" in data
