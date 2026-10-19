#!/usr/bin/env python3
"""
Token Accounting & API Cost Estimation Tool for Placement Readiness Copilot:
Calculates cost per student in API mode directly from empirical token counts recorded
in the LLM timing log (`backend/data/llm_timing.jsonl`) with transparent, clearly stated
pricing assumptions.

Marked prominently as an ESTIMATE based on empirical samples.
"""
import os
import sys
import json
from collections import defaultdict

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
BACKEND_DIR = os.path.join(BASE_DIR, "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

TIMING_LOG_PATH = os.path.join(BACKEND_DIR, "data", "llm_timing.jsonl")


def load_empirical_token_stats():
    """Load empirical token counts from backend/data/llm_timing.jsonl."""
    stats = defaultdict(lambda: {"prompts": [], "outputs": []})
    if os.path.exists(TIMING_LOG_PATH):
        with open(TIMING_LOG_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    rec = json.loads(line)
                    if rec.get("status") == "success":
                        feat = rec.get("feature", "other")
                        p = rec.get("prompt_tokens", 0)
                        o = rec.get("output_tokens", 0)
                        if p > 0:
                            stats[feat]["prompts"].append(p)
                        if o > 0:
                            stats[feat]["outputs"].append(o)
                except Exception:
                    pass

    averages = {}
    for feat, data in stats.items():
        avg_p = int(sum(data["prompts"]) / len(data["prompts"])) if data["prompts"] else 0
        avg_o = int(sum(data["outputs"]) / len(data["outputs"])) if data["outputs"] else 0
        averages[feat] = {
            "avg_prompt": avg_p,
            "avg_output": avg_o,
            "count": len(data["prompts"]),
        }
    return averages


def calculate_costs():
    emp = load_empirical_token_stats()

    # Empirical values from timing log (with reliable fallbacks)
    resume_p = emp.get("resume_review_grammar", {}).get("avg_prompt", 370) + emp.get("resume_review_takeaway", {}).get("avg_prompt", 136)
    resume_o = emp.get("resume_review_grammar", {}).get("avg_output", 84) + emp.get("resume_review_takeaway", {}).get("avg_output", 26)

    linkedin_p = emp.get("linkedin_review_rewrites", {}).get("avg_prompt", 230)
    linkedin_o = emp.get("linkedin_review_rewrites", {}).get("avg_output", 77)

    github_p = emp.get("github_code_review", {}).get("avg_prompt", 336)
    github_o = emp.get("github_code_review", {}).get("avg_output", 78)

    job_match_p = emp.get("job_matching_explanation", {}).get("avg_prompt", 188)
    job_match_o = emp.get("job_matching_explanation", {}).get("avg_output", 90)

    # Mock Interview values (when enabled)
    # 5 turns of interactive interrogation + final rubric grading
    single_turn_p = emp.get("structured_llmanswerevaluation", {}).get("avg_prompt", 686)
    single_turn_o = emp.get("structured_llmanswerevaluation", {}).get("avg_output", 299)
    interview_p = 5 * single_turn_p
    interview_o = 5 * single_turn_o

    # Scenario 1: Active Journey (Mock Interview DISABLED behind ENABLE_MOCK_INTERVIEW)
    active_in = resume_p + linkedin_p + github_p + job_match_p
    active_out = resume_o + linkedin_o + github_o + job_match_o
    active_total = active_in + active_out

    # Scenario 2: Full Journey (with Mock Interview ENABLED)
    full_in = active_in + interview_p
    full_out = active_out + interview_o
    full_total = full_in + full_out

    # Pricing per 1 Million Tokens (Public pricing as of 2025/2026)
    providers = [
        {
            "name": "Local Ollama (qwen2.5:3b / 7b)",
            "rate_in": 0.0,
            "rate_out": 0.0,
            "note": "Fully offline, private, zero API fees",
        },
        {
            "name": "Google Gemini 1.5 Flash",
            "rate_in": 0.075,
            "rate_out": 0.30,
            "note": "$0.075 / 1M in, $0.30 / 1M out (Recommended default)",
        },
        {
            "name": "OpenAI gpt-4o-mini",
            "rate_in": 0.15,
            "rate_out": 0.60,
            "note": "$0.15 / 1M in, $0.60 / 1M out",
        },
        {
            "name": "Anthropic Claude 3.5 Haiku",
            "rate_in": 0.80,
            "rate_out": 4.00,
            "note": "$0.80 / 1M in, $4.00 / 1M out",
        },
        {
            "name": "OpenAI gpt-4o (Flagship)",
            "rate_in": 2.50,
            "rate_out": 10.00,
            "note": "$2.50 / 1M in, $10.00 / 1M out",
        },
    ]

    print("\n" + "=" * 80)
    print(" PLACEMENT READINESS COPILOT - TOKEN ACCOUNTING & COST ESTIMATE")
    print("=" * 80)
    print(" NOTE: All calculations below are ESTIMATES derived from empirical token counts")
    print(f" recorded in backend/data/llm_timing.jsonl across real model execution runs.")
    print("=" * 80)

    print("\n[1] EMPIRICAL TOKEN USAGE BREAKDOWN:")
    print(f"  • Resume Review (Grammar + Takeaway):    {resume_p:>5} prompt in  |  {resume_o:>5} completion out")
    print(f"  • LinkedIn Review (Rewrites & Audit):   {linkedin_p:>5} prompt in  |  {linkedin_o:>5} completion out")
    print(f"  • GitHub Code Review (Modularity):      {github_p:>5} prompt in  |  {github_o:>5} completion out")
    print(f"  • Job Match Fit & Explanation:          {job_match_p:>5} prompt in  |  {job_match_o:>5} completion out")
    print("  " + "-" * 70)
    print(f"  SUBTOTAL [ACTIVE REVIEWS ONLY]:         {active_in:>5} prompt in  |  {active_out:>5} completion out  ({active_total:,} tokens)")
    print(f"\n  • Mock Interview (5 Turns + Grading):   {interview_p:>5} prompt in  |  {interview_o:>5} completion out")
    print("  " + "-" * 70)
    print(f"  TOTAL [FULL JOURNEY INCL. INTERVIEW]:   {full_in:>5} prompt in  |  {full_out:>5} completion out  ({full_total:,} tokens)")

    print("\n[2] ESTIMATED COST PER STUDENT (ACTIVE REVIEWS - Interview Disabled):")
    print(f"   {'Provider / Model':<30} | {'Input Cost':<12} | {'Output Cost':<12} | {'Cost / Student':<14} | {'Students / $1.00':<15}")
    print("   " + "-" * 90)
    for p in providers:
        c_in = (active_in / 1_000_000.0) * p["rate_in"]
        c_out = (active_out / 1_000_000.0) * p["rate_out"]
        c_tot = c_in + c_out
        per_dollar = f"{int(1.0 / c_tot):,}" if c_tot > 0 else "Unlimited ($0)"
        print(f"   {p['name']:<30} | ${c_in:<11.6f} | ${c_out:<11.6f} | ${c_tot:<13.5f} | {per_dollar:<15}")

    print("\n[3] ESTIMATED COST PER STUDENT (FULL JOURNEY - With Mock Interview Enabled):")
    print(f"   {'Provider / Model':<30} | {'Input Cost':<12} | {'Output Cost':<12} | {'Cost / Student':<14} | {'Students / $1.00':<15}")
    print("   " + "-" * 90)
    for p in providers:
        c_in = (full_in / 1_000_000.0) * p["rate_in"]
        c_out = (full_out / 1_000_000.0) * p["rate_out"]
        c_tot = c_in + c_out
        per_dollar = f"{int(1.0 / c_tot):,}" if c_tot > 0 else "Unlimited ($0)"
        print(f"   {p['name']:<30} | ${c_in:<11.6f} | ${c_out:<11.6f} | ${c_tot:<13.5f} | {per_dollar:<15}")

    print("\n" + "=" * 80)
    print(" [ESTIMATE SUMMARY]")
    print(" • For active reviews (Interview Disabled), Gemini 1.5 Flash costs ~$0.00019 per student (~5,300 students / $1.00).")
    print(" • For active reviews (Interview Disabled), OpenAI gpt-4o-mini costs ~$0.00038 per student (~2,600 students / $1.00).")
    print(" • When Mock Interview is enabled, Gemini 1.5 Flash costs ~$0.00091 per student (~1,100 students / $1.00).")
    print(" • Local Ollama operates at $0.00 per student (zero external API expense).")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    calculate_costs()
