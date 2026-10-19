from __future__ import annotations
import os
import sys
import fitz

sys.path.insert(0, os.path.abspath("backend"))

from tests.create_fixtures import FIXTURES_DIR, generate_all_fixtures
import re
from app.services.resume_reviewer import identify_sections

def inspect():
    generate_all_fixtures()
    pdf_path = os.path.join(FIXTURES_DIR, "resume_good.pdf")
    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    doc = fitz.open(stream=pdf_bytes, filetype="pdf")
    full_text = "\n\n".join(p.get_text("text") for p in doc)

    print("=" * 70)
    print("A. FULL TEXT EXTRACTED FROM resume_good.pdf")
    print(f"Total Character Count: {len(full_text)}")
    print(f"Total Word Count: {len(full_text.split())}")
    print("=" * 70)
    print(full_text)

    sections = identify_sections(full_text)
    exp_text = sections.get("experience", "")
    proj_text = sections.get("projects", "")
    content = exp_text + "\n" + proj_text
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    bullet_lines = []
    for line in lines:
        if line.startswith(("-", "•", "*", "–")) or re.match(r"^\d+\.", line):
            cleaned = re.sub(r"^[-•*–\d.]+\s*", "", line).strip()
            if cleaned.lower().startswith(("tech stack:", "technologies:", "tools:", "stack:")):
                continue
            if len(cleaned) > 15:
                bullet_lines.append(f"- {cleaned}")

    selected_bullets = bullet_lines[:4]
    model_prompt = "Proofread these bullet lines for grammatical correctness and professionalism:\n" + "\n".join(selected_bullets)

    print("\n" + "=" * 70)
    print("B. FULL TEXT SENT TO THE MODEL FOR 'resume_review_grammar'")
    print(f"Total Prompt Characters: {len(model_prompt)}")
    print(f"Total Prompt Words: {len(model_prompt.split())}")
    print("=" * 70)
    print(model_prompt)

    print("\n" + "=" * 70)
    print("C. COVERAGE CONFIRMATION")
    print("=" * 70)
    print(f"- Full Resume Length:    {len(full_text)} characters, {len(full_text.split())} words")
    print(f"- Sent to Model:        {len(model_prompt)} characters, {len(model_prompt.split())} words")
    print(f"- Coverage Percentage:  {len(model_prompt) / len(full_text) * 100:.1f}% of characters")
    print("\nSections NOT sent to the model:")
    print("  1. Contact Header (Name, Phone, Email, Location)")
    print("  2. Profile Links (GitHub URL, LeetCode URL, Portfolio URL)")
    print("  3. Education Section (University, Degree, GPA, Coursework)")
    print("  4. Technical Skills Section (Languages, Frameworks, Developer Tools)")
    print("  5. Co-curricular Achievements Section (Awards, Hackathons, Certifications)")
    print("\nConclusion: ONLY A TRUNCATED PART (the primary 3-4 accomplishment bullets from Experience/Projects) is sent to the model, NOT the whole resume.")

if __name__ == "__main__":
    inspect()
