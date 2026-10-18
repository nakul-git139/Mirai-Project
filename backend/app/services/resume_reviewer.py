from __future__ import annotations
import io
import os
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
import fitz  # PyMuPDF
import docx

from app.schemas import ReviewCheck
from app.llm.base import BaseLLMAdapter, LLMMessage
from app.llm.factory import get_llm_adapter
from app.services.profile_parser import (
    identify_sections,
    extract_skills_from_text,
    extract_projects_from_text,
    COMMON_SKILLS,
)

logger = logging.getLogger(__name__)

# Action verbs commonly expected on technical resumes
STRONG_ACTION_VERBS = {
    "accelerated", "architected", "automated", "authored", "benchmarked",
    "built", "configured", "constructed", "containerized", "created",
    "delivered", "deployed", "designed", "developed", "engineered",
    "executed", "implemented", "improved", "increased", "indexed",
    "integrated", "launched", "led", "maintained", "mentored",
    "migrated", "modeled", "monitored", "optimized", "orchestrated",
    "overhauled", "programmed", "published", "reduced", "refactored",
    "resolved", "scaled", "secured", "spearheaded", "standardized",
    "streamlined", "structured", "tested", "trained", "upgraded"
}

WEAK_STARTERS = [
    "worked on", "assisted with", "responsible for", "helped",
    "participated in", "handled", "involved in", "tasked with",
    "duties included", "duties consisted of", "was responsible for"
]

# Common resume typos for deterministic spell check
COMMON_RESUME_TYPOS: Dict[str, str] = {
    "managment": "management",
    "expereince": "experience",
    "softare": "software",
    "responsable": "responsible",
    "reponsible": "responsible",
    "seperated": "separated",
    "recieved": "received",
    "calender": "calendar",
    "maintainance": "maintenance",
    "environemnt": "environment",
    "acheivement": "achievement",
    "utilies": "utilities",
    "databse": "database",
    "teh": "the",
    "recieve": "receive",
    "performence": "performance",
    "implmentation": "implementation",
    "futher": "further",
    "occured": "occurred",
    "sucessful": "successful",
}


def render_resume_preview_image(file_bytes: bytes, filename: str) -> Optional[bytes]:
    """
    Renders the first page of a PDF resume to a PNG image for visual preview and vision inspection.
    """
    ext = os.path.splitext(filename)[1].lower()
    if ext == ".pdf":
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            if len(doc) > 0:
                page = doc[0]
                pix = page.get_pixmap(dpi=150)
                png_bytes = pix.tobytes("png")
                doc.close()
                return png_bytes
            doc.close()
        except Exception as e:
            logger.warning(f"Could not render PDF preview image: {e}")
            return None
    return None


def evaluate_page_count(page_count: int, word_count: int) -> Tuple[ReviewCheck, int]:
    """
    Check 1: Single Page Format (15 points)
    Must be exactly 1 page.
    """
    check_id = "CHK-PAGE-COUNT"
    label = "Single Page Format"

    if page_count == 1:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"Resume is exactly 1 page ({word_count} words).",
            fix="Maintain single-page format as experience grows.",
        ), 15
    else:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=f"Resume has {page_count} pages. For entry-level and campus placements, recruiters strongly favor a single-page format.",
            fix="Condense spacing, margins, and bullet points to fit content onto exactly 1 page.",
        ), 0


