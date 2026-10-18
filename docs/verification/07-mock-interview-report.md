# Verification Report: Module 07 — Mock Interview Simulator (Text Mode)

**Date**: 2026-10-16  
**Environment**: macOS (Darwin 25.3.0), Python 3.9.6, FastAPI, SQLite (SQLAlchemy), Vite + React, Chromium Browser Subagent, Local Ollama (`smollm:135m`)  
**Test Suite**: `backend/tests/test_interview.py` & full test suite (`make test`)

---

## 1. Commands Run and Real Outputs

### Command A: Mock Interview Pytest Suite (`test_interview.py`)
```bash
backend/venv/bin/pytest -v backend/tests/test_interview.py
```
**Real Output**:
```
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Users/nakulmirai/Mirai Project/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/nakulmirai/Mirai Project/backend
configfile: pytest.ini
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 6 items                                                              

backend/tests/test_interview.py::test_question_generation_grounded_in_resume PASSED [ 16%]
backend/tests/test_interview.py::test_three_scripted_sessions_score_ordering PASSED [ 33%]
backend/tests/test_interview.py::test_timer_session_ends_at_limit_and_produces_score PASSED [ 50%]
backend/tests/test_interview.py::test_edge_cases_empty_answer_quit_and_refresh PASSED [ 66%]
backend/tests/test_interview.py::test_transcript_saved_and_readiness_score_updates PASSED [ 83%]
backend/tests/test_interview.py::test_consent_enforcement_mock_interview PASSED [100%]

======================== 6 passed, 5 warnings in 8.05s =========================
```

---

