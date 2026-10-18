from __future__ import annotations
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

from sqlalchemy.orm import Session

from pydantic import BaseModel, Field

from app.models import InterviewSession, Profile, User
from app.llm.factory import get_llm_adapter
from app.llm.base import LLMMessage
from app.llm.structured import generate_structured_output
from app.services.readiness_service import compute_and_save_readiness_score

logger = logging.getLogger(__name__)

# Fixed Per-Answer Rubric Definition (Sum = 100)
RUBRIC_CRITERIA = {
    "CRIT-TECH-DEPTH": {
        "id": "CRIT-TECH-DEPTH",
        "name": "Technical Accuracy & Depth",
        "max_score": 35.0,
        "weight_pct": 35,
        "description": "Correctness of technical concepts, appropriate architecture/framework usage, and depth of explanation.",
    },
    "CRIT-CLARITY-COMM": {
        "id": "CRIT-CLARITY-COMM",
        "name": "Communication & Structure",
        "max_score": 25.0,
        "weight_pct": 25,
        "description": "Structured delivery (e.g. STAR method for behavioral, direct logical progression for technical), concise and coherent articulation.",
    },
    "CRIT-GROUNDED-EXP": {
        "id": "CRIT-GROUNDED-EXP",
        "name": "Grounded Experience & Relevance",
        "max_score": 25.0,
        "weight_pct": 25,
        "description": "Citing real projects, tools, metrics, repositories, or personal contributions vs generic hand-waving.",
    },
    "CRIT-CRITICAL-THINK": {
        "id": "CRIT-CRITICAL-THINK",
        "name": "Problem-Solving & Trade-offs",
        "max_score": 15.0,
        "weight_pct": 15,
        "description": "Explaining 'why', trade-offs, edge cases, alternatives considered, and architectural decisions.",
    },
}


def build_question_roadmap(profile: Optional[Profile], target_role: Optional[str] = None) -> List[Dict[str, Any]]:
    """
    Generates a personalized question roadmap based directly on the candidate's
    actual resume, parsed projects, declared skills, and target role.
    Guarantees:
      - Technical questions (specific to student's skills/stack)
      - Project deep-dive questions (explicitly referencing student's project names)
      - 1-2 HR/behavioral questions (STAR format)
    """
    role = target_role or (profile.target_roles[0] if (profile and profile.target_roles) else "Full Stack Software Engineer")
    
    # Extract projects
    projects = []
    if profile:
        projects = list(profile.projects or [])
        if not projects and profile.parsed_resume:
            projects = list(profile.parsed_resume.get("projects", []))

    # Extract skills
    skills = []
    if profile:
        skills = list(profile.skills or [])
        if not skills and profile.parsed_resume:
            skills = list(profile.parsed_resume.get("skills", []))
    
    # Normalization
    skill_names = [s.strip() for s in skills if s.strip()]
    if not skill_names:
        skill_names = ["Python", "FastAPI", "React", "PostgreSQL", "Docker", "Git"]

    project_titles = []
    for p in projects:
        if isinstance(p, dict):
            title = p.get("title") or p.get("name")
            if title:
                project_titles.append(title.strip())
        elif isinstance(p, str):
            project_titles.append(p.strip())

    if not project_titles:
        project_titles = ["Readiness Copilot", "Distributed Task Queue"]

    primary_project = project_titles[0]
    secondary_project = project_titles[1] if len(project_titles) > 1 else project_titles[0]
    primary_skills = ", ".join(skill_names[:3])
    secondary_skill = skill_names[1] if len(skill_names) > 1 else "REST APIs"

    roadmap = [
        {
            "id": "Q1",
            "type": "technical",
            "question": f"To begin our technical discussion for the {role} position: Can you explain how you design and structure scalable backend services or APIs using {primary_skills}? What key architectural principles do you prioritize for performance and reliability?",
            "context": f"Evaluates foundational core concepts and backend architecture aligned with declared skills: {primary_skills}.",
            "target_topics": skill_names[:3],
        },
        {
            "id": "Q2",
            "type": "project_deep_dive",
            "question": f"In your portfolio, you built '{primary_project}'. Walk me through how you deployed this project from development to production. What architectural challenges did you encounter, and how did you resolve them?",
            "context": f"Project deep-dive examining deployment, infrastructure, and technical execution of candidate project '{primary_project}'.",
            "target_topics": [primary_project],
        },
        {
            "id": "Q3",
            "type": "project_deep_dive",
            "question": f"Continuing on your technical work, looking at '{secondary_project}': Walk me through your data flow, concurrency, or state management strategy. If you had to scale this system to handle 10x the traffic, what specific bottlenecks would you tackle first?",
            "context": f"Project deep-dive examining scalability, bottlenecks, and state management in '{secondary_project}'.",
            "target_topics": [secondary_project],
        },
        {
            "id": "Q4",
            "type": "technical",
            "question": f"When building high-concurrency features with {secondary_skill}, how do you handle asynchronous operations, error boundaries, and database query optimization to prevent latency spikes?",
            "context": f"Technical interrogation of asynchronous execution and performance optimization with {secondary_skill}.",
            "target_topics": [secondary_skill],
        },
        {
            "id": "Q5",
            "type": "hr_behavioral",
            "question": "Tell me about a challenging situation where you faced a tight project deadline, unexpected technical roadblock, or team disagreement. How did you handle the situation, and what was the outcome? (Feel free to use the STAR method).",
            "context": "Evaluates behavioral competence, conflict resolution, accountability, and communication under pressure.",
            "target_topics": ["STAR", "teamwork", "conflict resolution"],
        },
    ]

    return roadmap