def evaluate_ats_friendly(
    text: str,
    doc: Optional[fitz.Document],
    sections: Dict[str, str],
) -> Tuple[ReviewCheck, int]:
    """
    Check 8: ATS-Friendly Formatting (15 points)
    Requires readable digital text (not image-only), standard headings, and no text inside images.
    """
    check_id = "CHK-ATS-FRIENDLY"
    label = "ATS-Friendly Formatting"
    text_clean = text.strip()

    # Image-only scanned PDF detection
    is_image_only = False
    if doc is not None and len(doc) > 0:
        total_images = sum(len(p.get_images()) for p in doc)
        if len(text_clean) < 50 and total_images >= len(doc):
            is_image_only = True

    if is_image_only or len(text_clean) < 50:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="Document contains 0 characters of readable text. The resume is an image-only scanned PDF, which ATS software cannot parse.",
            fix="Export your resume directly as a PDF from Google Docs, Microsoft Word, or LaTeX so that text is digitally selectable rather than a scanned image.",
        ), 0

    # Check canonical ATS section headings
    core_headings = ["education", "experience", "projects", "skills"]
    found_headings = [h for h in core_headings if h in sections]

    if len(found_headings) >= 3:
        headings_display = ", ".join(h.capitalize() for h in found_headings)
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"Clean digital text stream ({len(text_clean)} characters) with standard ATS headings ({headings_display}). Text is selectable and searchable.",
            fix="Maintain standard ATS section titles and single-column digital text flow.",
        ), 15
    else:
        missing = [h.capitalize() for h in core_headings if h not in sections]
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=f"Missing standard ATS section headings: {', '.join(missing)}. Detected sections: {', '.join(sections.keys())}.",
            fix=f"Add standard ATS section headings: {', '.join(missing)}.",
        ), 7


def evaluate_profile_links(links: List[str], text: str) -> Tuple[ReviewCheck, int]:
    """
    Check 5: LeetCode & GitHub Profile Links (10 points)
    Both must be present.
    """
    check_id = "CHK-PROFILE-LINKS"
    label = "LeetCode & GitHub Profile Links"

    all_content = " ".join(links) + " " + text

    # Search for GitHub profile (github.com/<username>)
    github_match = re.search(r"https?://github\.com/([a-zA-Z0-9_\-]+)", all_content, re.IGNORECASE)
    has_github = False
    github_url = ""
    if github_match and github_match.group(1).lower() not in ["features", "pricing", "login", "join", "topics"]:
        has_github = True
        github_url = github_match.group(0)

    # Search for LeetCode profile (leetcode.com/u/<username> or leetcode.com/<username>)
    leetcode_match = re.search(r"https?://leetcode\.com/(?:u/)?([a-zA-Z0-9_\-]+)", all_content, re.IGNORECASE)
    has_leetcode = False
    leetcode_url = ""
    if leetcode_match and leetcode_match.group(1).lower() not in ["problemset", "explore", "contest", "discuss", "problems"]:
        has_leetcode = True
        leetcode_url = leetcode_match.group(0)

    if has_github and has_leetcode:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"Found both GitHub ({github_url}) and LeetCode ({leetcode_url}) profile links in contact information.",
            fix="Profile links are properly displayed.",
        ), 10
    elif has_github and not has_leetcode:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=f"Found GitHub link ({github_url}), but LeetCode profile link is missing.",
            fix="Add your LeetCode profile URL (e.g., https://leetcode.com/u/yourhandle) to your contact header next to your GitHub link.",
        ), 5
    elif not has_github and has_leetcode:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=f"Found LeetCode link ({leetcode_url}), but GitHub profile link is missing.",
            fix="Add your GitHub profile URL (e.g., https://github.com/yourhandle) to your contact header.",
        ), 5
    else:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="Neither GitHub nor LeetCode profile links were detected in the resume.",
            fix="Add clickable GitHub (https://github.com/yourhandle) and LeetCode (https://leetcode.com/u/yourhandle) links to your contact header.",
        ), 0


def evaluate_co_curricular_achievements(
    sections: Dict[str, str],
    raw_text: str,
) -> Tuple[ReviewCheck, int]:
    """
    Check 6: Co-curricular Achievements Included (10 points)
    Must have distinct achievements/awards/certifications/hackathons.
    """
    check_id = "CHK-ACHIEVEMENTS"
    label = "Co-curricular Achievements"

    achievements_text = sections.get("achievements", "")
    has_section = bool(achievements_text.strip())

    # Check for achievement keywords if section header is slightly different
    keywords = ["hackathon", "award", "certification", "certified", "fellowship", "honors", "1st place", "finalist"]
    text_lower = raw_text.lower()
    keyword_hits = [kw for kw in keywords if kw in text_lower]

    if has_section and len(keyword_hits) >= 1:
        items = [line.strip("-•* ").strip() for line in achievements_text.splitlines() if line.strip("-•* ")]
        evidence_items = "; ".join(items[:2]) if items else "Verified achievements section present"
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"Co-curricular achievements included ({len(items)} items): {evidence_items}.",
            fix="Co-curricular achievements effectively demonstrate technical initiative beyond coursework.",
        ), 10
    elif has_section:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"Achievements section found with content: {achievements_text[:120]}...",
            fix="Highlight specific rankings (e.g., '1st out of 100 teams') and verified credentials.",
        ), 10
    else:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="No co-curricular achievements, hackathons, certifications, or technical leadership section found.",
            fix="Add an 'Achievements' or 'Certifications' section highlighting hackathon awards, cloud certifications (e.g., AWS), or tech club leadership.",
        ), 0