### Command B: Full Monorepo Pytest Suite (`make test`)
```bash
make test
```
**Real Output**:
```
Running all backend tests with pytest...
backend/venv/bin/pytest -v
============================= test session starts ==============================
platform darwin -- Python 3.9.6, pytest-8.4.2, pluggy-1.6.0 -- /Users/nakulmirai/Mirai Project/backend/venv/bin/python3
cachedir: .pytest_cache
rootdir: /Users/nakulmirai/Mirai Project
configfile: pytest.ini
testpaths: backend/tests
plugins: anyio-4.12.1, asyncio-1.2.0
asyncio: mode=auto, debug=False, asyncio_default_fixture_loop_scope=None, asyncio_default_test_loop_scope=function
collecting ... collected 73 items                                                             

backend/tests/test_auth.py::test_health_check PASSED                     [  1%]
backend/tests/test_auth.py::test_student_registration_and_login PASSED   [  2%]
backend/tests/test_auth.py::test_admin_registration_and_login PASSED     [  4%]
backend/tests/test_auth.py::test_duplicate_registration_fails PASSED     [  5%]
backend/tests/test_auth.py::test_student_token_rejected_on_admin_route PASSED [  6%]
backend/tests/test_auth.py::test_admin_can_post_job PASSED               [  8%]
backend/tests/test_github_review.py::test_good_repository_evaluation PASSED [  9%]
backend/tests/test_github_review.py::test_repo_with_no_readme PASSED     [ 10%]
backend/tests/test_github_review.py::test_planted_fake_secret_detection_and_false_positive_absence PASSED [ 12%]
backend/tests/test_github_review.py::test_nonexistent_github_username_handled_cleanly PASSED [ 13%]
backend/tests/test_github_review.py::test_live_link_returning_404 PASSED [ 15%]
backend/tests/test_github_review.py::test_live_link_with_js_console_error PASSED [ 16%]
backend/tests/test_github_review.py::test_github_rate_limit_simulation_provides_helpful_guidance PASSED [ 17%]
backend/tests/test_github_review.py::test_playwright_screenshots_and_unreachable_timeout PASSED [ 19%]
backend/tests/test_github_review.py::test_two_real_public_github_profiles PASSED [ 20%]
backend/tests/test_github_review.py::test_api_endpoints_and_consent PASSED [ 21%]
backend/tests/test_interview.py::test_question_generation_grounded_in_resume PASSED [ 23%]
backend/tests/test_interview.py::test_three_scripted_sessions_score_ordering PASSED [ 24%]
backend/tests/test_interview.py::test_timer_session_ends_at_limit_and_produces_score PASSED [ 26%]
backend/tests/test_interview.py::test_edge_cases_empty_answer_quit_and_refresh PASSED [ 27%]
backend/tests/test_interview.py::test_transcript_saved_and_readiness_score_updates PASSED [ 28%]
backend/tests/test_interview.py::test_consent_enforcement_mock_interview PASSED [ 30%]
backend/tests/test_linkedin_review.py::test_three_profiles_score_ordering_and_contradiction_detection PASSED [ 31%]
backend/tests/test_linkedin_review.py::test_rewrites_length_and_groundedness PASSED [ 32%]
backend/tests/test_linkedin_review.py::test_consistency_five_runs PASSED [ 34%]
backend/tests/test_linkedin_review.py::test_both_pdf_export_and_pasted_text_input PASSED [ 35%]
backend/tests/test_linkedin_review.py::test_api_endpoints_pdf_and_text PASSED [ 36%]
backend/tests/test_linkedin_review.py::test_consent_enforcement_linkedin_review PASSED [ 38%]
backend/tests/test_llm.py::test_mock_adapter_basic PASSED                [ 39%]
backend/tests/test_llm.py::test_extract_json_helper PASSED               [ 41%]
backend/tests/test_llm.py::test_structured_output_success_first_attempt PASSED [ 42%]
backend/tests/test_llm.py::test_structured_output_malformed_json_retry_success PASSED [ 43%]
backend/tests/test_llm.py::test_structured_output_persistent_malformed_raises_clear_schema_error PASSED [ 45%]
backend/tests/test_llm.py::test_structured_output_schema_field_validation_failure_retry PASSED [ 46%]
backend/tests/test_llm.py::test_ollama_adapter_configuration PASSED      [ 47%]
backend/tests/test_llm.py::test_ollama_adapter_unreachable_error_actionable PASSED [ 49%]
backend/tests/test_llm.py::test_ollama_adapter_model_missing_error_actionable PASSED [ 50%]
backend/tests/test_llm.py::test_cloud_adapters_require_api_key PASSED    [ 52%]
backend/tests/test_profile.py::test_clean_1page_pdf_parsing PASSED       [ 53%]
backend/tests/test_profile.py::test_messy_multipage_pdf_parsing PASSED   [ 54%]
backend/tests/test_profile.py::test_sample_docx_parsing PASSED           [ 56%]
backend/tests/test_profile.py::test_corrupt_file_raises_clean_value_error PASSED [ 57%]
backend/tests/test_profile.py::test_consent_rule_enforcement PASSED      [ 58%]
backend/tests/test_profile.py::test_corrupt_file_api_returns_clean_400_not_500 PASSED [ 60%]
backend/tests/test_profile.py::test_upload_parse_edit_persist_flow PASSED [ 61%]
backend/tests/test_profile.py::test_linkedin_pasted_and_pdf_intake PASSED [ 63%]
backend/tests/test_profile.py::test_chat_intake PASSED                   [ 64%]
backend/tests/test_profile.py::test_delete_profile_data_and_account_removes_disk_files PASSED [ 65%]
backend/tests/test_profile.py::test_student_cannot_read_other_student_data PASSED [ 67%]
backend/tests/test_readiness_score.py::test_readiness_formula_all_100_yields_100 PASSED [ 68%]
backend/tests/test_readiness_score.py::test_readiness_formula_all_0_yields_0 PASSED [ 69%]
backend/tests/test_readiness_score.py::test_readiness_formula_mixed_case_1 PASSED [ 71%]
backend/tests/test_readiness_score.py::test_readiness_formula_mixed_case_2 PASSED [ 72%]
backend/tests/test_readiness_score.py::test_readiness_formula_mixed_case_3 PASSED [ 73%]
backend/tests/test_readiness_score.py::test_placement_level_boundaries[49-Not ready] PASSED [ 75%]
backend/tests/test_readiness_score.py::test_placement_level_boundaries[50-Almost ready] PASSED [ 76%]
backend/tests/test_readiness_score.py::test_placement_level_boundaries[74-Almost ready] PASSED [ 78%]
backend/tests/test_readiness_score.py::test_placement_level_boundaries[75-Placement ready] PASSED [ 79%]
backend/tests/test_readiness_score.py::test_placement_level_boundaries[0-Not ready] PASSED [ 80%]
backend/tests/test_readiness_score.py::test_placement_level_boundaries[100-Placement ready] PASSED [ 82%]
backend/tests/test_readiness_score.py::test_missing_components_no_crash_or_nan PASSED [ 83%]
backend/tests/test_readiness_score.py::test_top_actions_sorted_and_applying_top_action_yields_claimed_gain PASSED [ 84%]
backend/tests/test_readiness_score.py::test_progress_tracking_and_history_update PASSED [ 86%]
backend/tests/test_readiness_score.py::test_readiness_api_endpoints_and_consent PASSED [ 87%]
backend/tests/test_resume_review.py::test_four_resumes_planted_flaws_detected PASSED [ 89%]
backend/tests/test_resume_review.py::test_consistency_five_runs PASSED   [ 90%]
backend/tests/test_resume_review.py::test_failed_checks_have_specific_non_generic_fixes PASSED [ 91%]
backend/tests/test_resume_review.py::test_resume_review_api_endpoints PASSED [ 93%]
backend/tests/test_resume_review.py::test_resume_review_consent_enforcement PASSED [ 94%]
backend/tests/test_settings.py::test_settings_retrieval_contains_no_raw_keys PASSED [ 95%]
backend/tests/test_settings.py::test_settings_update_persists_without_leaking_key PASSED [ 97%]
backend/tests/test_settings.py::test_log_sanitizer_redacts_api_keys PASSED [ 98%]
backend/tests/test_settings.py::test_test_connection_mock PASSED         [100%]

======================= 73 passed, 5 warnings in 21.37s ========================
```

