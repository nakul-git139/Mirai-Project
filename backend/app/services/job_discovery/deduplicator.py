from __future__ import annotations
import re
from typing import List, Dict, Any, Tuple


COMPANY_SUFFIX_REGEX = re.compile(
    r"\b(inc\.?|llc|corp\.?|corporation|ltd\.?|limited|technologies|tech|co\.?|gmbh|solutions)\b",
    re.IGNORECASE,
)
PUNCT_REGEX = re.compile(r"[^\w\s]")


def normalize_company(company: str) -> str:
    """Normalize company name to canonical lowercase form."""
    if not company:
        return ""
    text = company.lower()
    text = COMPANY_SUFFIX_REGEX.sub("", text)
    text = PUNCT_REGEX.sub(" ", text)
    return " ".join(text.split())


def normalize_title(title: str) -> str:
    """Normalize job title removing locations in brackets, levels, punctuation."""
    if not title:
        return ""
    text = title.lower()
    # Remove bracketed content like (Remote) or [Engineering]
    text = re.sub(r"\[.*?\]|\(.*?\)", "", text)
    text = PUNCT_REGEX.sub(" ", text)
    tokens = text.split()
    return " ".join(tokens)


def get_canonical_key(job: Dict[str, Any]) -> str:
    """Generate a stable canonical key based on normalized company and title."""
    comp = normalize_company(job.get("company", ""))
    tit = normalize_title(job.get("title", ""))
    return f"{comp}::{tit}"


def merge_job_pair(primary: Dict[str, Any], duplicate: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two matching job records into a single consolidated record."""
    merged = primary.copy()

    # Collect all sources
    existing_sources = merged.get("sources") or [merged.get("source")]
    dup_sources = duplicate.get("sources") or [duplicate.get("source")]
    combined_sources = []
    for s in existing_sources + dup_sources:
        if s and s not in combined_sources:
            combined_sources.append(s)
    merged["sources"] = combined_sources

    # Collect URLs
    canonical_url = merged.get("url") or duplicate.get("url") or ""
    merged["url"] = canonical_url

    existing_alts = set(merged.get("alternate_urls") or [])
    for u in [duplicate.get("url"), merged.get("url")]:
        if u and u != canonical_url:
            existing_alts.add(u)
    merged["alternate_urls"] = sorted(list(existing_alts))

    # Keep longer description
    desc_p = merged.get("description", "") or ""
    desc_d = duplicate.get("description", "") or ""
    if len(desc_d) > len(desc_p):
        merged["description"] = desc_d

    # Prefer detailed location
    loc_p = merged.get("location", "") or ""
    loc_d = duplicate.get("location", "") or ""
    if "unspecified" in loc_p.lower() and loc_d:
        merged["location"] = loc_d

    # Merge metadata
    meta = merged.get("metadata", {}).copy()
    meta.update(duplicate.get("metadata", {}))
    merged["metadata"] = meta

    return merged


def deduplicate_jobs(jobs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicates a list of job postings across multiple sources.
    Merges duplicate postings with the same canonical company and title.
    """
    seen: Dict[str, Dict[str, Any]] = {}
    order: List[str] = []

    for job in jobs:
        key = get_canonical_key(job)
        if not key or key == "::":
            # If both company and title are missing, fall back to unique id
            key = str(job.get("id", len(order)))

        if key in seen:
            seen[key] = merge_job_pair(seen[key], job)
        else:
            j_copy = job.copy()
            if "sources" not in j_copy:
                j_copy["sources"] = [j_copy.get("source")] if j_copy.get("source") else []
            seen[key] = j_copy
            order.append(key)

    return [seen[k] for k in order]
