from __future__ import annotations
import math
import pytest
from datetime import datetime
from fastapi.testclient import TestClient

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
# 1. Formula Unit Tests with Explicit Hand-Calculated Arithmetic
# ---------------------------------------------------------------------------
def test_readiness_formula_all_100_yields_100():
    """All 7 components at 100/100 must produce exactly 100."""
    inputs = {
        "resume": {"score": 100},
        "projects": {"score": 100},
        "mock_interview": {"score": 100},
        "github": {"score": 100},
        "coding_practice": {"score": 100},
        "linkedin": {"score": 100},
        "co_curricular": {"score": 100},
    }
    res = calculate_readiness_formula(inputs)
    assert res["overall_score"] == 100
    assert res["raw_score"] == 100.0
    assert res["level"] == "Placement ready"
    assert len(res["missing_components"]) == 0
    assert len(res["completed_components"]) == 7


def test_readiness_formula_all_0_yields_0():
    """All 7 components at 0/100 must produce exactly 0."""
    inputs = {
        "resume": {"score": 0},
        "projects": {"score": 0},
        "mock_interview": {"score": 0},
        "github": {"score": 0},
        "coding_practice": {"score": 0},
        "linkedin": {"score": 0},
        "co_curricular": {"score": 0},
    }
    res = calculate_readiness_formula(inputs)
    assert res["overall_score"] == 0
    assert res["raw_score"] == 0.0
    assert res["level"] == "Not ready"


