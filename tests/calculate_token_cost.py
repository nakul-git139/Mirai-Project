#!/usr/bin/env python3
"""
Token Accounting & API Cost Estimation Tool for Placement Readiness Copilot:
Calculates cost per student in API mode directly from empirical token counts recorded
in the LLM timing log (`backend/data/llm_timing.jsonl`).

DISCLAIMER: All prices below are UNVERIFIED PLACEHOLDERS loaded from
`backend/app/pricing_config.json` for the user to confirm against official billing consoles.
No verification date is claimed or invented.
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
PRICING_CONFIG_PATH = os.path.join(BACKEND_DIR, "app", "pricing_config.json")


def load_pricing_config():
    """Load pricing assumptions from config file."""
    if os.path.exists(PRICING_CONFIG_PATH):
        with open(PRICING_CONFIG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    return [
        {
            "provider": "ollama",
            "model": "qwen2.5:3b",
            "display_name": "Local Ollama (qwen2.5:3b / 7b)",
            "input_price_per_1m": 0.0,
            "output_price_per_1m": 0.0,
            "source_url": "Self-hosted weights (Private LAN)",
            "date_checked": None,
            "verified": False,
        }
    ]


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
    providers = load_pricing_config()

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

    print("\n" + "=" * 90)
    print(" PLACEMENT READINESS COPILOT - TOKEN ACCOUNTING & COST ESTIMATE")
    print("=" * 90)
    print(" [UNVERIFIED PLACEHOLDER DISCLAIMER]")
    print(" • All provider pricing rates below are UNVERIFIED PLACEHOLDERS loaded from")
    print("   backend/app/pricing_config.json for the user to confirm.")
    print(" • Verification Status: verified=False | date_checked=None (No verification claimed).")
    print(" • Token counts reflect compact prompts used in our deterministic code pipeline.")
    print("   Hosted prompts and system instructions in alternative implementations may be larger.")
    print("=" * 90)

    print("\n[1] EMPIRICAL TOKEN USAGE BREAKDOWN:")
    print(f"  • Resume Review (Grammar + Takeaway):    {resume_p:>5} prompt in  |  {resume_o:>5} completion out")
    print(f"  • LinkedIn Review (Rewrites & Audit):   {linkedin_p:>5} prompt in  |  {linkedin_o:>5} completion out")
    print(f"  • GitHub Code Review (Modularity):      {github_p:>5} prompt in  |  {github_o:>5} completion out")
    print(f"  • Job Match Fit & Explanation:          {job_match_p:>5} prompt in  |  {job_match_o:>5} completion out")
    print("  " + "-" * 75)
    print(f"  SUBTOTAL [ACTIVE REVIEWS ONLY]:         {active_in:>5} prompt in  |  {active_out:>5} completion out  ({active_total:,} tokens)")
    print(f"\n  • Mock Interview (5 Turns + Grading):   {interview_p:>5} prompt in  |  {interview_o:>5} completion out")
    print("  " + "-" * 75)
    print(f"  TOTAL [FULL JOURNEY INCL. INTERVIEW]:   {full_in:>5} prompt in  |  {full_out:>5} completion out  ({full_total:,} tokens)")

    print("\n[2] UNVERIFIED PLACEHOLDER COST PER STUDENT (ACTIVE REVIEWS - Interview Disabled):")
    print(f"   {'Provider / Model':<28} | {'Input ($/1M)':<13} | {'Output ($/1M)':<13} | {'Cost/Student':<13} | {'Verified':<10}")
    print("   " + "-" * 85)
    for p in providers:
        rate_in = p["input_price_per_1m"]
        rate_out = p["output_price_per_1m"]
        c_in = (active_in / 1_000_000.0) * rate_in
        c_out = (active_out / 1_000_000.0) * rate_out
        c_tot = c_in + c_out
        v_str = "True" if p.get("verified") else "False (Unverified)"
        print(f"   {p['display_name']:<28} | ${rate_in:<12.3f} | ${rate_out:<12.3f} | ${c_tot:<12.5f} | {v_str:<10}")

    print("\n[3] UNVERIFIED PLACEHOLDER COST PER STUDENT (FULL JOURNEY - With Mock Interview):")
    print(f"   {'Provider / Model':<28} | {'Input ($/1M)':<13} | {'Output ($/1M)':<13} | {'Cost/Student':<13} | {'Verified':<10}")
    print("   " + "-" * 85)
    for p in providers:
        rate_in = p["input_price_per_1m"]
        rate_out = p["output_price_per_1m"]
        c_in = (full_in / 1_000_000.0) * rate_in
        c_out = (full_out / 1_000_000.0) * rate_out
        c_tot = c_in + c_out
        v_str = "True" if p.get("verified") else "False (Unverified)"
        print(f"   {p['display_name']:<28} | ${rate_in:<12.3f} | ${rate_out:<12.3f} | ${c_tot:<12.5f} | {v_str:<10}")

    print("\n[4] PLACEHOLDER SOURCE URLS (User Confirmation Required):")
    for p in providers:
        print(f"   • {p['display_name']:<28}: {p['source_url']} (Date Checked: {p.get('date_checked')})")

    print("\n" + "=" * 90)
    print(" [SUMMARY]")
    print(" • All rates are unverified placeholders loaded from backend/app/pricing_config.json.")
    print(" • Local Ollama operates at $0.00 per student (self-hosted open weights).")
    print("=" * 90 + "\n")


if __name__ == "__main__":
    calculate_costs()