def evaluate_student_answer(
    question_obj: Dict[str, Any],
    answer_text: str,
    llm_adapter: Optional[Any] = None,
) -> Dict[str, Any]:
    """
    Evaluates a student's answer using the fixed per-answer benchmark rubric.
    Deterministic-first with LLM subjective calibration:
      - Evaluates length, specificity, technical keyword presence, and STAR structure.
      - Calls LLM adapter at temperature=0 with structured schema if available.
      - Returns score (0-100), criteria breakdown, feedback summary, and adaptive follow-up.
    """
    clean_text = (answer_text or "").strip()
    words = clean_text.split()
    word_count = len(words)
    q_type = question_obj.get("type", "technical")
    q_text = question_obj.get("question", "")

    # Edge Case: Extremely short / one-word answers (e.g. "yes", "i used python")
    if word_count < 5:
        criteria_scores = [
            {
                "criterion_id": "CRIT-TECH-DEPTH",
                "name": "Technical Accuracy & Depth",
                "score": 10.0,
                "max_score": 35.0,
                "feedback": "Answer is too brief (< 5 words) to demonstrate technical depth or mastery.",
            },
            {
                "criterion_id": "CRIT-CLARITY-COMM",
                "name": "Communication & Structure",
                "score": 10.0,
                "max_score": 25.0,
                "feedback": "Single-phrase or one-word response lacks structure and professional articulation.",
            },
            {
                "criterion_id": "CRIT-GROUNDED-EXP",
                "name": "Grounded Experience & Relevance",
                "score": 5.0,
                "max_score": 25.0,
                "feedback": "No concrete examples, project artifacts, or metrics provided.",
            },
            {
                "criterion_id": "CRIT-CRITICAL-THINK",
                "name": "Problem-Solving & Trade-offs",
                "score": 5.0,
                "max_score": 15.0,
                "feedback": "No discussion of trade-offs, constraints, or design decisions.",
            },
        ]
        total_score = 30
        summary = "Answer was too brief to evaluate properly. Expand with specific technical details and examples."
        adaptive_followup = "Could you elaborate further on that? In an interview, sharing the specific technologies, steps, and decisions you took helps showcase your engineering depth."
        return {
            "score": total_score,
            "criteria": criteria_scores,
            "summary": summary,
            "adaptive_followup": adaptive_followup,
            "is_weak": True,
        }

    # Deterministic heuristics baseline
    tech_keywords = [
        "api", "database", "sql", "cache", "redis", "docker", "test", "latency",
        "react", "python", "fastapi", "deploy", "server", "architecture", "query",
        "index", "pipeline", "component", "async", "await", "rest", "git", "ci/cd",
        "microservice", "security", "schema", "scale", "performance", "metric"
    ]
    matched_tech = [k for k in tech_keywords if k in clean_text.lower()]
    has_metrics = any(char.isdigit() for char in clean_text) or any(t in clean_text.lower() for t in ["%", "ms", "users", "seconds", "reduced", "improved"])
    star_indicators = any(term in clean_text.lower() for term in ["situation", "task", "action", "result", "when i was", "my role", "the outcome", "we resolved", "i decided"])

    # LLM Structured Evaluation Prompt
    prompt = f"""You are an expert technical interviewer evaluating a student candidate's interview answer.
Question Type: {q_type}
Question Asked: {q_text}
Student's Answer: {clean_text}

Evaluate the student's answer strictly against these 4 fixed rubric criteria:
1. CRIT-TECH-DEPTH (max 35 pts): Technical depth, correct concepts, architectural rigor.
2. CRIT-CLARITY-COMM (max 25 pts): Structured delivery, coherence, STAR framing for behavioral.
3. CRIT-GROUNDED-EXP (max 25 pts): Citing real projects, tools, metrics, concrete implementation.
4. CRIT-CRITICAL-THINK (max 15 pts): Trade-offs, design rationale, alternatives considered.

Scoring calibration anchors:
- Strong answer (detailed, mentions architecture/STAR, specific tools/metrics): Total 80 - 100
- Mediocre / weak answer (generic, few details, superficial): Total 45 - 65
- Off-topic or evasive answer (does not address the question, rambling): Total 15 - 40

Provide constructive feedback and, if appropriate, a natural adaptive follow-up question that an interviewer would ask next.
"""

    class LLMAnswerEvaluation(BaseModel):
        tech_depth_score: float = Field(ge=0, le=35, default=20.0)
        tech_depth_feedback: str = ""
        clarity_score: float = Field(ge=0, le=25, default=15.0)
        clarity_feedback: str = ""
        grounded_exp_score: float = Field(ge=0, le=25, default=15.0)
        grounded_exp_feedback: str = ""
        critical_think_score: float = Field(ge=0, le=15, default=10.0)
        critical_think_feedback: str = ""
        summary: str = ""
        adaptive_followup: Optional[str] = None
        is_off_topic: bool = False

    try:
        adapter = llm_adapter or get_llm_adapter()
        eval_obj: LLMAnswerEvaluation = generate_structured_output(
            adapter=adapter,
            prompt=prompt,
            schema=LLMAnswerEvaluation,
            system_prompt="You are a strict, objective interview evaluator who produces structured JSON adhering to official placement rubrics.",
            temperature=0.0,
            max_retries=1,
        )

        c1 = min(35.0, max(0.0, float(eval_obj.tech_depth_score)))
        c2 = min(25.0, max(0.0, float(eval_obj.clarity_score)))
        c3 = min(25.0, max(0.0, float(eval_obj.grounded_exp_score)))
        c4 = min(15.0, max(0.0, float(eval_obj.critical_think_score)))
        total = int(round(c1 + c2 + c3 + c4))

        criteria_scores = [
            {
                "criterion_id": "CRIT-TECH-DEPTH",
                "name": "Technical Accuracy & Depth",
                "score": c1,
                "max_score": 35.0,
                "feedback": eval_obj.tech_depth_feedback or "Demonstrates adequate technical concepts.",
            },
            {
                "criterion_id": "CRIT-CLARITY-COMM",
                "name": "Communication & Structure",
                "score": c2,
                "max_score": 25.0,
                "feedback": eval_obj.clarity_feedback or "Delivery is structured and understandable.",
            },
            {
                "criterion_id": "CRIT-GROUNDED-EXP",
                "name": "Grounded Experience & Relevance",
                "score": c3,
                "max_score": 25.0,
                "feedback": eval_obj.grounded_exp_feedback or "Grounds statements in real tools and experiences.",
            },
            {
                "criterion_id": "CRIT-CRITICAL-THINK",
                "name": "Problem-Solving & Trade-offs",
                "score": c4,
                "max_score": 15.0,
                "feedback": eval_obj.critical_think_feedback or "Discusses decisions and considerations.",
            },
        ]

        return {
            "score": total,
            "criteria": criteria_scores,
            "summary": eval_obj.summary or "Solid answer demonstrating foundational skills.",
            "adaptive_followup": eval_obj.adaptive_followup or "That is insightful. How did you measure or validate the impact of that approach?",
            "is_weak": total < 55,
        }

    except Exception as e:
        logger.warning(f"LLM interview evaluation fallback activated: {e}")
        # Deterministic fallback calculation
        c1 = 28.0 if len(matched_tech) >= 3 else (18.0 if len(matched_tech) >= 1 else 10.0)
        c2 = 22.0 if word_count >= 40 else (15.0 if word_count >= 15 else 8.0)
        c3 = 22.0 if (has_metrics or len(matched_tech) >= 2) else 12.0
        c4 = 13.0 if ("trade" in clean_text.lower() or "because" in clean_text.lower() or "challenge" in clean_text.lower()) else 7.0
        total = int(round(c1 + c2 + c3 + c4))

        return {
            "score": total,
            "criteria": [
                {
                    "criterion_id": "CRIT-TECH-DEPTH",
                    "name": "Technical Accuracy & Depth",
                    "score": c1,
                    "max_score": 35.0,
                    "feedback": f"Detected technical keywords: {', '.join(matched_tech[:4]) or 'general software terminology'}.",
                },
                {
                    "criterion_id": "CRIT-CLARITY-COMM",
                    "name": "Communication & Structure",
                    "score": c2,
                    "max_score": 25.0,
                    "feedback": f"Response length ({word_count} words) provided sufficient context.",
                },
                {
                    "criterion_id": "CRIT-GROUNDED-EXP",
                    "name": "Grounded Experience & Relevance",
                    "score": c3,
                    "max_score": 25.0,
                    "feedback": "Referenced concrete tools and deployment steps." if has_metrics else "Could include more quantifiable metrics.",
                },
                {
                    "criterion_id": "CRIT-CRITICAL-THINK",
                    "name": "Problem-Solving & Trade-offs",
                    "score": c4,
                    "max_score": 15.0,
                    "feedback": "Explained reasons behind technical implementation choices.",
                },
            ],
            "summary": "Completed rubric evaluation based on response content.",
            "adaptive_followup": f"Could you walk me through the trade-offs you considered when implementing this?",
            "is_weak": total < 55,
        }


