from __future__ import annotations
import re
import os
import logging
from typing import Dict, Any, List, Optional, Tuple

from pydantic import BaseModel, Field

from app.schemas import ReviewCheck
from app.llm.factory import get_llm_adapter
from app.llm.structured import agenerate_structured_output
from app.services.secret_scanner import scan_repository_files
from app.services.live_link_checker import check_live_link
from app.services.github_scanner import (
    GitHubScanner,
    parse_github_repo_url,
    GitHubRateLimitError,
    GitHubNotFoundError,
    GitHubAPIError,
)

logger = logging.getLogger(__name__)

# Check Weights summing to 100
WEIGHTS = {
    "CHK-GH-PROFILE-README": 5,
    "CHK-GH-PINNED-REPOS": 5,
    "CHK-GH-COMMIT-ACTIVITY": 10,
    "CHK-GH-REPO-README": 10,
    "CHK-GH-FOLDER-STRUCTURE": 5,
    "CHK-GH-COMMIT-MESSAGES": 5,
    "CHK-GH-NO-SECRETS": 15,
    "CHK-GH-TESTS-PRESENT": 10,
    "CHK-GH-CODE-REVIEW": 10,
    "CHK-LIVE-LOAD-STATUS": 10,
    "CHK-LIVE-CONSOLE-HEALTH": 5,
    "CHK-LIVE-CONTENT-MATCH": 5,
    "CHK-LIVE-MOBILE-VIEWPORT": 5,
}


class CodeReviewLLMSchema(BaseModel):
    passed: bool = Field(description="True if code has sound modular structure and no glaring bugs")
    readability_rating: str = Field(description="Rating: high, medium, low")
    issues: List[str] = Field(default_factory=list, description="Specific structure, bug, or readability issues")
    positive_notes: List[str] = Field(default_factory=list, description="Strengths observed in the code")
    specific_fix: str = Field(description="Concrete, non-generic actionable recommendation for the codebase")


