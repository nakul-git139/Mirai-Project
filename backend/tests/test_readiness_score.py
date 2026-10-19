from __future__ import annotations
import math
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

from app import config
from app.services.readiness_service import (
    calculate_readiness_formula,
    get_placement_level,
    WEIGHTS,
    compute_and_save_readiness_score,
    get_current_readiness_score,
    get_readiness_history,
)
from app.models import User, Profile, ReviewResult, ReadinessScore, InterviewSession
from app.main import app


# ---------------------------------------------------------------------------
# 1. Formula Unit Tests: Mode 1 - Flag OFF (Rescaled to 100, weights / 80)
# ---------------------------------------------------------------------------
def test_readiness_formula_flag_off_all_100_yields_100():
    """
    With flag OFF, all 6 remaining components at 100/100 must produce exactly 100.
    Hand-calculated:
      100 * (25/80) + 100 * (25/80) + 100 * (10/80) + 100 * (10/80) + 100 * (5/80) + 100 * (5/80)
      = 31.25 + 31.25 + 12.50 + 12.50 + 6.25 + 6.25 = 100.00
    """
    inputs = {
        "resume": {"score": 100},
        "projects": {"score": 100},
        "mock_interview": {"score": 100},  # Even if interview data is present, flag off excludes it
        "github": {"score": 100},
        "coding_practice": {"score": 100},
        "linkedin": {"score": 100},
        "co_curricular": {"score": 100},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=False)
    assert res["overall_score"] == 100
    assert res["raw_score"] == 100.0
    assert res["level"] == "Placement ready"
    assert res["note"] == "Mock interview not included. Your score is based on the other 80% of the readiness criteria."
    assert "mock_interview" not in res["missing_components"]
    assert res["breakdown"]["mock_interview"].status == "excluded"
    assert res["breakdown"]["mock_interview"].weight == 0.0


def test_readiness_formula_flag_off_all_0_yields_0():
    """With flag OFF, all remaining components at 0/100 must produce exactly 0."""
    inputs = {
        "resume": {"score": 0},
        "projects": {"score": 0},
        "mock_interview": {"score": None},
        "github": {"score": 0},
        "coding_practice": {"score": 0},
        "linkedin": {"score": 0},
        "co_curricular": {"score": 0},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=False)
    assert res["overall_score"] == 0
    assert res["raw_score"] == 0.0
    assert res["level"] == "Not ready"
    assert res["note"] == "Mock interview not included. Your score is based on the other 80% of the readiness criteria."


def test_readiness_formula_flag_off_mixed_case():
    """
    Mixed Case (Hand-calculated arithmetic with weights / 80):
      Resume:          80 * (25 / 80) = 25.00
      Projects:        60 * (25 / 80) = 18.75
      GitHub:          90 * (10 / 80) = 11.25
      Coding practice: 50 * (10 / 80) =  6.25
      LinkedIn:        80 * ( 5 / 80) =  5.00
      Co-curricular:   60 * ( 5 / 80) =  3.75
      Mock interview:  excluded (weight = 0)
      ---------------------------------------
      Sum: 25.00 + 18.75 + 11.25 + 6.25 + 5.00 + 3.75 = 70.00
      Level: "Almost ready" (50 <= 70 <= 74)
    """
    inputs = {
        "resume": {"score": 80},
        "projects": {"score": 60},
        "mock_interview": {"score": None},
        "github": {"score": 90},
        "coding_practice": {"score": 50},
        "linkedin": {"score": 80},
        "co_curricular": {"score": 60},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=False)
    assert res["raw_score"] == 70.0
    assert res["overall_score"] == 70
    assert res["level"] == "Almost ready"
    assert res["note"] == "Mock interview not included. Your score is based on the other 80% of the readiness criteria."
    assert "mock_interview" not in res["missing_components"]
    assert all("interview" not in a.id.lower() and "interview" not in a.component.lower() for a in res["top_actions"])