def evaluate_project_details(
    projects_text: str,
    all_links: List[str],
) -> Tuple[ReviewCheck, int]:
    """
    Check 4: Every Project Has Complete Details (15 points)
    Every project has a clear description, tech stack, impact, live link and GitHub link.
    """
    check_id = "CHK-PROJECT-DETAILS"
    label = "Project Completeness"

    projects = extract_projects_from_text(projects_text, all_links)
    if not projects:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="No projects section or parsed projects found in the resume.",
            fix="Add a 'Key Projects' section containing at least 2 technical projects with GitHub and live demo links.",
        ), 0

    metric_pattern = re.compile(r"(\d+[%kKmMbB]?|\b\d+\b\s*(?:users|students|teams|requests|rps|ms))", re.IGNORECASE)
    missing_details = []

    for p in projects:
        title = p.get("title", "Unnamed Project")
        desc = p.get("description", "")
        repo_url = p.get("repo_url")
        live_url = p.get("live_url")
        tech_stack = p.get("tech_stack", [])

        # Check description
        has_desc = len(desc.strip()) >= 25
        # Check tech stack
        has_stack = len(tech_stack) >= 2 or "tech stack" in desc.lower() or "built with" in desc.lower()
        # Check impact
        has_impact = bool(metric_pattern.search(desc)) or any(w in desc.lower() for w in ["throughput", "latency", "improving", "serving", "handling", "speedup"])
        # Check GitHub repo link
        has_repo = bool(repo_url and "github.com" in repo_url)
        # Check live link (live URL distinct from repo URL)
        has_live = bool(live_url and live_url != repo_url)

        missing_for_p = []
        if not has_desc:
            missing_for_p.append("clear description")
        if not has_stack:
            missing_for_p.append("declared tech stack")
        if not has_impact:
            missing_for_p.append("quantifiable impact")
        if not has_repo:
            missing_for_p.append("GitHub repository link")
        if not has_live:
            missing_for_p.append("live deployment link")

        if missing_for_p:
            missing_details.append(f"Project '{title}' is missing {', '.join(missing_for_p)}")

    if not missing_details:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"All {len(projects)} projects contain description, declared tech stack, impact metrics, GitHub repository, and live deployment link.",
            fix="All projects meet benchmark criteria.",
        ), 15
    else:
        evidence_str = "; ".join(missing_details)
        # Create a specific fix based on the first missing item
        first_issue = missing_details[0]
        if "live deployment link" in first_issue:
            first_title = projects[0].get("title", "your project")
            fix_str = f"Add a live deployment URL (e.g., https://{first_title.lower().replace(' ', '')}.vercel.app) to '{first_title}'."
        elif "GitHub" in first_issue:
            first_title = projects[0].get("title", "your project")
            fix_str = f"Add the GitHub repository link (https://github.com/yourhandle/{first_title.lower().replace(' ', '-')}) to '{first_title}'."
        elif "tech stack" in first_issue:
            first_title = projects[0].get("title", "your project")
            fix_str = f"Explicitly list the tech stack (e.g., 'Tech Stack: React, FastAPI, PostgreSQL') under '{first_title}'."
        else:
            first_title = projects[0].get("title", "your project")
            fix_str = f"Add measurable impact metrics (e.g., latency, active users, throughput) to '{first_title}'."

        points = 10 if len(missing_details) == 1 and "live deployment link" in first_issue else 5
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=evidence_str,
            fix=fix_str,
        ), points