---

### Command C: Real Readiness Score Recalculation API Check
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@msot.edu","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -s http://127.0.0.1:8000/api/readiness/current \
  -H "Authorization: Bearer $TOKEN"
```
**Real Output**:
```json
{
  "id": 7,
  "user_id": 12,
  "overall_score": 74,
  "raw_score": 73.95,
  "level": "Almost ready",
  "breakdown": {
    "resume": { "weight": 25, "score": 100.0, "weighted_points": 25.0, "status": "scored" },
    "projects": { "weight": 25, "score": 100.0, "weighted_points": 25.0, "status": "scored" },
    "mock_interview": {
      "weight": 20,
      "score": 66.0,
      "weighted_points": 13.2,
      "status": "scored",
      "summary": "Completed mock interview score: 66/100 (1 of 4 criteria passed)."
    },
    "coding_practice": { "weight": 10, "score": 70.0, "weighted_points": 7.0, "status": "scored" },
    "co_curricular": { "weight": 5, "score": 75.0, "weighted_points": 3.75, "status": "scored" },
    "github": { "weight": 10, "score": null, "weighted_points": 0.0, "status": "missing" },
    "linkedin": { "weight": 5, "score": null, "weighted_points": 0.0, "status": "missing" }
  },
  "top_actions": [
    { "id": "ACT-MISSING-GITHUB", "title": "Run automated review on your GitHub repository", "points_gained": 10.0 },
    { "id": "ACT-CHK-INT-TECH-DEPTH", "title": "Fix Technical Accuracy & Depth", "points_gained": 7.0 },
    { "id": "ACT-MISSING-LINKEDIN", "title": "Run benchmark review on your LinkedIn profile", "points_gained": 5.0 },
    { "id": "ACT-CHK-INT-CLARITY", "title": "Fix Communication & Structure", "points_gained": 5.0 },
    { "id": "ACT-CHK-INT-CRITICAL-THINK", "title": "Fix Problem-Solving & Trade-offs", "points_gained": 3.0 }
  ]
}
```

---

### Command D: Browser End-to-End Test (Chromium)
- **Browser Subagent Flow**:
  1. Opened `http://127.0.0.1:5173`.
  2. Logged in as student `alex@msot.edu` / `password123`.
  3. Navigated to **Mock Interview** tab.
  4. Verified 15-minute and 20-minute duration selectors, role options, and candidate grounding preview.
  5. Started 15-minute interview; verified countdown timer, Q1 prompt, and text area.
  6. Answered questions referencing candidate stack (FastAPI, Docker, PostgreSQL, AWS ECS, Redis).
  7. Concluded session and verified Performance Report:
     - Final score: **66 / 100** (*Almost Ready*)
     - 4 Rubric Criteria progress bars (`CRIT-TECH-DEPTH`, `CRIT-CLARITY-COMM`, `CRIT-GROUNDED-EXP`, `CRIT-CRITICAL-THINK`)
     - Demonstrated Strengths & Improvement Tips
     - Full Turn-by-Turn Replayable Transcript