# ---------------------------------------------------------------------------
# 2. Formula Unit Tests: Mode 2 - Flag ON (Interview Taken vs Not Taken)
# ---------------------------------------------------------------------------
def test_readiness_formula_flag_on_with_interview_taken():
    """
    When flag is ON and interview is TAKEN:
    Uses original 20% weight, sum of weights = 100, note is None.
    Hand-calculated arithmetic:
      Resume:          80 * (25 / 100) = 20.0
      Projects:        60 * (25 / 100) = 15.0
      Mock interview:  70 * (20 / 100) = 14.0
      GitHub:          90 * (10 / 100) =  9.0
      Coding practice: 50 * (10 / 100) =  5.0
      LinkedIn:        80 * ( 5 / 100) =  4.0
      Co-curricular:   60 * ( 5 / 100) =  3.0
      ---------------------------------------
      Sum: 20.0 + 15.0 + 14.0 + 9.0 + 5.0 + 4.0 + 3.0 = 70.0
      Level: "Almost ready" (50 <= 70 <= 74)
    """
    inputs = {
        "resume": {"score": 80},
        "projects": {"score": 60},
        "mock_interview": {"score": 70},
        "github": {"score": 90},
        "coding_practice": {"score": 50},
        "linkedin": {"score": 80},
        "co_curricular": {"score": 60},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=True)
    assert res["raw_score"] == 70.0
    assert res["overall_score"] == 70
    assert res["level"] == "Almost ready"
    assert res["note"] is None  # Note is NOT shown when interview is taken
    assert res["breakdown"]["mock_interview"].status == "scored"
    assert res["breakdown"]["mock_interview"].weight == 20.0
    assert res["breakdown"]["mock_interview"].weighted_points == 14.0


def test_readiness_formula_flag_on_interview_not_taken():
    """
    When flag is ON but interview is NOT taken:
    Rescales remaining 6 components to 100 (divided by 80), shows note,
    and lists mock_interview in missing components with action to unlock 20 pts.
    """
    inputs = {
        "resume": {"score": 80},
        "projects": {"score": 60},
        "mock_interview": {"score": None},
        "github": {"score": 90},
        "coding_practice": {"score": 50},
        "linkedin": {"score": 80},
        "co_curricular": {"score": 60},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=True)
    assert res["raw_score"] == 70.0
    assert res["overall_score"] == 70
    assert res["level"] == "Almost ready"
    assert res["note"] == "Mock interview not included. Your score is based on the other 80% of the readiness criteria."
    assert "mock_interview" in res["missing_components"]
    assert any(a.id == "ACT-MISSING-MOCK-INTERVIEW" for a in res["top_actions"])


# ---------------------------------------------------------------------------
# 3. Boundary Levels: 49, 50, 74, 75 in Both Modes
# ---------------------------------------------------------------------------
@pytest.mark.parametrize(
    "score, expected_level",
    [
        (49, "Not ready"),
        (50, "Almost ready"),
        (74, "Almost ready"),
        (75, "Placement ready"),
        (0, "Not ready"),
        (100, "Placement ready"),
    ],
)
def test_placement_level_boundaries(score: int, expected_level: str):
    """Verifies strict boundary thresholds defined in project rules."""
    assert get_placement_level(score) == expected_level


@pytest.mark.parametrize("target_score, expected_level", [
    (49, "Not ready"),
    (50, "Almost ready"),
    (74, "Almost ready"),
    (75, "Placement ready"),
])
def test_boundary_levels_flag_off(target_score: int, expected_level: str):
    """
    Verifies boundary level calculation when flag is OFF.
    All 6 components set to target_score must result in exactly target_score.
      target_score * (25/80) * 2 + target_score * (10/80) * 2 + target_score * (5/80) * 2
      = target_score * (80/80) = target_score.
    """
    inputs = {
        "resume": {"score": target_score},
        "projects": {"score": target_score},
        "mock_interview": {"score": None},
        "github": {"score": target_score},
        "coding_practice": {"score": target_score},
        "linkedin": {"score": target_score},
        "co_curricular": {"score": target_score},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=False)
    assert res["overall_score"] == target_score
    assert res["level"] == expected_level


@pytest.mark.parametrize("target_score, expected_level", [
    (49, "Not ready"),
    (50, "Almost ready"),
    (74, "Almost ready"),
    (75, "Placement ready"),
])
def test_boundary_levels_flag_on_with_interview(target_score: int, expected_level: str):
    """
    Verifies boundary level calculation when flag is ON with completed interview.
    All 7 components set to target_score must result in exactly target_score.
    """
    inputs = {
        "resume": {"score": target_score},
        "projects": {"score": target_score},
        "mock_interview": {"score": target_score},
        "github": {"score": target_score},
        "coding_practice": {"score": target_score},
        "linkedin": {"score": target_score},
        "co_curricular": {"score": target_score},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=True)
    assert res["overall_score"] == target_score
    assert res["level"] == expected_level