def synthesize_session_feedback(rubric_scores: List[Dict[str, Any]], target_role: str) -> Dict[str, Any]:
    """
    Synthesizes overall strengths, weak areas, and actionable improvement tips
    from individual question rubric scores.
    """
    if not rubric_scores:
        return {
            "strengths": ["Demonstrated willingness to practice technical interview simulations."],
            "weaknesses": ["Session was ended before completing enough questions to establish detailed trends."],
            "tips": ["Complete a full 15 or 20-minute mock interview session to evaluate all core competencies."],
            "rubric_averages": {cid: 0.0 for cid in RUBRIC_CRITERIA},
        }

    # Aggregate criteria averages
    criteria_totals: Dict[str, float] = {cid: 0.0 for cid in RUBRIC_CRITERIA}
    criteria_counts: Dict[str, int] = {cid: 0 for cid in RUBRIC_CRITERIA}

    for item in rubric_scores:
        for c in item.get("criteria", []):
            cid = c.get("criterion_id")
            if cid in criteria_totals:
                criteria_totals[cid] += float(c.get("score", 0.0))
                criteria_counts[cid] += 1

    averages = {}
    for cid, total in criteria_totals.items():
        count = max(1, criteria_counts[cid])
        averages[cid] = round(total / count, 1)

    strengths = []
    weaknesses = []
    tips = []

    # 1. Tech Depth
    if averages.get("CRIT-TECH-DEPTH", 0) >= 25.0:
        strengths.append(f"Strong command of core {target_role} frameworks, terminology, and system architecture.")
    else:
        weaknesses.append("Superficial explanations of architectural principles; needs deeper technical precision.")
        tips.append("Deepen explanations of how underlying tools work under the hood (e.g. database indexing, async loops, caching layers).")

    # 2. Clarity
    if averages.get("CRIT-CLARITY-COMM", 0) >= 18.0:
        strengths.append("Structured and coherent communication style with clear logical progression.")
    else:
        weaknesses.append("Answers occasionally lack clear structure or rely on fragmented thoughts.")
        tips.append("Use the STAR framework (Situation, Task, Action, Result) for behavioral questions to keep answers concise and punchy.")

    # 3. Grounded Experience
    if averages.get("CRIT-GROUNDED-EXP", 0) >= 18.0:
        strengths.append("Consistently grounds claims in real projects, repositories, and measurable outcomes.")
    else:
        weaknesses.append("Heavy reliance on generic hypothetical statements rather than personal portfolio evidence.")
        tips.append("Name-drop exact tools, libraries, and quantifiable results from your projects (e.g. 'reduced latency by 35%', 'deployed on AWS with Docker').")

    # 4. Critical Thinking
    if averages.get("CRIT-CRITICAL-THINK", 0) >= 10.0:
        strengths.append("Demonstrates maturity by proactively discussing trade-offs, edge cases, and design constraints.")
    else:
        weaknesses.append("Rarely mentions why certain technical choices were made or what alternatives were rejected.")
        tips.append("Always explain the 'why': why did you pick this database/framework over alternatives, and what are the trade-offs?")

    if not strengths:
        strengths.append("Engaged actively with the interview questions and attempted all assigned topics.")
    if not weaknesses:
        weaknesses.append("Maintain consistency across more complex distributed systems scenarios.")
    if not tips:
        tips.append("Practice timing your answers to stay between 90 and 150 seconds per response.")

    return {
        "strengths": strengths,
        "weaknesses": weaknesses,
        "tips": tips,
        "rubric_averages": averages,
    }