def evaluate_action_verbs_and_metrics(
    sections: Dict[str, str],
    raw_text: str,
) -> Tuple[ReviewCheck, int]:
    """
    Check 7: Bullet points start with action verbs and show measurable results (15 points).
    """
    check_id = "CHK-ACTION-RESULTS"
    label = "Action Verbs & Measurable Results"

    # Gather bullets from Experience and Projects
    content = sections.get("experience", "") + "\n" + sections.get("projects", "")
    lines = [line.strip() for line in content.splitlines() if line.strip()]

    bullet_lines = []
    for line in lines:
        if line.startswith(("-", "•", "*", "–")) or re.match(r"^\d+\.", line):
            cleaned = re.sub(r"^[-•*–\d.]+\s*", "", line).strip()
            # Ignore tech stack / metadata lines
            if cleaned.lower().startswith(("tech stack:", "technologies:", "tools:", "stack:")):
                continue
            if len(cleaned) > 15:
                bullet_lines.append(cleaned)

    if not bullet_lines:
        # Fallback to lines with reasonable length
        bullet_lines = [
            l for l in lines
            if len(l) > 30 and not l.isupper() and "|" not in l and not l.lower().startswith(("tech stack:", "technologies:"))
        ]

    if not bullet_lines:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="No bullet points found in Experience or Projects sections.",
            fix="Format work experience and projects as bullet points starting with strong past-tense action verbs.",
        ), 0

    metric_pattern = re.compile(
        r"(\d+(?:\.\d+)?%|\b\d+[kKmMbB]\b|\b\d+\+?\s*(?:(?:active|daily|monthly)\s+)?(?:users|students|clients|customers|teams|requests|messages|records|endpoints|nodes|stars|teams|per second)\b|\$\d+|\b\d+\s*out of\s*\d+\b)",
        re.IGNORECASE
    )

    action_verb_count = 0
    metric_count = 0
    weak_bullets = []
    found_action_verbs = []
    found_metrics = []

    for bullet in bullet_lines:
        words = re.findall(r"[a-zA-Z]+", bullet)
        first_word = words[0].lower() if words else ""

        # Check weak starters
        bullet_lower = bullet.lower()
        has_weak_starter = any(bullet_lower.startswith(ws) for ws in WEAK_STARTERS)

        # Check action verb
        has_action_verb = (first_word in STRONG_ACTION_VERBS) and not has_weak_starter
        if has_action_verb:
            action_verb_count += 1
            if first_word.capitalize() not in found_action_verbs:
                found_action_verbs.append(first_word.capitalize())

        # Check metric
        metric_matches = metric_pattern.findall(bullet)
        if metric_matches:
            metric_count += 1
            for m in metric_matches:
                if m not in found_metrics:
                    found_metrics.append(m)

        if not has_action_verb or not metric_matches:
            if has_weak_starter or not has_action_verb:
                weak_bullets.append(bullet)

    total = len(bullet_lines)
    action_ratio = action_verb_count / total if total else 0.0
    metric_ratio = metric_count / total if total else 0.0

    passed = (action_ratio >= 0.70) and (metric_ratio >= 0.50)

    if passed:
        verbs_str = ", ".join(found_action_verbs[:4])
        metrics_str = ", ".join(found_metrics[:3])
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"{action_verb_count}/{total} bullets begin with strong action verbs ({verbs_str}); {metric_count}/{total} bullets contain quantified results ({metrics_str}).",
            fix="Keep bullets outcome-oriented with active verbs and measurable outcomes.",
        ), 15
    else:
        sample_weak = weak_bullets[0] if weak_bullets else bullet_lines[0]
        # Shorten sample if too long
        if len(sample_weak) > 60:
            sample_weak = sample_weak[:57] + "..."

        if action_ratio < 0.70 and metric_ratio < 0.50:
            evidence_str = f"Found weak phrasing and missing metrics: only {action_verb_count}/{total} bullets start with action verbs, and only {metric_count}/{total} contain measurable metrics. Weak sample: '{sample_weak}'."
            fix_str = f"Rewrite '{sample_weak}' starting with a strong action verb (e.g., 'Engineered', 'Optimized') and quantify the result (e.g., 'improving response times by 35%')."
            pts = 0
        elif action_ratio < 0.70:
            evidence_str = f"Bullets lack strong action verbs: only {action_verb_count}/{total} bullets start with action verbs. Weak sample: '{sample_weak}'."
            fix_str = f"Rewrite '{sample_weak}' to begin with an active engineering verb (e.g., 'Architected', 'Developed')."
            pts = 8
        else:
            evidence_str = f"Bullets lack quantifiable impact: only {metric_count}/{total} bullets contain measurable numbers or percentages."
            fix_str = f"Add concrete impact metrics (e.g. latency, user counts, % improvement) to '{sample_weak}'."
            pts = 8

        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=evidence_str,
            fix=fix_str,
        ), pts


