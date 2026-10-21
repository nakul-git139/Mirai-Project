# Verification Report: Module 05 — GitHub Codebase Review & Live Link Checker

**Date**: 2026-10-16  
**Environment**: macOS (Darwin 25.3.0), Python 3.9.6, FastAPI, Playwright (Chromium Headless Shell 148.0.7778.96), Vite + React  
**Test Suite**: `backend/tests/test_github_review.py` & full test suite (`make test`)

---

## 1. Commands Run and Real Outputs

### Command A: Full Monorepo Pytest Suite
```bash
make test
```
**Real Output**:
```
Running all backend tests with pytest...
backend/venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- backend/venv/bin/python
cachedir: .pytest_cache
rootdir: .
configfile: pytest.ini
testpaths: backend/tests
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 52 items                                                             

backend/tests/test_auth.py::test_health_check PASSED                     [  1%]
backend/tests/test_auth.py::test_student_registration_and_login PASSED   [  3%]
backend/tests/test_auth.py::test_admin_registration_and_login PASSED     [  5%]
backend/tests/test_auth.py::test_duplicate_registration_fails PASSED     [  7%]
backend/tests/test_auth.py::test_student_token_rejected_on_admin_route PASSED [  9%]
backend/tests/test_auth.py::test_admin_can_post_job PASSED               [ 11%]
backend/tests/test_github_review.py::test_good_repository_evaluation PASSED [ 13%]
backend/tests/test_github_review.py::test_repo_with_no_readme PASSED     [ 15%]
backend/tests/test_github_review.py::test_planted_fake_secret_detection_and_false_positive_absence PASSED [ 17%]
backend/tests/test_github_review.py::test_nonexistent_github_username_handled_cleanly PASSED [ 19%]
backend/tests/test_github_review.py::test_live_link_returning_404 PASSED [ 21%]
backend/tests/test_github_review.py::test_live_link_with_js_console_error PASSED [ 23%]
backend/tests/test_github_review.py::test_github_rate_limit_simulation_provides_helpful_guidance PASSED [ 25%]
backend/tests/test_github_review.py::test_playwright_screenshots_and_unreachable_timeout PASSED [ 26%]
backend/tests/test_github_review.py::test_two_real_public_github_profiles PASSED [ 28%]
backend/tests/test_github_review.py::test_api_endpoints_and_consent PASSED [ 30%]
backend/tests/test_linkedin_review.py::test_three_profiles_score_ordering_and_contradiction_detection PASSED [ 32%]
backend/tests/test_linkedin_review.py::test_rewrites_length_and_groundedness PASSED [ 34%]
backend/tests/test_linkedin_review.py::test_consistency_five_runs 
[LinkedIn Review 5x Consistency Test] Run scores: [100, 100, 100, 100, 100]
PASSED [ 36%]
backend/tests/test_linkedin_review.py::test_both_pdf_export_and_pasted_text_input PASSED [ 38%]
backend/tests/test_linkedin_review.py::test_api_endpoints_pdf_and_text PASSED [ 40%]
backend/tests/test_linkedin_review.py::test_consent_enforcement_linkedin_review PASSED [ 42%]
backend/tests/test_llm.py::test_mock_adapter_basic PASSED                [ 44%]
backend/tests/test_llm.py::test_extract_json_helper PASSED               [ 46%]
backend/tests/test_llm.py::test_structured_output_success_first_attempt PASSED [ 48%]
backend/tests/test_llm.py::test_structured_output_malformed_json_retry_success PASSED [ 50%]
backend/tests/test_llm.py::test_structured_output_persistent_malformed_raises_clear_schema_error PASSED [ 51%]
backend/tests/test_llm.py::test_structured_output_schema_field_validation_failure_retry PASSED [ 53%]
backend/tests/test_llm.py::test_ollama_adapter_configuration PASSED      [ 55%]
backend/tests/test_llm.py::test_ollama_adapter_unreachable_error_actionable PASSED [ 57%]
backend/tests/test_llm.py::test_ollama_adapter_model_missing_error_actionable PASSED [ 59%]
backend/tests/test_llm.py::test_cloud_adapters_require_api_key PASSED    [ 61%]
backend/tests/test_profile.py::test_clean_1page_pdf_parsing PASSED       [ 63%]
backend/tests/test_profile.py::test_messy_multipage_pdf_parsing PASSED   [ 65%]
backend/tests/test_profile.py::test_sample_docx_parsing PASSED           [ 67%]
backend/tests/test_profile.py::test_corrupt_file_raises_clean_value_error PASSED [ 69%]
backend/tests/test_profile.py::test_consent_rule_enforcement PASSED      [ 71%]
backend/tests/test_profile.py::test_corrupt_file_api_returns_clean_400_not_500 PASSED [ 73%]
backend/tests/test_profile.py::test_upload_parse_edit_persist_flow PASSED [ 75%]
backend/tests/test_profile.py::test_linkedin_pasted_and_pdf_intake PASSED [ 76%]
backend/tests/test_profile.py::test_chat_intake PASSED                   [ 78%]
backend/tests/test_profile.py::test_delete_profile_data_and_account_removes_disk_files PASSED [ 80%]
backend/tests/test_profile.py::test_student_cannot_read_other_student_data PASSED [ 82%]
backend/tests/test_resume_review.py::test_four_resumes_planted_flaws_detected PASSED [ 84%]
backend/tests/test_resume_review.py::test_consistency_five_runs PASSED   [ 86%]
backend/tests/test_resume_review.py::test_failed_checks_have_specific_non_generic_fixes PASSED [ 88%]
backend/tests/test_resume_review.py::test_resume_review_api_endpoints PASSED [ 90%]
backend/tests/test_resume_review.py::test_resume_review_consent_enforcement PASSED [ 92%]
backend/tests/test_settings.py::test_settings_retrieval_contains_no_raw_keys PASSED [ 94%]
backend/tests/test_settings.py::test_settings_update_persists_without_leaking_key PASSED [ 96%]
backend/tests/test_settings.py::test_log_sanitizer_redacts_api_keys PASSED [ 98%]
backend/tests/test_settings.py::test_test_connection_mock PASSED         [100%]

======================== 52 passed, 5 warnings in 11.41s ========================
```