# ---------------------------------------------------------------------------
# 4. Missing Components Handling (Flag Off vs Flag On)
# ---------------------------------------------------------------------------
def test_missing_components_flag_off():
    """
    In Flag OFF mode:
    - Missing LinkedIn contributes 0.0.
    - Mock interview is NOT included in missing_components.
    - Remaining 5 completed components contribute:
        Resume (80) * 25/80 = 25.0
        Projects (80) * 25/80 = 25.0
        GitHub (80) * 10/80 = 10.0
        Coding (80) * 10/80 = 10.0
        Co-curricular (80) * 5/80 = 5.0
        Sum = 25 + 25 + 10 + 10 + 5 = 75.00
    - Overall score = 75 ("Placement ready").
    """
    inputs = {
        "resume": {"score": 80},
        "projects": {"score": 80},
        "mock_interview": {"score": None},
        "github": {"score": 80},
        "coding_practice": {"score": 80},
        "linkedin": {"score": None},
        "co_curricular": {"score": 80},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=False)
    assert not math.isnan(res["raw_score"])
    assert res["raw_score"] == 75.0
    assert res["overall_score"] == 75
    assert res["level"] == "Placement ready"
    assert "linkedin" in res["missing_components"]
    assert "mock_interview" not in res["missing_components"]
    assert res["breakdown"]["linkedin"].status == "missing"
    assert res["breakdown"]["mock_interview"].status == "excluded"


def test_missing_components_flag_on():
    """
    In Flag ON mode (interview not taken):
    - Missing LinkedIn and missing mock interview.
    - Rescaled formula calculates remaining 5 components to 75.00.
    - Both 'mock_interview' and 'linkedin' are in missing_components.
    """
    inputs = {
        "resume": {"score": 80},
        "projects": {"score": 80},
        "mock_interview": {"score": None},
        "github": {"score": 80},
        "coding_practice": {"score": 80},
        "linkedin": {"score": None},
        "co_curricular": {"score": 80},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=True)
    assert res["raw_score"] == 75.0
    assert res["overall_score"] == 75
    assert "mock_interview" in res["missing_components"]
    assert "linkedin" in res["missing_components"]
    assert res["breakdown"]["mock_interview"].status == "missing"


# ---------------------------------------------------------------------------
# 5. Top 5 Actions: Interview Excluded While Flag is Off & Realized Gain
# ---------------------------------------------------------------------------
def test_top_actions_never_suggest_interview_while_flag_off():
    """
    Asserts that when ENABLE_MOCK_INTERVIEW is False, the top 5 actions list
    never includes taking or improving the mock interview.
    """
    failed_check = {
        "id": "CHK-PROFILE-LINKS",
        "label": "LeetCode & GitHub Profile Links",
        "pass": False,
        "evidence": "LeetCode link missing from resume.",
        "fix": "Add LeetCode profile link to contact header.",
    }
    inputs = {
        "resume": {"score": 80, "checks": [failed_check]},
        "projects": {"score": 80, "checks": []},
        "mock_interview": {"score": None},
        "github": {"score": 80, "checks": []},
        "coding_practice": {"score": 80, "checks": []},
        "linkedin": {"score": None},
        "co_curricular": {"score": None},
    }
    res = calculate_readiness_formula(inputs, mock_interview_enabled=False)
    actions = res["top_actions"]
    assert len(actions) > 0
    for act in actions:
        assert "interview" not in act.id.lower()
        assert "interview" not in act.component.lower()


def test_top_actions_claimed_gain_matches_realized_gain_flag_off():
    """
    In Flag OFF mode:
    Resume check CHK-PROFILE-LINKS is worth 10 rubric points.
    Effective weight of resume = (25 / 80) * 100 = 31.25%.
    Claimed points gained = round(10 * (25 / 80), 2) = 3.12 points.
    Fixing it from 80 to 90 produces exact realized gain of 3.12 raw score points.
    """
    failed_check = {
        "id": "CHK-PROFILE-LINKS",
        "label": "LeetCode & GitHub Profile Links",
        "pass": False,
        "evidence": "LeetCode link missing.",
        "fix": "Add LeetCode profile link.",
    }
    inputs_before = {
        "resume": {"score": 80, "checks": [failed_check]},
        "projects": {"score": 80, "checks": []},
        "mock_interview": {"score": None},
        "github": {"score": 80, "checks": []},
        "coding_practice": {"score": 80, "checks": []},
        "linkedin": {"score": 80, "checks": []},
        "co_curricular": {"score": 80, "checks": []},
    }
    res_before = calculate_readiness_formula(inputs_before, mock_interview_enabled=False)
    top_act = res_before["top_actions"][0]
    claimed_gain = top_act.points_gained
    assert top_act.id == "ACT-CHK-PROFILE-LINKS"
    assert claimed_gain == round(10 * (25.0 / 80.0), 2)  # 3.12

    inputs_after = {
        "resume": {"score": 90, "checks": [{**failed_check, "pass": True}]},
        "projects": {"score": 80, "checks": []},
        "mock_interview": {"score": None},
        "github": {"score": 80, "checks": []},
        "coding_practice": {"score": 80, "checks": []},
        "linkedin": {"score": 80, "checks": []},
        "co_curricular": {"score": 80, "checks": []},
    }
    res_after = calculate_readiness_formula(inputs_after, mock_interview_enabled=False)
    realized_gain = round(res_after["raw_score"] - res_before["raw_score"], 2)
    assert realized_gain == claimed_gain