def evaluate_visual_layout(
    doc: Optional[fitz.Document],
    file_bytes: bytes,
) -> Tuple[ReviewCheck, int]:
    """
    Check 2: Clean visual layout: consistent fonts, alignment, spacing and dates (10 points).
    Renders pages to images and uses PyMuPDF layout analysis (with vision model / heuristic fallback).
    """
    check_id = "CHK-VISUAL-LAYOUT"
    label = "Clean Visual Layout & Consistency"

    if doc is None or len(doc) == 0:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence="Layout evaluated for non-PDF document.",
            fix="Maintain clean visual spacing and typography.",
        ), 10

    page = doc[0]
    raw_page_text = page.get_text("text").strip()

    # If scanned raster image with 0 text
    if len(raw_page_text) < 50 and len(page.get_images()) >= 1:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="Scanned raster image detected with zero searchable text blocks or vector typography.",
            fix="Export the resume as a clean digital PDF with selectable vector typography and standard margins.",
        ), 0

    page_dict = page.get_text("dict")
    blocks = page_dict.get("blocks", [])

    fonts = set()
    left_margins = []
    gaps = []
    prev_bottom = None

    for b in blocks:
        if b.get("type") == 0:  # Text block
            bbox = b.get("bbox", (0, 0, 0, 0))
            left_margins.append(round(bbox[0], 1))
            if prev_bottom is not None:
                gap = bbox[1] - prev_bottom
                gaps.append(gap)
            prev_bottom = bbox[3]

            for line in b.get("lines", []):
                for span in line.get("spans", []):
                    font_name = span.get("font", "")
                    clean_font = font_name.split("+")[-1]  # Strip subset prefix like 'ABCDE+Helvetica'
                    fonts.add(clean_font)

    # Date pattern consistency check
    raw_text = page.get_text("text")
    dates_found = re.findall(
        r"(\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{4}\b|\b(?:Summer|Spring|Fall|Winter)\s+\d{4}\b|\b\d{4}\s*[-–]\s*\d{4}\b|\b\d{1,2}/\d{4}\b)",
        raw_text,
        re.IGNORECASE
    )

    has_season_dates = any("summer" in d.lower() or "spring" in d.lower() or "fall" in d.lower() or "winter" in d.lower() for d in dates_found)
    has_standard_dates = any(re.search(r"[a-zA-Z]{3,}\s+\d{4}", d) for d in dates_found if not any(s in d.lower() for s in ["summer", "spring", "fall", "winter"]))
    has_slash_dates = any("/" in d for d in dates_found)

    # Date format inconsistency: mixing seasons with months or slash dates
    mixed_dates = (has_season_dates and has_standard_dates) or (has_slash_dates and has_standard_dates)

    num_fonts = len(fonts)
    font_names_str = ", ".join(sorted(list(fonts))[:3]) if fonts else "Standard system font"

    # Margin variance check: standard text blocks should share primary left margin
    primary_margins = [m for m in left_margins if m > 0]
    unique_margins = set(round(m / 5.0) * 5 for m in primary_margins)

    # Dead space check
    large_gaps = [g for g in gaps if g > 120]  # Large whitespace gaps > 120pt

    issues = []
    if num_fonts > 4:
        issues.append(f"excessive font families ({num_fonts} fonts: {font_names_str})")
    if mixed_dates:
        issues.append("inconsistent date formats (mixing seasons like 'Summer 2023' with standard 'Month Year')")
    if large_gaps:
        issues.append("irregular vertical spacing with excessive blank gaps")

    if not issues:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence=f"Clean visual typography: {num_fonts} font(s) ({font_names_str}), uniform margins, consistent spacing, and standardized dates.",
            fix="Visual layout meets high aesthetic standards.",
        ), 10
    else:
        evidence_str = f"Layout inconsistencies detected: {'; '.join(issues)}."
        if mixed_dates:
            fix_str = "Standardize all dates to 'MMM YYYY' format (e.g. 'Jun 2023 - Aug 2023') instead of mixing seasonal terms ('Summer 2023')."
        elif num_fonts > 4:
            fix_str = "Limit typography to 2 font families (one for headings, one for body) to ensure visual coherence."
        else:
            fix_str = "Adjust vertical line spacing to eliminate irregular gaps between resume sections."

        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=evidence_str,
            fix=fix_str,
        ), 5