---

### Command B: Real Public GitHub Profile 1 (`pallets/flask`) via REST API
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"curl_student_mod05@msot.edu","password":"Password123!"}' | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/api/reviews/github \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"pallets","repo_url":"pallets/flask","live_url":"https://flask.palletsprojects.com"}' | jq '{score: .score, summary: .summary, checks_count: (.checks | length), repo_details: .repo_details}'
```
**Real Output**:
```json
{
  "score": 85,
  "summary": "GitHub & Codebase Review Score: 85/100. Passed 11 of 13 placement benchmark checks. Tier 2: Interview Ready. Solid technical foundation; addressing flagged fixes will maximize recruiter callbacks.",
  "checks_count": 13,
  "repo_details": {
    "owner": "pallets",
    "name": "flask",
    "description": "The Python micro framework for building web applications.",
    "language": "Python",
    "stargazers_count": 74910,
    "forks_count": 17079,
    "file_count": 287
  }
}
```

---

### Command C: Real Public GitHub Profile 2 (`torvalds/uemacs`) via REST API
```bash
curl -s -X POST http://127.0.0.1:8000/api/reviews/github \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"username":"torvalds","repo_url":"torvalds/uemacs"}' | jq '{score: .score, summary: .summary, checks_count: (.checks | length), repo_details: .repo_details}'
```
**Real Output**:
```json
{
  "score": 40,
  "summary": "GitHub & Codebase Review Score: 40/100. Passed 5 of 13 placement benchmark checks. Tier 4: Overhaul Required. Critical gaps in security, documentation, tests, or live deployment.",
  "checks_count": 13,
  "repo_details": {
    "owner": "torvalds",
    "name": "uemacs",
    "description": "Random version of microemacs with my private modificatons",
    "language": "C",
    "stargazers_count": 2168,
    "forks_count": 325,
    "file_count": 51
  }
}
```

---

### Command D: Standalone Playwright Live Link Verification
```bash
curl -s -X POST http://127.0.0.1:8000/api/reviews/live-link \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://example.com","project_title":"Example Domain"}' | jq
```
**Real Output**:
```json
{
  "url": "https://example.com",
  "loaded": true,
  "status_code": 200,
  "load_time_ms": 137,
  "console_errors": [],
  "network_errors": [],
  "title": "Example Domain",
  "meta_description": "",
  "desktop_screenshot": "0f58acc21607_desktop.png",
  "mobile_screenshot": "0f58acc21607_mobile.png",
  "mobile_overflow": false,
  "content_match": true,
  "content_overlap_ratio": 1.0,
  "extracted_snippet": "This domain is for use in documentation examples without needing permission. This is not a service; avoid relying on it for testing and monitoring purposes.",
  "error_message": null
}
```

---

## 2. Verification Checklist Matrix

| # | Verification Criterion | Status | Evidence / Details |
| :--- | :--- | :--- | :--- |
| **1** | **6+ Test Cases Implemented** | **PASSED** | 1. Good Repo (>=80 score, all checks pass)<br>2. Repo with no README (flags `CHK-GH-REPO-README`)<br>3. Planted Secret (`AKIA9876543210SECKEY` and RSA private key flagged)<br>4. Nonexistent Username (`GitHubNotFoundError` on 404)<br>5. Live Link returning 404 (`loaded == False, status == 404`)<br>6. Live Link with JS Console Error (`TypeError` captured) |
| **2** | **2 Real Public GitHub Profiles** | **PASSED** | Tested `pallets/flask` (Score: 85, Tier 2) and `torvalds/uemacs` (Score: 40, Tier 4). |
| **3** | **Secret Scanner Validation** | **PASSED** | Planted AWS access key and RSA key detected and masked (`AKIA...KEY`). Zero false positives on clean repo containing `.env.example`, `package-lock.json`, and documentation placeholders (`AKIAIOSFODNN7EXAMPLE`). |
| **4** | **Playwright Screenshots & Timeout** | **PASSED** | Generates desktop (`1280x720`) and mobile (`375x667`) screenshots saved to `backend/data/screenshots/`. Unreachable IP (`http://10.255.255.1:9999/unreachable`) times out cleanly within 1,500ms without hanging or crashing. |
| **5** | **GitHub Rate Limit Simulation** | **PASSED** | Mocked HTTP 403 response with `x-ratelimit-remaining: 0`. Raises `GitHubRateLimitError` providing actionable guidance to add a Personal Access Token in Settings for 5,000 req/hr. |
| **6** | **All Earlier Modules Pass** | **PASSED** | `make test` executes 52 passing tests (Auth, Profile Intake, Resume Review, LinkedIn Review, Settings, LLM Adapter, and GitHub Review). Zero regressions. |

---

## 3. What Could Not Be Verified & Why
- Direct OAuth user impersonation was intentionally not implemented per **Rule 4 (Privacy)**: The Copilot operates strictly on public developer data and does not ask students for login credentials or scrape private repositories.