def start_interview_session(
    db: Session,
    user: User,
    duration_minutes: int = 15,
    time_limit_seconds: Optional[int] = None,
    target_role: Optional[str] = None,
) -> InterviewSession:
    """
    Initializes a new Mock Interview Session:
      - Validates consent
      - Generates personalized question roadmap
      - Seeds initial interviewer greeting & Q1
      - Sets timer boundaries
    """
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not profile or not profile.consent_given:
        raise PermissionError("Student consent is required before starting a mock interview simulation.")

    # Abandon any existing in_progress session for this user so they don't have zombie sessions
    db.query(InterviewSession).filter(
        InterviewSession.user_id == user.id,
        InterviewSession.status == "in_progress",
    ).update({"status": "abandoned"})
    db.commit()

    role = target_role or (profile.target_roles[0] if profile.target_roles else "Full Stack Software Engineer")
    roadmap = build_question_roadmap(profile, target_role=role)
    
    # Calculate timer limit
    actual_seconds = time_limit_seconds if (time_limit_seconds and time_limit_seconds > 0) else (duration_minutes * 60)
    now = datetime.utcnow()
    expires_at = now + timedelta(seconds=actual_seconds)

    q1 = roadmap[0]
    initial_message = {
        "role": "interviewer",
        "content": f"Hello! Welcome to your mock interview simulation for the {role} position. We have {duration_minutes} minutes allocated today. Let's get started:\n\n{q1['question']}",
        "timestamp": now.isoformat(),
        "question_id": q1["id"],
    }

    session = InterviewSession(
        user_id=user.id,
        target_role=role,
        duration_minutes=duration_minutes,
        time_limit_seconds=actual_seconds,
        expires_at=expires_at,
        status="in_progress",
        current_question_index=0,
        question_plan=roadmap,
        messages=[initial_message],
        rubric_scores=[],
        feedback=None,
        score=None,
        created_at=now,
        updated_at=now,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def process_student_message(
    db: Session,
    session: InterviewSession,
    message_text: str,
    llm_adapter: Optional[Any] = None,
) -> Tuple[InterviewSession, Dict[str, Any]]:
    """
    Processes a student answer:
      - Checks timer (auto-ends if expired)
      - Evaluates answer against fixed rubric
      - Generates adaptive follow-up or advances to next question
      - Persists state and updates readiness if ended
    """
    now = datetime.utcnow()
    
    # Check if timer has expired
    if session.expires_at and now >= session.expires_at:
        logger.info(f"Interview session {session.id} timer expired.")
        session = end_interview_session(db, session, reason="timer_expired")
        return session, {
            "role": "interviewer",
            "content": "Time is up! Our interview session has concluded. I have evaluated your responses and generated your performance breakdown below.",
            "is_ended": True,
            "evaluation": None,
        }

    roadmap = session.question_plan or []
    current_idx = session.current_question_index or 0
    current_q = roadmap[current_idx] if current_idx < len(roadmap) else roadmap[-1]

    # Evaluate answer against fixed rubric
    eval_result = evaluate_student_answer(current_q, message_text, llm_adapter=llm_adapter)

    # Append student message
    student_msg = {
        "role": "student",
        "content": message_text,
        "timestamp": now.isoformat(),
        "question_id": current_q.get("id"),
        "evaluation": eval_result,
    }
    
    # Update rubric scores list
    rubric_entry = {
        "question_id": current_q.get("id"),
        "question_text": current_q.get("question"),
        "question_type": current_q.get("type"),
        "score": eval_result["score"],
        "criteria": eval_result["criteria"],
        "summary": eval_result["summary"],
    }
    updated_rubric_scores = list(session.rubric_scores or [])
    updated_rubric_scores.append(rubric_entry)
    session.rubric_scores = updated_rubric_scores

    messages = list(session.messages or [])
    messages.append(student_msg)

    # Check if there are more questions or if we should conclude
    next_idx = current_idx + 1
    session.current_question_index = next_idx

    # Check if all questions completed
    if next_idx >= len(roadmap):
        # Conclude session
        session.messages = messages
        session = end_interview_session(db, session, reason="completed")
        interviewer_reply = {
            "role": "interviewer",
            "content": f"Thank you for sharing those insights! That completes all our questions for this interview. Let me summarize your results and placement readiness score.",
            "timestamp": datetime.utcnow().isoformat(),
            "is_ended": True,
            "evaluation": eval_result,
        }
        messages.append(interviewer_reply)
        session.messages = messages
        db.commit()
        db.refresh(session)
        return session, interviewer_reply

    # Advance to next question or ask adaptive follow-up
    next_q = roadmap[next_idx]
    
    # Adaptive follow-up phrasing if answer was weak or raised an interesting point
    transition = ""
    if eval_result.get("is_weak"):
        transition = "Thanks for that initial response. Let's explore your practical experience a bit further: "
    else:
        transition = "Great explanation. Moving to the next area: "

    interviewer_reply_text = f"{transition}\n\n{next_q['question']}"
    interviewer_msg = {
        "role": "interviewer",
        "content": interviewer_reply_text,
        "timestamp": datetime.utcnow().isoformat(),
        "question_id": next_q.get("id"),
        "is_ended": False,
        "evaluation": eval_result,
    }
    messages.append(interviewer_msg)
    session.messages = messages
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)
    return session, interviewer_msg