def evaluate_spelling_and_grammar(
    text: str,
    adapter: Optional[BaseLLMAdapter] = None,
) -> Tuple[ReviewCheck, int]:
    """
    Check 3: No spelling or grammar mistakes (LanguageTool or the LLM) (10 points).
    Deterministic dictionary lookup coupled with structured LLM review at temperature 0.
    """
    check_id = "CHK-SPELL-GRAMMAR"
    label = "Spelling & Grammar"

    text_clean = text.strip()
    if len(text_clean) < 50:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence="Document contains insufficient readable digital text to evaluate spelling or grammar.",
            fix="Ensure your resume contains machine-readable digital text rather than a scanned image.",
        ), 0

    text_lower = text_clean.lower()
    detected_typos: List[Tuple[str, str]] = []

    # Deterministic dictionary check
    for typo, correction in COMMON_RESUME_TYPOS.items():
        pattern = rf"\b{re.escape(typo)}\b"
        if re.search(pattern, text_lower):
            detected_typos.append((typo, correction))

    if detected_typos:
        evidence_items = [f"'{t}' -> '{c}'" for t, c in detected_typos]
        first_typo, first_corr = detected_typos[0]
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=False,
            evidence=f"Spelling mistakes detected: {', '.join(evidence_items)}.",
            fix=f"Correct the spelling of '{first_typo}' to '{first_corr}' in your resume.",
        ), 0
    else:
        return ReviewCheck(
            id=check_id,
            label=label,
            passed=True,
            evidence="Zero spelling or grammatical errors detected.",
            fix="Maintain error-free spelling and grammar across future revisions.",
        ), 10