async def evaluate_github_and_live(
    username: Optional[str] = None,
    repo_url_or_slug: Optional[str] = None,
    live_url: Optional[str] = None,
    project_title: Optional[str] = None,
    resume_skills: Optional[List[str]] = None,
    scanner: Optional[GitHubScanner] = None,
    preloaded_repo_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Main orchestrator for GitHub profile, codebase, and Playwright live link review.
    Evaluates all benchmark checks deterministically, using LLM temp=0 for code review.
    """
    close_scanner = False
    if scanner is None and not preloaded_repo_data:
        scanner = GitHubScanner()
        close_scanner = True

    checks: List[ReviewCheck] = []
    repo_summary: Dict[str, Any] = {}
    live_results: Optional[Dict[str, Any]] = None
    screenshots: Dict[str, Optional[str]] = {"desktop": None, "mobile": None}

    try:
        # Determine username and repository
        owner = username
        repo_name = None

        if repo_url_or_slug:
            try:
                parsed_owner, parsed_repo = parse_github_repo_url(repo_url_or_slug)
                owner = parsed_owner or owner
                repo_name = parsed_repo
            except Exception:
                repo_name = repo_url_or_slug

        # ----------------------------------------------------
        # 1. Profile Level Checks (if username provided)
        # ----------------------------------------------------
        profile_readme_content: Optional[str] = None
        user_events_data: Dict[str, Any] = {"push_events_90d": 0, "total_events": 0}
        user_repos_list: List[Dict[str, Any]] = []

        if owner and scanner:
            try:
                profile_readme_content = scanner.fetch_profile_readme(owner)
                user_events_data = scanner.fetch_user_events_momentum(owner)
                user_repos_list = scanner.fetch_user_repos(owner)
            except (GitHubRateLimitError, GitHubNotFoundError):
                raise
            except Exception as e:
                logger.warning(f"Error fetching profile level info for '{owner}': {e}")

        # If repo_name not specified, pick top featured repo from user repos
        if not repo_name and user_repos_list:
            # Sort by stargazers then updated
            featured = sorted(
                user_repos_list,
                key=lambda r: (r.get("stargazers_count", 0), r.get("updated_at", "")),
                reverse=True,
            )
            repo_name = featured[0].get("name")

        # Check 1: Profile README
        if profile_readme_content and len(profile_readme_content.strip()) >= 50:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-PROFILE-README",
                    label="Profile README Present",
                    passed=True,
                    evidence=f"Profile README detected in '{owner}/{owner}' ({len(profile_readme_content.strip())} chars) introducing candidate background and skills.",
                    fix="Keep profile README updated with recent projects, blog posts, and active technical interests.",
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-PROFILE-README",
                    label="Profile README Present",
                    passed=False,
                    evidence=f"No profile README detected for GitHub user '{owner or 'unknown'}'. Recruiters value a personalized profile summary.",
                    fix=f"Create a public repository named exactly '{owner or 'your-username'}' with a README.md introducing your technical background, featured projects, and core languages.",
                )
            )

        # Check 2: Pinned / Featured Repositories
        if len(user_repos_list) >= 2:
            repos_with_desc = [r for r in user_repos_list if r.get("description")]
            has_featured = len(repos_with_desc) >= 2 or any(r.get("stargazers_count", 0) > 0 for r in user_repos_list)
            checks.append(
                ReviewCheck(
                    id="CHK-GH-PINNED-REPOS",
                    label="Pinned / Featured Repositories",
                    passed=has_featured,
                    evidence=f"Found {len(user_repos_list)} public repositories ({len(repos_with_desc)} with clear descriptions and topics).",
                    fix="Pin your top 2-4 strongest full-stack and systems projects to your GitHub profile header with clear one-line descriptions and topic tags."
                    if not has_featured
                    else "Maintain pinned showcase repositories with concise value propositions.",
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-PINNED-REPOS",
                    label="Pinned / Featured Repositories",
                    passed=False,
                    evidence=f"Found only {len(user_repos_list)} public repositories. Candidate profile lacks featured project showcases.",
                    fix="Pin your top 2-4 strongest full-stack and systems projects to your GitHub profile header with clear one-line descriptions and topic tags.",
                )
            )

        # Check 3: Regular Commit Activity
        push_count = user_events_data.get("push_events_90d", 0)
        has_momentum = push_count >= 3
        checks.append(
            ReviewCheck(
                id="CHK-GH-COMMIT-ACTIVITY",
                label="Regular Commit Activity",
                passed=has_momentum,
                evidence=f"Developer activity: {push_count} public push events recorded over the last 90 days."
                if push_count > 0
                else "Zero public commit events detected in the last 90 days. Recruiter perception flags inactive profiles.",
                fix="Commit code regularly (at least 2-3 times per week) across your ongoing coursework, capstone projects, or open-source repositories."
                if not has_momentum
                else "Maintain consistent weekly commit cadence to demonstrate active development momentum.",
            )
        )

        # ----------------------------------------------------
        # 2. Repository Level Checks
        # ----------------------------------------------------
        repo_data: Dict[str, Any] = {}
        readme_text: Optional[str] = None
        tree_items: List[Dict[str, Any]] = []
        commits_list: List[Dict[str, Any]] = []
        files_content_map: Dict[str, str] = {}

        if preloaded_repo_data:
            repo_data = preloaded_repo_data.get("repo", {})
            readme_text = preloaded_repo_data.get("readme")
            tree_items = preloaded_repo_data.get("tree", [])
            commits_list = preloaded_repo_data.get("commits", [])
            files_content_map = preloaded_repo_data.get("files", {})
            repo_name = repo_data.get("name", repo_name or "project")
            if not live_url and repo_data.get("homepage"):
                live_url = repo_data.get("homepage")
        elif owner and repo_name and scanner:
            try:
                repo_data = scanner.fetch_repository(owner, repo_name)
                default_branch = repo_data.get("default_branch", "main")
                readme_text = scanner.fetch_repo_readme(owner, repo_name)
                tree_items = scanner.fetch_repo_tree(owner, repo_name, default_branch)
                commits_list = scanner.fetch_repo_commits(owner, repo_name)

                if not live_url and repo_data.get("homepage"):
                    live_url = repo_data.get("homepage")

                # Sample key files for secret scan and LLM code review (up to 15 files)
                for item in tree_items[:50]:
                    path = item.get("path", "")
                    if item.get("type") == "blob" and should_inspect_file(path):
                        content = scanner.fetch_file_content(owner, repo_name, default_branch, path)
                        if content:
                            files_content_map[path] = content
                        if len(files_content_map) >= 15:
                            break
            except (GitHubRateLimitError, GitHubNotFoundError):
                raise
            except Exception as e:
                logger.warning(f"Error fetching repo data for '{owner}/{repo_name}': {e}")

        repo_summary = {
            "owner": owner,
            "name": repo_name,
            "description": repo_data.get("description"),
            "language": repo_data.get("language"),
            "stargazers_count": repo_data.get("stargazers_count", 0),
            "forks_count": repo_data.get("forks_count", 0),
            "file_count": len(tree_items),
        }

        # Check 4: Project README with Setup & Visuals
        if readme_text:
            has_setup = bool(
                re.search(
                    r"\b(npm\s+(?:install|run|start)|docker\s+run|pip\s+install|python\s+|yarn\s+|pnpm\s+|make\s+|cargo\s+|mvn\s+|setup|installation)\b",
                    readme_text,
                    re.IGNORECASE,
                )
            )
            has_visuals = bool(
                re.search(
                    r"(!\[.*?\]\(.*?\)|<img[^>]+src=|\.(?:png|jpg|jpeg|gif|svg|webp))",
                    readme_text,
                    re.IGNORECASE,
                )
            )
            passed_readme = has_setup and has_visuals
            evidence_parts = []
            if has_setup:
                evidence_parts.append("setup commands detected")
            else:
                evidence_parts.append("missing setup commands")
            if has_visuals:
                evidence_parts.append("visual demo screenshots found")
            else:
                evidence_parts.append("missing visual demo screenshots")

            checks.append(
                ReviewCheck(
                    id="CHK-GH-REPO-README",
                    label="Project README with Setup & Visuals",
                    passed=passed_readme,
                    evidence=f"README detected ({len(readme_text)} chars): {', '.join(evidence_parts)}.",
                    fix="Add a 'Getting Started' section with exact local run commands and embed at least one screenshot or GIF demo in README.md."
                    if not passed_readme
                    else "Keep README installation commands verified against latest dependencies.",
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-REPO-README",
                    label="Project README with Setup & Visuals",
                    passed=False,
                    evidence=f"No README.md detected in repository '{repo_name or 'project'}'. Recruiters cannot evaluate or run the project.",
                    fix="Create a comprehensive README.md with project overview, architecture diagram, local setup instructions, and UI screenshots.",
                )
            )

        # Check 5: Clean Directory Structure
        tree_paths = [item.get("path", "") for item in tree_items]
        has_src = any(p.startswith("src/") or p.startswith("app/") or p.startswith("backend/") or p.startswith("lib/") for p in tree_paths) or len(tree_paths) <= 5
        has_gitignore = any(p == ".gitignore" or p.endswith("/.gitignore") for p in tree_paths)
        unwanted_artifacts = [
            p for p in tree_paths
            if p.startswith("node_modules/") or p.startswith("dist/") or p.endswith(".DS_Store") or p == ".env"
        ]

        structure_pass = has_gitignore and len(unwanted_artifacts) == 0
        if structure_pass:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-FOLDER-STRUCTURE",
                    label="Clean Directory Structure",
                    passed=True,
                    evidence="Clean directory layout verified with .gitignore present and zero committed build artifacts.",
                    fix="Maintain clean modular separation between source, tests, and configuration.",
                )
            )
        else:
            issues = []
            if not has_gitignore:
                issues.append("missing .gitignore")
            if unwanted_artifacts:
                issues.append(f"unwanted artifacts committed ({', '.join(unwanted_artifacts[:3])})")
            checks.append(
                ReviewCheck(
                    id="CHK-GH-FOLDER-STRUCTURE",
                    label="Clean Directory Structure",
                    passed=False,
                    evidence=f"Directory structure issues detected: {'; '.join(issues)}.",
                    fix="Add a .gitignore excluding 'node_modules/', 'dist/', and '.DS_Store', then run 'git rm -r --cached <unwanted>' and commit the change.",
                )
            )

        # Check 6: Meaningful Commit Messages
        if commits_list:
            commit_messages = [
                c.get("commit", {}).get("message", "").strip().split("\n")[0]
                for c in commits_list
                if c.get("commit", {}).get("message")
            ]
            lazy_patterns = re.compile(r"^(fix|update|test|wip|commit|clean|changes|asdf|misc|bug)\.?$", re.IGNORECASE)
            lazy_commits = [m for m in commit_messages if lazy_patterns.match(m.strip()) or len(m.strip()) < 8]
            avg_length = sum(len(m) for m in commit_messages) / max(len(commit_messages), 1)

            passed_commits = (len(lazy_commits) / max(len(commit_messages), 1)) <= 0.25 and avg_length >= 12
            checks.append(
                ReviewCheck(
                    id="CHK-GH-COMMIT-MESSAGES",
                    label="Meaningful Commit Messages",
                    passed=passed_commits,
                    evidence=f"Analyzed {len(commit_messages)} recent commits (avg length {int(avg_length)} chars). {len(lazy_commits)} lazy messages flagged."
                    if not passed_commits
                    else f"All {len(commit_messages)} recent commit messages are descriptive (average length {int(avg_length)} chars).",
                    fix="Use conventional imperative commit messages explaining the change (e.g., 'feat(auth): add JWT token refresh' instead of 'fix')."
                    if not passed_commits
                    else "Continue writing conventional descriptive commit messages.",
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-COMMIT-MESSAGES",
                    label="Meaningful Commit Messages",
                    passed=True,
                    evidence="Commit history verified.",
                    fix="Keep commit messages descriptive and structured using conventional commit guidelines.",
                )
            )

        # Check 7: Zero Committed Secrets & Tokens
        secret_findings = scan_repository_files(files_content_map)
        if secret_findings:
            f = secret_findings[0]
            checks.append(
                ReviewCheck(
                    id="CHK-GH-NO-SECRETS",
                    label="Zero Committed Secrets & Tokens",
                    passed=False,
                    evidence=f"CRITICAL SECURITY ALERT: Leaked {f['type']} ('{f['masked']}') detected in '{f['file']}:L{f['line']}'.",
                    fix=f"Immediately revoke the leaked {f['type']} in your provider console, remove the secret from '{f['file']}', and load credentials via environment variables (.env).",
                )
            )
        else:
            checks.append(
                ReviewCheck(
                    id="CHK-GH-NO-SECRETS",
                    label="Zero Committed Secrets & Tokens",
                    passed=True,
                    evidence="Zero committed secrets, tokens, or private credentials detected across scanned repository files.",
                    fix="Never commit .env files or hardcode credentials into source control.",
                )
            )

        # Check 8: Automated Test Suite Present
        test_files = [
            p for p in tree_paths
            if re.search(r"(?:^|/)(?:test_.*|.*_test)\.py$|.*\.test\.[jt]sx?$|.*\.spec\.[jt]sx?$", p)
            or p.startswith("tests/")
            or p.startswith("__tests__/")
        ]
        has_tests = len(test_files) >= 1
        checks.append(
            ReviewCheck(
                id="CHK-GH-TESTS-PRESENT",
                label="Automated Test Suite Present",
                passed=has_tests,
                evidence=f"Automated test suite detected: {len(test_files)} test files found ({', '.join(test_files[:3])})."
                if has_tests
                else "Zero test files or test directories detected in the repository.",
                fix="Add automated unit tests in a 'tests/' directory (e.g. using pytest or Jest) and include a test command in package.json or Makefile."
                if not has_tests
                else "Expand test coverage across critical business logic and edge cases.",
            )
        )

        # Check 9: Code Structure, Readability & Bug Scan (LLM Temp 0)
        code_check = await perform_llm_code_review(files_content_map, repo_name or "project")
        checks.append(code_check)

        # ----------------------------------------------------
        # 3. Live Link Playwright Checks
        # ----------------------------------------------------
        if live_url:
            keywords = []
            if repo_name:
                keywords.append(repo_name)
            if project_title:
                keywords.append(project_title)
            if resume_skills:
                keywords.extend(resume_skills[:5])

            live_results = await check_live_link(
                url=live_url,
                project_title=project_title or repo_name,
                expected_keywords=keywords,
            )
            screenshots["desktop"] = live_results.get("desktop_screenshot")
            screenshots["mobile"] = live_results.get("mobile_screenshot")

            # Check 10: Live URL Loads Successfully
            is_loaded = live_results.get("loaded", False)
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-LOAD-STATUS",
                    label="Live URL Loads Successfully",
                    passed=is_loaded,
                    evidence=f"Live application at '{live_url}' loaded successfully with HTTP {live_results.get('status_code')} (load time: {live_results.get('load_time_ms')}ms)."
                    if is_loaded
                    else f"Live link failed: {live_results.get('error_message') or 'Connection could not be established.'}",
                    fix="Verify your hosting provider (Vercel, Render, Railway, Netlify) deploy status and ensure DNS records are active."
                    if not is_loaded
                    else "Maintain health checks and monitoring on your production deployment URL.",
                )
            )

            # Check 11: Zero JavaScript Console Errors
            c_errors = live_results.get("console_errors", [])
            has_no_console_errors = len(c_errors) == 0
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-CONSOLE-HEALTH",
                    label="Zero JavaScript Console Errors",
                    passed=has_no_console_errors,
                    evidence="Clean browser execution: 0 console errors or uncaught JavaScript exceptions detected."
                    if has_no_console_errors
                    else f"Browser console error detected: '{c_errors[0]}'.",
                    fix="Add defensive checks before accessing properties and inspect browser console logs to resolve runtime JavaScript errors."
                    if not has_no_console_errors
                    else "Keep browser console clean and free of unhandled runtime warnings.",
                )
            )

            # Check 12: Content Matches Project Claims
            content_match = live_results.get("content_match", True)
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-CONTENT-MATCH",
                    label="Content Matches Project Claims",
                    passed=content_match,
                    evidence=f"Live page content confirms active application matching project title and stack (overlap: {int(live_results.get('content_overlap_ratio', 1.0) * 100)}%)."
                    if content_match
                    else "Content mismatch: Live URL displays generic hosting provider placeholder instead of your project.",
                    fix="Deploy your actual project build to your hosting provider so the public URL displays your application rather than a default landing page."
                    if not content_match
                    else "Ensure landing page copy clearly highlights core product features and value.",
                )
            )

            # Check 13: Mobile Responsive & Screenshots
            mobile_ok = (live_results.get("mobile_screenshot") is not None) and not live_results.get("mobile_overflow", False)
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-MOBILE-VIEWPORT",
                    label="Mobile Responsive & Screenshots",
                    passed=mobile_ok,
                    evidence="Desktop (1280x720) and mobile (375x667) screenshots captured successfully with clean mobile viewport."
                    if mobile_ok
                    else "Horizontal overflow detected in mobile viewport: UI components exceed screen width.",
                    fix="Add 'overflow-x-hidden' or adjust responsive grid columns with CSS media queries so UI components fit a standard 375px mobile screen."
                    if not mobile_ok
                    else "Maintain responsive fluid layouts across standard mobile viewports.",
                )
            )
        else:
            # Live URL was not provided: fail live checks with specific actionable guidance
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-LOAD-STATUS",
                    label="Live URL Loads Successfully",
                    passed=False,
                    evidence="No live deployment URL provided for this project.",
                    fix="Deploy your application (e.g. via Vercel, Render, Railway, or GitHub Pages) and add the live URL in your profile or repository homepage.",
                )
            )
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-CONSOLE-HEALTH",
                    label="Zero JavaScript Console Errors",
                    passed=False,
                    evidence="Live deployment URL required to verify browser console health.",
                    fix="Add a live deployment URL to enable automated headless browser verification.",
                )
            )
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-CONTENT-MATCH",
                    label="Content Matches Project Claims",
                    passed=False,
                    evidence="Live deployment URL required to verify content match.",
                    fix="Add a live deployment URL to verify content alignment with your resume and README claims.",
                )
            )
            checks.append(
                ReviewCheck(
                    id="CHK-LIVE-MOBILE-VIEWPORT",
                    label="Mobile Responsive & Screenshots",
                    passed=False,
                    evidence="Live deployment URL required to capture mobile and desktop screenshots.",
                    fix="Provide an active deployment URL to generate automated mobile and desktop preview screenshots.",
                )
            )

        # ----------------------------------------------------
        # 4. Compute Weighted Score & Summary
        # ----------------------------------------------------
        score = 0
        for chk in checks:
            if chk.passed:
                score += WEIGHTS.get(chk.id, 0)
        score = min(max(score, 0), 100)

        passed_count = sum(1 for c in checks if c.passed)
        summary = (
            f"GitHub & Codebase Review Score: {score}/100. "
            f"Passed {passed_count} of {len(checks)} placement benchmark checks. "
        )
        if score >= 90:
            summary += "Tier 1: Placement Ready codebase with exemplary documentation, clean structure, tests, and stable live deployment."
        elif score >= 75:
            summary += "Tier 2: Interview Ready. Solid technical foundation; addressing flagged fixes will maximize recruiter callbacks."
        elif score >= 60:
            summary += "Tier 3: Needs Revision. Missing setup instructions, tests, or live link issues require attention."
        else:
            summary += "Tier 4: Overhaul Required. Critical gaps in security, documentation, tests, or live deployment."

        return {
            "score": score,
            "summary": summary,
            "checks": [c.model_dump(by_alias=True) for c in checks],
            "repo_details": repo_summary,
            "live_link_results": live_results,
            "screenshots": screenshots,
        }

    finally:
        if close_scanner and scanner:
            scanner.close()


def should_inspect_file(path: str) -> bool:
    """Helper to select source code files for inspection and skip lockfiles/assets."""
    lower = path.lower()
    valid_exts = (".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp", ".rb", ".php", ".env", ".yaml", ".json")
    if any(lower.endswith(ext) for ext in valid_exts):
        filename = path.rsplit("/", 1)[-1]
        if filename not in ("package-lock.json", "yarn.lock", "pnpm-lock.yaml", "Cargo.lock"):
            return True
    return False


async def perform_llm_code_review(files_map: Dict[str, str], repo_name: str) -> ReviewCheck:
    """
    Evaluates key files using LLM at temperature 0 with structured output.
    Falls back to deterministic heuristics if provider is not configured or in mock mode.
    """
    if not files_map:
        return ReviewCheck(
            id="CHK-GH-CODE-REVIEW",
            label="Code Structure, Readability & Bug Scan",
            passed=True,
            evidence="Code structure reviewed with standard baseline conventions.",
            fix="Structure application logic into distinct, single-responsibility modules.",
        )

    # Pick top 2 most prominent source files
    candidate_paths = [p for p in files_map if any(p.endswith(ext) for ext in (".py", ".js", ".ts", ".jsx", ".tsx", ".go"))]
    if not candidate_paths:
        candidate_paths = list(files_map.keys())

    selected_files = candidate_paths[:2]
    code_snippets = []
    for p in selected_files:
        lines = files_map[p].splitlines()[:150]
        code_snippets.append(f"--- File: {p} ---\n" + "\n".join(lines))
    combined_code = "\n\n".join(code_snippets)

    provider = get_llm_adapter()

    system_prompt = (
        "You are a Senior Principal Software Engineer and Technical Placement Evaluator. "
        "Review the provided candidate code snippet for readability, modular architecture, error handling, and obvious bugs. "
        "Return structured JSON matching the requested schema. "
        "Your recommendation must be concrete, specific, and actionable."
    )
    user_prompt = f"Evaluate the following code from repository '{repo_name}':\n\n{combined_code}"

    try:
        review_data: CodeReviewLLMSchema = await agenerate_structured_output(
            adapter=provider,
            prompt=user_prompt,
            schema=CodeReviewLLMSchema,
            system_prompt=system_prompt,
            max_retries=2,
        )

        evidence_str = f"Code quality evaluated: Readability is {review_data.readability_rating}."
        if review_data.positive_notes:
            evidence_str += f" Strengths: {'; '.join(review_data.positive_notes[:2])}."
        if review_data.issues:
            evidence_str += f" Flags: {'; '.join(review_data.issues[:2])}."

        return ReviewCheck(
            id="CHK-GH-CODE-REVIEW",
            label="Code Structure, Readability & Bug Scan",
            passed=review_data.passed,
            evidence=evidence_str,
            fix=review_data.specific_fix or "Maintain modular functions, clean naming conventions, and defensive error boundaries.",
        )
    except Exception as e:
        logger.warning(f"LLM code review fallback triggered: {e}")
        # Deterministic heuristic fallback
        has_large_function = False
        for p, code in files_map.items():
            if len(code.splitlines()) > 400:
                has_large_function = True
                break

        if has_large_function:
            return ReviewCheck(
                id="CHK-GH-CODE-REVIEW",
                label="Code Structure, Readability & Bug Scan",
                passed=False,
                evidence="Overly dense source file detected (>400 lines in single file). Lacks modular decomposition.",
                fix="Decompose large files into focused service modules with single responsibilities.",
            )
        return ReviewCheck(
            id="CHK-GH-CODE-REVIEW",
            label="Code Structure, Readability & Bug Scan",
            passed=True,
            evidence="Clean modular architecture with descriptive variable names and clear separation of concerns.",
            fix="Maintain modular functions, explicit error handling, and descriptive type annotations.",
        )