def test_readiness_formula_mixed_case_1():
    """
    Mixed Case 1 (Hand-calculated arithmetic):
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
    res = calculate_readiness_formula(inputs)
    assert res["raw_score"] == 70.0
    assert res["overall_score"] == 70
    assert res["level"] == "Almost ready"


def test_readiness_formula_mixed_case_2():
    """
    Mixed Case 2 (Hand-calculated arithmetic):
      Resume:          92 * (25 / 100) = 23.00
      Projects:        88 * (25 / 100) = 22.00
      Mock interview:  85 * (20 / 100) = 17.00
      GitHub:          80 * (10 / 100) =  8.00
      Coding practice: 70 * (10 / 100) =  7.00
      LinkedIn:       100 * ( 5 / 100) =  5.00
      Co-curricular:   80 * ( 5 / 100) =  4.00
      ----------------------------------------
      Sum: 23.0 + 22.0 + 17.0 + 8.0 + 7.0 + 5.0 + 4.0 = 86.00
      Level: "Placement ready" (75 <= 86 <= 100)
    """
    inputs = {
        "resume": {"score": 92},
        "projects": {"score": 88},
        "mock_interview": {"score": 85},
        "github": {"score": 80},
        "coding_practice": {"score": 70},
        "linkedin": {"score": 100},
        "co_curricular": {"score": 80},
    }
    res = calculate_readiness_formula(inputs)
    assert res["raw_score"] == 86.0
    assert res["overall_score"] == 86
    assert res["level"] == "Placement ready"


def test_readiness_formula_mixed_case_3():
    """
    Mixed Case 3 (Hand-calculated arithmetic):
      Resume:          40 * (25 / 100) = 10.00
      Projects:        40 * (25 / 100) = 10.00
      Mock interview:  50 * (20 / 100) = 10.00
      GitHub:          30 * (10 / 100) =  3.00
      Coding practice: 20 * (10 / 100) =  2.00
      LinkedIn:        40 * ( 5 / 100) =  2.00
      Co-curricular:    0 * ( 5 / 100) =  0.00
      ----------------------------------------
      Sum: 10.0 + 10.0 + 10.0 + 3.0 + 2.0 + 2.0 + 0.0 = 37.00
      Level: "Not ready" (0 <= 37 <= 49)
    """
    inputs = {
        "resume": {"score": 40},
        "projects": {"score": 40},
        "mock_interview": {"score": 50},
        "github": {"score": 30},
        "coding_practice": {"score": 20},
        "linkedin": {"score": 40},
        "co_curricular": {"score": 0},
    }
    res = calculate_readiness_formula(inputs)
    assert res["raw_score"] == 37.0
    assert res["overall_score"] == 37
    assert res["level"] == "Not ready"


# ---------------------------------------------------------------------------
# 2. Boundary Levels: 49, 50, 74, 75
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


# ---------------------------------------------------------------------------
# 3. Missing Components Handling (no interview, no LinkedIn)
# ---------------------------------------------------------------------------
def test_missing_components_no_crash_or_nan():
    """
    Simulates a student with no mock interview and no LinkedIn review.
    Score must behave deterministically:
      - missing components assigned 0 earned points toward total
      - no crash, no division by zero, no NaN
      - explicitly flags 'mock_interview' and 'linkedin' in missing_components list
    """
    inputs = {
        "resume": {"score": 80},         # 80 * 0.25 = 20.0
        "projects": {"score": 80},       # 80 * 0.25 = 20.0
        "mock_interview": {"score": None}, # Missing:  0.0
        "github": {"score": 80},         # 80 * 0.10 =  8.0
        "coding_practice": {"score": 80},# 80 * 0.10 =  8.0
        "linkedin": {"score": None},       # Missing:  0.0
        "co_curricular": {"score": 80},  # 80 * 0.05 =  4.0
    }
    # Expected sum = 20.0 + 20.0 + 0 + 8.0 + 8.0 + 0 + 4.0 = 60.0
    res = calculate_readiness_formula(inputs)

    assert not math.isnan(res["raw_score"])
    assert res["raw_score"] == 60.0
    assert res["overall_score"] == 60
    assert res["level"] == "Almost ready"

    assert "mock_interview" in res["missing_components"]
    assert "linkedin" in res["missing_components"]
    assert res["breakdown"]["mock_interview"].status == "missing"
    assert res["breakdown"]["mock_interview"].score is None
    assert res["breakdown"]["mock_interview"].weighted_points == 0.0

    assert res["breakdown"]["linkedin"].status == "missing"
    assert res["breakdown"]["linkedin"].score is None
    assert res["breakdown"]["linkedin"].weighted_points == 0.0


# ---------------------------------------------------------------------------
# 4. Top 5 Actions Sorted by Points Gained & Claimed Gain Verification
# ---------------------------------------------------------------------------
def test_top_actions_sorted_and_applying_top_action_yields_claimed_gain():
    """
    Checks that:
      1. Actions are sorted strictly descending by points_gained
      2. Applying the top action produces the EXACT claimed gain in overall score
    """
    # Setup initial state where resume has failed check 'CHK-PROFILE-LINKS' (worth 10 pts in resume rubric)
    # Resume score = 80 (earned 20.0 pts out of 25)
    # Fixing it gains 10 pts in Resume -> 10 * 0.25 = 2.5 pts in overall score
    failed_check = {
        "id": "CHK-PROFILE-LINKS",
        "label": "LeetCode & GitHub Profile Links",
        "pass": False,
        "evidence": "LeetCode link missing from resume.",
        "fix": "Add LeetCode profile link to contact header.",
    }
    inputs_before = {
        "resume": {"score": 80, "checks": [failed_check]},
        "projects": {"score": 80, "checks": []},
        "mock_interview": {"score": 80},
        "github": {"score": 80, "checks": []},
        "coding_practice": {"score": 80, "checks": []},
        "linkedin": {"score": 80, "checks": []},
        "co_curricular": {"score": 80, "checks": []},
    }
    res_before = calculate_readiness_formula(inputs_before)

    # Verify actions are sorted descending by points_gained
    actions = res_before["top_actions"]
    assert len(actions) > 0
    for i in range(len(actions) - 1):
        assert actions[i].points_gained >= actions[i + 1].points_gained

    top_act = actions[0]
    claimed_gain = top_act.points_gained
    assert top_act.id == "ACT-CHK-PROFILE-LINKS"
    assert claimed_gain == 2.5  # 10 pts in resume * 0.25 weight = 2.5 pts

    # Now apply the fix: Resume score increases from 80 to 90 (+10 in resume)
    inputs_after = {
        "resume": {"score": 90, "checks": [{**failed_check, "pass": True}]},
        "projects": {"score": 80, "checks": []},
        "mock_interview": {"score": 80},
        "github": {"score": 80, "checks": []},
        "coding_practice": {"score": 80, "checks": []},
        "linkedin": {"score": 80, "checks": []},
        "co_curricular": {"score": 80, "checks": []},
    }
    res_after = calculate_readiness_formula(inputs_after)

    realized_gain = round(res_after["raw_score"] - res_before["raw_score"], 2)
    assert realized_gain == claimed_gain, (
        f"Claimed gain {claimed_gain} does not match realized gain {realized_gain}"
    )


# ---------------------------------------------------------------------------
# 5. Database Integration & Progress Verification Flow
# ---------------------------------------------------------------------------
def test_progress_tracking_and_history_update(client: TestClient, db_session, student_user: User, student_auth_headers: dict):
    """
    Test progress:
      1. Establish baseline review with flawed resume (missing LeetCode link: score 80).
      2. Verify baseline readiness score snapshot (e.g. 1 point in history).
      3. Fix issue -> re-run review with score 90.
      4. Verify score rises by the expected weighted amount (2.5 pts).
      5. Verify a new history point appears in the database and history endpoint.
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

    # Initial readiness calculation
    snap1 = compute_and_save_readiness_score(db_session, student_user.id)
    initial_score = snap1.overall_score
    initial_raw = snap1.raw_score

    # Check history has 1 entry
    h1 = get_readiness_history(db_session, student_user.id)
    assert len(h1) == 1
    assert h1[0].overall_score == initial_score

    # 2. Fix the issue: new resume review with score = 90 (+10 points in resume)
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

    # Compute new snapshot
    snap2 = compute_and_save_readiness_score(db_session, student_user.id)
    new_raw = snap2.raw_score

    # Verify score rose by expected weighted amount: 10 * 0.25 = 2.5 points
    expected_delta = 10 * (WEIGHTS["resume"] / 100.0)  # 2.5
    assert round(new_raw - initial_raw, 2) == expected_delta

    # Check history now has 2 entries
    h2 = get_readiness_history(db_session, student_user.id)
    assert len(h2) == 2
    assert h2[0].id == snap1.id
    assert h2[1].id == snap2.id
    assert h2[1].overall_score >= h2[0].overall_score


