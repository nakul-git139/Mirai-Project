from __future__ import annotations
import re
from typing import List, Dict, Any, Optional

# Pre-compiled high-precision secret patterns
SECRET_PATTERNS = [
    {
        "type": "AWS Access Key",
        "pattern": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
        "severity": "CRITICAL",
    },
    {
        "type": "AWS Temporary Key",
        "pattern": re.compile(r"\b(ASIA[0-9A-Z]{16})\b"),
        "severity": "CRITICAL",
    },
    {
        "type": "Private Key",
        "pattern": re.compile(r"(-----BEGIN (?:RSA|DSA|EC|OPENSSH|PGP) PRIVATE KEY[^-]*-----)"),
        "severity": "CRITICAL",
    },
    {
        "type": "GitHub Personal Access Token",
        "pattern": re.compile(r"\b((?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36,})\b"),
        "severity": "CRITICAL",
    },
    {
        "type": "GitHub Fine-Grained Token",
        "pattern": re.compile(r"\b(github_pat_[A-Za-z0-9_]{22}_[A-Za-z0-9_]{59})\b"),
        "severity": "CRITICAL",
    },
    {
        "type": "Slack API Token",
        "pattern": re.compile(r"\b(xox[baprs]-[0-9a-zA-Z]{10,48})\b"),
        "severity": "HIGH",
    },
    {
        "type": "OpenAI / LLM API Key",
        "pattern": re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,})\b"),
        "severity": "HIGH",
    },
    {
        "type": "Database Connection URI with Credentials",
        "pattern": re.compile(
            r"\b((?:postgres(?:ql)?|mysql|mongodb(?:\+srv)?|redis)://[a-zA-Z0-9_\-\.]+:(?!(?:password|\$|\{))[^@\s/]{4,}@[a-zA-Z0-9_\-\.]+)",
            re.IGNORECASE,
        ),
        "severity": "CRITICAL",
    },
    {
        "type": "Hardcoded API / Secret Key Assignment",
        "pattern": re.compile(
            r"""(?:api_key|secret_key|client_secret|auth_token|access_token)\s*[:=]\s*['"]([a-zA-Z0-9_\-]{20,})['"]""",
            re.IGNORECASE,
        ),
        "severity": "HIGH",
    },
]

# Standard documentation placeholders and dummy strings that should not trigger false positives
KNOWN_PLACEHOLDERS = {
    "AKIAIOSFODNN7EXAMPLE",
    "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
    "your_api_key_here",
    "your-api-key-here",
    "YOUR_API_KEY",
    "your_secret_key",
    "your-secret-key",
    "ENTER_YOUR_API_KEY",
    "INSERT_API_KEY_HERE",
    "my_api_key_placeholder",
    "dummy_api_key_value",
    "mock-model",
    "mock-api-key",
    "mock_token_1234567890",
}

# Files that commonly contain documentation examples or compiled data where secrets checks should be skipped or softened
SKIPPED_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".gif", ".webp", ".ico", ".svg",
    ".pdf", ".zip", ".tar", ".gz", ".lock", ".woff", ".woff2",
    ".ttf", ".eot", ".mp4", ".mp3", ".wav",
}

SKIPPED_FILENAMES = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "Cargo.lock",
    "Gemfile.lock",
    ".env.example",
    ".env.template",
    ".env.sample",
}


def is_placeholder(secret: str) -> bool:
    """Check if the detected secret is a common documentation placeholder or test dummy."""
    cleaned = secret.strip().strip("'\"")
    if cleaned in KNOWN_PLACEHOLDERS:
        return True
    lower = cleaned.lower()
    if any(
        kw in lower
        for kw in (
            "example",
            "placeholder",
            "dummy",
            "your_key",
            "your-key",
            "insert_",
            "replace_me",
            "xxxxxxxx",
            "1234567890",
            "test_key",
            "test-token",
        )
    ):
        return True
    return False


def mask_secret(secret: str) -> str:
    """Masks secret to show first 4 and last 3 characters for safe evidence reporting."""
    if len(secret) <= 8:
        return "***"
    return f"{secret[:4]}...{secret[-3:]}"


def scan_file_content(path: str, content: str) -> List[Dict[str, Any]]:
    """
    Scans a single file's content for committed secrets.
    Returns a list of findings with secret type, masked value, line number, and severity.
    """
    findings: List[Dict[str, Any]] = []

    # Check if filename is excluded
    filename = path.rsplit("/", 1)[-1]
    if filename in SKIPPED_FILENAMES:
        return findings

    # Check if extension is excluded
    dot_idx = filename.rfind(".")
    if dot_idx != -1 and filename[dot_idx:].lower() in SKIPPED_EXTENSIONS:
        return findings

    lines = content.splitlines()
    for line_num, line in enumerate(lines, 1):
        # Ignore comments indicating documentation example
        if "example" in line.lower() and "secret" in line.lower():
            if is_placeholder(line):
                continue

        for rule in SECRET_PATTERNS:
            matches = rule["pattern"].findall(line)
            for match in matches:
                secret_str = match if isinstance(match, str) else match[0]
                if is_placeholder(secret_str):
                    continue
                findings.append(
                    {
                        "file": path,
                        "line": line_num,
                        "type": rule["type"],
                        "masked": mask_secret(secret_str),
                        "severity": rule["severity"],
                    }
                )

    return findings


def scan_repository_files(files_dict: Dict[str, str]) -> List[Dict[str, Any]]:
    """
    Scans a dictionary mapping file path -> text content.
    Returns all findings aggregated across the repository.
    """
    all_findings: List[Dict[str, Any]] = []
    for path, content in files_dict.items():
        all_findings.extend(scan_file_content(path, content))
    return all_findings
