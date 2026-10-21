# Module 02: Profile Intake — Verification Report

## Verification Summary
- **Module**: Module 02 (Profile Intake)
- **Status**: PASSED (All 31 unit & integration tests passed; all curl checks passed; browser flow verified)
- **Date**: 2026-10-15

---

## 1. Automated Test Suite (`make test`)

### Command Run:
```bash
make test
```

### Real Command Output:
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
collecting ... collected 31 items

backend/tests/test_auth.py::test_health_check PASSED                     [  3%]
backend/tests/test_auth.py::test_student_registration_and_login PASSED   [  6%]
backend/tests/test_auth.py::test_admin_registration_and_login PASSED     [  9%]
backend/tests/test_auth.py::test_duplicate_registration_fails PASSED     [ 12%]
backend/tests/test_auth.py::test_student_token_rejected_on_admin_route PASSED [ 16%]
backend/tests/test_auth.py::test_admin_can_post_job PASSED               [ 19%]
backend/tests/test_llm.py::test_mock_adapter_basic PASSED                [ 22%]
backend/tests/test_llm.py::test_extract_json_helper PASSED               [ 25%]
backend/tests/test_llm.py::test_structured_output_success_first_attempt PASSED [ 29%]
backend/tests/test_llm.py::test_structured_output_malformed_json_retry_success PASSED [ 32%]
backend/tests/test_llm.py::test_structured_output_persistent_malformed_raises_clear_schema_error PASSED [ 35%]
backend/tests/test_llm.py::test_structured_output_schema_field_validation_failure_retry PASSED [ 38%]
backend/tests/test_llm.py::test_ollama_adapter_configuration PASSED      [ 41%]
backend/tests/test_llm.py::test_ollama_adapter_unreachable_error_actionable PASSED [ 45%]
backend/tests/test_llm.py::test_ollama_adapter_model_missing_error_actionable PASSED [ 48%]
backend/tests/test_llm.py::test_cloud_adapters_require_api_key PASSED    [ 51%]
backend/tests/test_profile.py::test_clean_1page_pdf_parsing PASSED       [ 54%]
backend/tests/test_profile.py::test_messy_multipage_pdf_parsing PASSED   [ 58%]
backend/tests/test_profile.py::test_sample_docx_parsing PASSED           [ 61%]
backend/tests/test_profile.py::test_corrupt_file_raises_clean_value_error PASSED [ 64%]
backend/tests/test_profile.py::test_consent_rule_enforcement PASSED      [ 67%]
backend/tests/test_profile.py::test_corrupt_file_api_returns_clean_400_not_500 PASSED [ 70%]
backend/tests/test_profile.py::test_upload_parse_edit_persist_flow PASSED [ 74%]
backend/tests/test_profile.py::test_linkedin_pasted_and_pdf_intake PASSED [ 77%]
backend/tests/test_profile.py::test_chat_intake PASSED                   [ 80%]
backend/tests/test_profile.py::test_delete_profile_data_and_account_removes_disk_files PASSED [ 83%]
backend/tests/test_profile.py::test_student_cannot_read_other_student_data PASSED [ 87%]
backend/tests/test_settings.py::test_settings_retrieval_contains_no_raw_keys PASSED [ 90%]
backend/tests/test_settings.py::test_settings_update_persists_without_leaking_key PASSED [ 93%]
backend/tests/test_settings.py::test_log_sanitizer_redacts_api_keys PASSED [ 96%]
backend/tests/test_settings.py::test_test_connection_mock PASSED         [100%]

======================== 31 passed, 5 warnings in 1.17s ========================
```

---

## 2. Live API & Curl Verification

### Script Executed:
Executed Python-driven curl test against live FastAPI server (`http://127.0.0.1:8000`).

### Real Command Output:
```
=== 1. Register Student A ===
Register status: 201, user_id: 1
Login status: 200, token obtained

=== 2. Verify Consent Enforcement ===
Submit GitHub without consent: status=400, detail='Consent is required before submitting or updating profile data. Please grant consent first.'
Grant consent status: 200, consent_given=True
Submit GitHub with consent: status=200, username='curl_user'

=== 3. Upload Corrupt File -> Clean 400 (No 500) ===
Upload corrupt file: status=400, detail='Invalid or corrupt PDF file: Failed to open stream'

=== 4. Upload Clean 1-Page Resume ===
Upload clean resume: status=200, page_count=1
Detected skills: ['AWS', 'C++', 'CI/CD', 'CSS', 'Docker', 'Express']...
Uploaded files tracked: 1

=== 5. Edit Field & Refresh Persistence ===
Edit status: 200, headline='Lead Distributed Systems Architect'
Refreshed profile: headline='Lead Distributed Systems Architect', bio='Building autonomous verification pipelines.'

=== 6. Verify Files On Disk Before Deletion ===
Disk files matching user 1 before delete: ['1_20261015091857_clean_1page_resume.pdf']

=== 7. Delete Profile Data -> Assert Disk & DB Clear ===
Delete data status: 200, message='All profile data reset and 1 uploaded file(s) removed from disk.'
Disk files matching user 1 after delete: []
Profile after data clear: skills=[], parsed_resume={}

=== 8. Privacy & Tenant Isolation: Student A reading Student B ===
Student A accessing Student B (2): status=403, detail='Access forbidden: You cannot view another student\'s profile data.'

=== 9. Delete Student Account & All Data ===
Delete account status: 200, message='Account 1 and all associated data and 0 file(s) permanently deleted.'

ALL CURL VERIFICATION STEPS PASSED SUCCESSFULLY!
```

---

## 3. Browser UI End-to-End Verification

### Verification Scenario:
- Opened http://127.0.0.1:5173 in browser.
- Registered student account `browser_user@mirai.dev` and logged in.
- Navigated to `Profile & My Data` page (`#nav-profile`).
- Verified consent banner displayed `Action Required`. Checked `Grant Intake Consent`, verified transition to `Consent Granted`.
- Attached `backend/tests/fixtures/clean_1page_resume.pdf` to `#resume-file-input`. Clicked `Upload & Parse Resume`.
- Confirmed parsing finished, page count badge showed `1 Page (ATS Optimal)`, and extracted skills rendered in `#skills-cloud`.
- Changed Professional Headline to `Principal Infrastructure Architect` and clicked `Save Details`.
- Refreshed browser, navigated back to `Profile & My Data`, and confirmed headline persisted.
- Verified stored resume appeared in the files table under `My Data Privacy & Deletion Center`.
- Clicked `Clear Profile Data & Uploaded Files`, confirmed modal, and verified disk file removed and table displayed `No files currently saved in storage`.
- Recording and screenshot saved:
  `artifacts/verification_flow.webp`

---

## 4. Summary of What Passed, Failed, and Could Not Be Verified
- **What Passed**:
  - All 4 test fixtures (`clean_1page_resume.pdf`, `messy_multipage_resume.pdf`, `sample_resume.docx`, `corrupt_resume.pdf`) generated and parsed.
  - Page count, section extraction, skills extraction, and links extraction.
  - Corrupt file returns clean HTTP 400 Bad Request without 500 errors.
  - Consent rule strictly enforced on all intake endpoints.
  - Profile field edits persist across page refreshes.
  - Data wipe and account deletion remove both database records and physical disk files from `backend/data/uploads/`.
  - Tenant isolation prevents Student A from reading Student B's data (403 Forbidden).
  - All 20 earlier tests plus 11 new tests pass (`31 passed in 1.17s`).
- **What Failed**: None. All checks passed.
- **What Could Not Be Verified**: None. Full verification completed across pytest, curl, and live browser automation.