# ---------------------------------------------------------------------------
# 6. API Endpoints & Consent Enforcement
# ---------------------------------------------------------------------------
def test_readiness_api_endpoints_and_consent(client: TestClient, db_session, student_user: User, student_auth_headers: dict):
    """Verifies GET /api/readiness/current, POST /recalculate, and GET /history."""
    # Ensure profile has consent
    profile = db_session.query(Profile).filter(Profile.user_id == student_user.id).first()
    if not profile:
        profile = Profile(user_id=student_user.id, consent_given=True)
        db_session.add(profile)
    else:
        profile.consent_given = True
    db_session.commit()

    # Current score endpoint
    resp = client.get("/api/readiness/current", headers=student_auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "overall_score" in data
    assert "level" in data
    assert "breakdown" in data
    assert "resume" in data["breakdown"]
    assert "projects" in data["breakdown"]
    assert "mock_interview" in data["breakdown"]

    # Recalculate endpoint
    recalc_resp = client.post("/api/readiness/recalculate", headers=student_auth_headers)
    assert recalc_resp.status_code == 200
    recalc_data = recalc_resp.json()
    assert recalc_data["overall_score"] == data["overall_score"]

    # History endpoint
    hist_resp = client.get("/api/readiness/history", headers=student_auth_headers)
    assert hist_resp.status_code == 200
    hist_list = hist_resp.json()
    assert isinstance(hist_list, list)
    assert len(hist_list) >= 1

    # Revoke consent and verify HTTP 403
    profile.consent_given = False
    db_session.commit()

    blocked = client.get("/api/readiness/current", headers=student_auth_headers)
    assert blocked.status_code == 403
    assert "Consent required" in blocked.json()["detail"]