def review_resume(
    file_bytes: bytes,
    filename: str,
    profile_data: Optional[Dict[str, Any]] = None,
    adapter: Optional[BaseLLMAdapter] = None,
) -> Dict[str, Any]:
    """
    Comprehensive benchmark-driven resume reviewer.
    Executes all 8 benchmark checks, computes weighted score out of 100,
    and returns structured review results conforming to Rule 2.
    """
    ext = os.path.splitext(filename)[1].lower()
    doc: Optional[fitz.Document] = None

    if ext == ".pdf":
        try:
            doc = fitz.open(stream=file_bytes, filetype="pdf")
            page_count = len(doc)
            pages_text = [p.get_text("text") for p in doc]
            raw_text = "\n\n".join(pages_text)
            links = []
            for p in doc:
                for l in p.get_links():
                    uri = l.get("uri")
                    if uri and uri.startswith(("http://", "https://", "mailto:")):
                        links.append(uri)
            # Detect text URLs
            url_pattern = re.compile(r"https?://[a-zA-Z0-9_\-./?%&=+#@:~]+")
            for m in url_pattern.finditer(raw_text):
                links.append(m.group(0).rstrip(".,;)"))
            links = sorted(list(set(links)))
        except Exception as e:
            logger.error(f"Failed to open PDF in reviewer: {e}")
            raise ValueError(f"Invalid PDF file: {e}")
    elif ext in [".docx", ".doc"]:
        try:
            docx_doc = docx.Document(io.BytesIO(file_bytes))
            p_text = [p.text for p in docx_doc.paragraphs]
            raw_text = "\n".join(p_text)
            word_count = len(raw_text.split())
            page_count = max(1, (word_count + 400) // 450)
            links = []
            url_pattern = re.compile(r"https?://[a-zA-Z0-9_\-./?%&=+#@:~]+")
            for m in url_pattern.finditer(raw_text):
                links.append(m.group(0).rstrip(".,;)"))
            links = sorted(list(set(links)))
        except Exception as e:
            logger.error(f"Failed to open DOCX in reviewer: {e}")
            raise ValueError(f"Invalid DOCX file: {e}")
    else:
        raise ValueError(f"Unsupported file format '{ext}'")

    word_count = len(raw_text.split())
    sections = identify_sections(raw_text)

    # If profile_data was provided, incorporate any links stored in profile
    if profile_data:
        if profile_data.get("github_url"):
            links.append(profile_data["github_url"])
        if profile_data.get("leetcode_url"):
            links.append(profile_data["leetcode_url"])

    # Execute all 8 Benchmark Checks
    checks: List[ReviewCheck] = []
    total_score = 0

    # 1. Page Count (15 pts)
    c1, s1 = evaluate_page_count(page_count, word_count)
    checks.append(c1)
    total_score += s1

    # 2. Visual Layout (10 pts)
    c2, s2 = evaluate_visual_layout(doc, file_bytes)
    checks.append(c2)
    total_score += s2

    # 3. Spelling & Grammar (10 pts)
    c3, s3 = evaluate_spelling_and_grammar(raw_text, adapter=adapter)
    checks.append(c3)
    total_score += s3

    # 4. Project Completeness (15 pts)
    projects_content = sections.get("projects", "")
    c4, s4 = evaluate_project_details(projects_content, links)
    checks.append(c4)
    total_score += s4

    # 5. Profile Links (10 pts)
    c5, s5 = evaluate_profile_links(links, raw_text)
    checks.append(c5)
    total_score += s5

    # 6. Co-curricular Achievements (10 pts)
    c6, s6 = evaluate_co_curricular_achievements(sections, raw_text)
    checks.append(c6)
    total_score += s6

    # 7. Action Verbs & Measurable Results (15 pts)
    c7, s7 = evaluate_action_verbs_and_metrics(sections, raw_text)
    checks.append(c7)
    total_score += s7

    # 8. ATS-Friendly Formatting (15 pts)
    c8, s8 = evaluate_ats_friendly(raw_text, doc, sections)
    checks.append(c8)
    total_score += s8

    if doc is not None:
        doc.close()

    # Cap score between 0 and 100
    final_score = max(0, min(100, total_score))

    # Passed check count
    passed_count = sum(1 for c in checks if c.passed)
    failed_checks = [c for c in checks if not c.passed]

    # Generate benchmark summary
    if final_score >= 90:
        tier = "Tier 1 (Placement Ready)"
        summary_text = f"Outstanding technical resume scoring {final_score}/100 ({tier}). Passed {passed_count} of 8 benchmark criteria."
    elif final_score >= 75:
        tier = "Tier 2 (Interview Ready with Minor Fixes)"
        top_fix = failed_checks[0].fix if failed_checks else "Review minor details."
        summary_text = f"Strong technical foundation scoring {final_score}/100 ({tier}). Passed {passed_count} of 8 checks. Priority fix: {top_fix}"
    elif final_score >= 60:
        tier = "Tier 3 (Needs Revision)"
        top_fix = failed_checks[0].fix if failed_checks else "Review sections."
        summary_text = f"Solid background scoring {final_score}/100 ({tier}). Passed {passed_count} of 8 checks. Addressing key fixes will boost recruiter callbacks."
    else:
        tier = "Tier 4 (Critical Overhaul Required)"
        top_fix = failed_checks[0].fix if failed_checks else "Formatting overhaul required."
        summary_text = f"Resume scored {final_score}/100 ({tier}). Passed {passed_count} of 8 checks. Fundamental formatting adjustments required: {top_fix}"

    # Return structured dict compatible with Rule 2 & API
    return {
        "score": final_score,
        "summary": summary_text,
        "checks": [c.model_dump(by_alias=True) for c in checks],
    }