def end_interview_session(db: Session, session: InterviewSession, reason: str = "completed") -> InterviewSession:
    """
    Concludes an interview session, computes final score as average of rubric scores,
    synthesizes feedback, persists transcript, and updates student's readiness score.
    """
    if session.status == "completed":
        return session

    scores = session.rubric_scores or []
    if scores:
        avg_score = int(round(sum(float(s.get("score", 0)) for s in scores) / len(scores)))
        final_score = max(0, min(100, avg_score))
    else:
        final_score = 0

    feedback = synthesize_session_feedback(scores, session.target_role)
    feedback["reason"] = reason

    session.status = "completed"
    session.score = final_score
    session.feedback = feedback
    session.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(session)

    # Auto-recalculate student's placement readiness score!
    try:
        compute_and_save_readiness_score(db, session.user_id)
        logger.info(f"Readiness score recalculated for user {session.user_id} after interview completion.")
    except Exception as e:
        logger.error(f"Failed to auto-update readiness score for user {session.user_id}: {e}")

    return session


def get_active_session_for_user(db: Session, user_id: int) -> Optional[InterviewSession]:
    """Finds an in-progress session for the user, checking for timer expiration."""
    session = (
        db.query(InterviewSession)
        .filter(InterviewSession.user_id == user_id, InterviewSession.status == "in_progress")
        .order_by(InterviewSession.id.desc())
        .first()
    )
    if not session:
        return None

    # Check if timer has expired
    if session.expires_at and datetime.utcnow() >= session.expires_at:
        logger.info(f"Active session {session.id} found expired upon retrieval. Auto-closing.")
        return end_interview_session(db, session, reason="timer_expired")

    return session
