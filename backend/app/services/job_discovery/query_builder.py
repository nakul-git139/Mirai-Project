from __future__ import annotations
import urllib.parse
from typing import List, Dict, Optional, Any


def format_term(term: str, always_quote: bool = False) -> str:
    """Format a single term, adding double quotes if spaces/symbols or always_quote is True."""
    term = term.strip()
    if term.startswith('"') and term.endswith('"'):
        return term
    if always_quote or " " in term or "-" in term or "." in term:
        return f'"{term}"'
    return term


def format_clause(terms: List[str], always_quote: bool = False) -> str:
    """Format a list of terms into an OR-joined parenthesized boolean clause."""
    clean_terms = [t.strip() for t in terms if t and t.strip()]
    if not clean_terms:
        return ""
    formatted = [format_term(t, always_quote=always_quote) for t in clean_terms]
    return f"({' OR '.join(formatted)})"


def build_boolean_query(
    skills: List[str],
    job_types: Optional[List[str]] = None,
    locations: Optional[List[str]] = None,
    target_roles: Optional[List[str]] = None,
    max_skills: int = 4,
) -> str:
    """
    Build a boolean search query string from student skills, role types, and locations.
    Example output:
    ("React" OR "Next.js") AND (intern OR internship) AND (Bangalore OR remote)
    """
    clauses: List[str] = []

    # 1. Skills clause (skills always double-quoted)
    top_skills = [s for s in skills if s.strip()][:max_skills]
    if top_skills:
        clauses.append(format_clause(top_skills, always_quote=True))

    # 2. Target roles clause (if provided)
    if target_roles:
        clean_roles = [r for r in target_roles if r.strip()][:2]
        if clean_roles:
            clauses.append(format_clause(clean_roles, always_quote=True))

    # 3. Job types clause (defaults to intern / internship)
    types_list = job_types if job_types is not None else ["intern", "internship"]
    if types_list:
        clauses.append(format_clause(types_list, always_quote=False))

    # 4. Locations clause (defaults to Bangalore / remote)
    loc_list = locations if locations is not None else ["Bangalore", "remote"]
    if loc_list:
        clauses.append(format_clause(loc_list, always_quote=False))

    return " AND ".join(clauses)


def build_open_search_links(
    query: str,
    location: str = "India",
    primary_role: Optional[str] = None,
) -> Dict[str, str]:
    """
    Generate outbound pre-filled search URLs for sites that must NOT be scraped.
    The student clicks these to open search results manually in their own browser.
    """
    encoded_query = urllib.parse.quote_plus(query)
    encoded_loc = urllib.parse.quote_plus(location)

    # Simplified keyword for sites with shorter URL limits
    simple_keyword = primary_role or query.split(" AND ")[0].replace("(", "").replace(")", "").replace('"', "")
    encoded_simple = urllib.parse.quote_plus(simple_keyword)

    return {
        "linkedin": f"https://www.linkedin.com/jobs/search/?keywords={encoded_query}&location={encoded_loc}",
        "naukri": f"https://www.naukri.com/jobs-in-india?k={encoded_query}",
        "internshala": f"https://internshala.com/internships/keywords-{encoded_simple}/",
        "google": f"https://www.google.com/search?q={encoded_query}+jobs",
    }