# ---------------------------------------------------------------------------
# 6. Database Integration & API Endpoints
# ---------------------------------------------------------------------------
def test_progress_tracking_and_history_update(client: TestClient, db_session, student_user: User, student_auth_headers: dict):
    """
    Verifies that compute_and_save_readiness_score respects the flag,
    persists history snapshots with the rescaled score and note.
    """
    # 1. Clear previous reviews and scores
    db_session.query(ReadinessScore).filter(ReadinessScore.user_id == student_user.id).delete()
    db_session.query(ReviewResult).filter(ReviewResult.user_id == student_user.id).delete()
    db_session.commit()

    # Create initial resume review: score = 80
    rev1 = ReviewResult(
        user_id=student_user.id,
        review_type="resume",
        score=80,
        summary="Initial review: Missing LeetCode link.",
        checks=[
            {
                "id": "CHK-PROFILE-LINKS",
                "label": "LeetCode & GitHub Profile Links",
                "pass": False,
                "evidence": "LeetCode profile link missing.",
                "fix": "Add LeetCode profile URL to contact header.",
            }
        ],
        created_at=datetime.utcnow(),
    )
    db_session.add(rev1)
    db_session.commit()

    snap1 = compute_and_save_readiness_score(db_session, student_user.id)
    initial_raw = snap1.raw_score

    # 2. Fix the issue: resume score increases to 90
    rev2 = ReviewResult(
        user_id=student_user.id,
        review_type="resume",
        score=90,
        summary="Updated review: LeetCode link present.",
        checks=[
            {
                "id": "CHK-PROFILE-LINKS",
                "label": "LeetCode & GitHub Profile Links",
                "pass": True,
                "evidence": "Found LeetCode profile link.",
                "fix": "Maintain active profile links.",
            }
        ],
        created_at=datetime.utcnow(),
    )
    db_session.add(rev2)
    db_session.commit()

    snap2 = compute_and_save_readiness_score(db_session, student_user.id)
    new_raw = snap2.raw_score

    # In flag off mode, delta = 10 * 25 / 80 = 3.12 pts
    expected_delta = round(10 * (25.0 / 80.0), 2)
    assert round(new_raw - initial_raw, 2) == expected_delta

    # Check history
    h2 = get_readiness_history(db_session, student_user.id)
    assert len(h2) == 2
    assert h2[1].overall_score >= h2[0].overall_score


def test_readiness_api_endpoints_flag_off_includes_note(client: TestClient, db_session, student_user: User, student_auth_headers: dict, monkeypatch):
    """
    Verifies that GET /api/readiness/current returns the clear note and rescaled criteria when flag is off.
    """
    monkeypatch.setattr(config, "ENABLE_MOCK_INTERVIEW", False)

    profile = db_session.query(Profile).filter(Profile.user_id == student_user.id).first()
    if not profile:
        profile = Profile(user_id=student_user.id, consent_given=True)
        db_session.add(profile)
    else:
        profile.consent_given = True
    db_session.commit()

    resp = client.get("/api/readiness/current", headers=student_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "note" in data
    assert data["note"] == "Mock interview not included. Your score is based on the other 80% of the readiness criteria."
    assert "mock_interview" not in data.get("missing_components", [])
    assert data["breakdown"]["mock_interview"]["status"] == "excluded"
    assert data["breakdown"]["mock_interview"]["weight"] == 0.0

    # Ensure no interview actions in top actions
    for act in data.get("top_actions", []):
        assert "interview" not in act["id"].lower()
        assert "interview" not in act["component"].lower()