- **Recording Artifact**: `docs/samples/` and `mock_interview_report_1792172278058.png`

---

## 2. Real Transcripts Generated & Saved

1. **`docs/samples/scripted_interview_transcript.json`**:
   - Multi-turn benchmark session evaluating 5 turns across all question types.
   - Final score: 67 / 100.
2. **`docs/samples/ollama_interview_transcript.json`**:
   - Real local session executed with Ollama (`smollm:135m`).
   - Final score: 67 / 100.

---

## 3. What Passed, What Failed, and What Could Not Be Verified

| Verification Requirement | Status | Evidence / Notes |
| :--- | :--- | :--- |
| **1. Resume Grounding & Mix** | **PASSED** | `test_question_generation_grounded_in_resume` passed: verified candidate projects (*Readiness Copilot*, *Distributed Task Queue*) and skills (*Python*, *FastAPI*, *React*) are cited across technical, project deep-dive, and HR questions. |
| **2. 3 Scripted Profiles (Score Ordering)** | **PASSED** | `test_three_scripted_sessions_score_ordering` passed: strong answerer (81.0) > weak answerer (30.0) >= off-topic answerer (30.0); strong score $\ge 75$, weak score $\le 45$. |
| **3. Countdown Timer Expiration** | **PASSED** | `test_timer_session_ends_at_limit_and_produces_score` passed: session auto-completes at limit, transitions to `status="completed"`, and calculates valid final score and feedback. |
| **4. Edge Cases: Empty answers, Quit, Refresh** | **PASSED** | `test_edge_cases_empty_answer_quit_and_refresh` passed: rejects empty input with 400, early termination via `/end` cleanly scores completed questions, and browser refresh resumes active session via `GET /api/interview/active`. |
| **5. Transcript Saved & Readiness Update** | **PASSED** | `test_transcript_saved_and_readiness_score_updates` passed: transcript saved to SQLite, `GET /api/interview/{id}/replay` returns full turn history, and readiness score updates `mock_interview` from `missing` to `scored`, lifting overall score from 61 to 74. |
| **6. Real Ollama & Scripted Sessions** | **PASSED** | Real Ollama (`smollm:135m`) and scripted sessions executed and persisted to `docs/samples/ollama_interview_transcript.json` and `docs/samples/scripted_interview_transcript.json`. |
| **7. Full Test Suite & Regressions** | **PASSED** | `make test`: All 73 tests passed cleanly (0 failed). Zero regressions across earlier modules. |
| **Hosted Cloud API End-to-End** | **COULD NOT VERIFY (NO HOSTED API KEY CONFIGURED)** | No paid cloud API key (OpenAI/Anthropic/Gemini) was provided in the local environment; verified locally with Ollama and Mock adapter. |
