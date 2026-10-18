# Placement Readiness Benchmark: Resume Rubric

This document specifies the official placement readiness benchmark rubric for student resumes in the **Placement Readiness Copilot**. Every check evaluates a concrete dimension of a student's technical resume to produce an objective verdict, factual evidence, and a specific actionable fix.

---

## 1. Overview & Core Philosophy

1. **Benchmark-Driven**: Every review evaluates the resume against a deterministic rubric. Each check returns `{ id, label, pass, evidence, fix }`.
2. **Deterministic-First Computation**: Wherever possible, checks are computed directly in code (page count, link extraction, layout metrics, heading detection). Subjective checks (grammar, tone, depth) use the LLM provider at temperature 0 with structured JSON output so repeated runs score within ±3 points.
3. **Specific, Non-Generic Fixes**: Fixes must state exactly what to add, delete, or move (e.g., *"Add your LeetCode profile link to the contact header"*, *"Move Projects above Education"*). Generic phrases like *"improve your resume"* or *"check grammar"* are strictly forbidden.
4. **Overall Score**: The overall score is an integer from 0 to 100 calculated from weighted rubric items.

---

## 2. Benchmark Checklist Specification

| Check ID | Label | Evaluation Method | Weight | Description & Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **`CHK-PAGE-COUNT`** | Exactly One Page | Deterministic Code (PyMuPDF) | 15 pts | The document must contain exactly 1 page (`page_count == 1`). Multi-page resumes fail for entry-level / MSOT student placements. |
| **`CHK-ATS-FRIENDLY`** | ATS-Friendly Formatting | Deterministic Code (PyMuPDF) | 15 pts | Must contain readable digital text stream (not scanned raster image), standard section headings (`Education`, `Experience`, `Projects`, `Skills`), and no text trapped inside images. |
| **`CHK-PROJECT-DETAILS`** | Project Completeness | Hybrid (Code Parser + LLM Temp 0) | 15 pts | Every project must include a concise description, declared tech stack, quantifiable impact/results, live deployment URL, and GitHub repository URL. |
| **`CHK-ACTION-RESULTS`** | Action Verbs & Measurable Results | Hybrid (Code Regex + LLM Temp 0) | 15 pts | Bullet points must start with strong active verbs (e.g., *Built, Engineered, Optimized, Designed*) and include measurable numerical results (percentages, user counts, latency reductions). |
| **`CHK-PROFILE-LINKS`** | LeetCode & GitHub Profile Links | Deterministic Code (Hyperlink & Regex Parser) | 10 pts | The contact header or links section must include both an active GitHub profile link (`github.com/<username>`) and a LeetCode profile link (`leetcode.com/u/<username>`). |
| **`CHK-VISUAL-LAYOUT`** | Clean Visual Layout & Consistency | Vision Model / Layout Heuristic Fallback | 10 pts | Consistent font families (<= 3 distinct fonts), uniform margins and alignments, balanced vertical spacing, and standard date formats (e.g., `MMM YYYY`). Evaluated via page image rendering. |
| **`CHK-SPELL-GRAMMAR`** | Zero Spelling & Grammar Mistakes | Local Dictionary + LLM Temp 0 | 10 pts | Zero spelling mistakes, typos, or syntax errors. Flags exact misspelled words and suggests the precise corrected word. |
| **`CHK-ACHIEVEMENTS`** | Co-curricular Achievements | Deterministic Code + Heading Parser | 10 pts | Includes a distinct section for co-curricular achievements, such as hackathons, open source contributions, industry certifications, or technical student club leadership. |

**Total Score**: 100 Points

---

## 3. Detailed Check Definitions

### Check 1: Single Page Format (`CHK-PAGE-COUNT`)
- **Weight**: 15 points
- **Method**: PyMuPDF `len(doc)`
- **Pass Criteria**: `page_count == 1`
- **Evidence Example**: 
  - *Pass*: `"Resume is exactly 1 page (512 words, 1 page rendered)."`
  - *Fail*: `"Resume has 2 pages. For undergraduate and master's placements, single-page resumes are strongly required by hiring recruiters."`
- **Specific Fix Example**:
  - *Fail*: `"Condense line spacing, margins, and bullet points to reduce total content onto exactly 1 page."`

---

### Check 2: Clean Visual Layout (`CHK-VISUAL-LAYOUT`)
- **Weight**: 10 points
- **Method**: PyMuPDF renders page to PNG pixmap (150 DPI). If a vision model is active, pass image; otherwise, inspect PyMuPDF layout dictionaries (spans, font families, bbox margins, date patterns).
- **Pass Criteria**: 
  - Font families <= 3 distinct fonts across the document.
  - Consistent left margin alignment (bounding boxes align within 4pt tolerance).
  - Vertical whitespace gaps do not exceed 25% of page height.
  - Date formats follow uniform patterns without jarring inconsistencies.
- **Evidence Example**:
  - *Pass*: `"Uniform layout verified: 2 font families (Helvetica, Helvetica-Bold), consistent left margin at 40pt, and standard 'MMM YYYY' date formats."`
  - *Fail*: `"Inconsistent date formats detected ('Summer 2023' mixed with '2023/01') and erratic left margins (x=40pt, x=75pt)."`
- **Specific Fix Example**:
  - *Fail*: `"Standardize all dates to 'MMM YYYY' format and align dates to the right margin with consistent tabs."`

---

### Check 3: Zero Spelling or Grammar Mistakes (`CHK-SPELL-GRAMMAR`)
- **Weight**: 10 points
- **Method**: Deterministic resume dictionary analysis coupled with LLM evaluation at `temperature=0.0` with structured JSON schema.
- **Pass Criteria**: Zero detected typos or grammatical errors.
- **Evidence Example**:
  - *Pass*: `"No spelling or grammatical errors detected across all sections."`
  - *Fail*: `"Found spelling errors: 'managment' -> 'management', 'expereince' -> 'experience', 'softare' -> 'software'."`
- **Specific Fix Example**:
  - *Fail*: `"Correct spelling of 'managment' to 'management' in the Acme Cloud Solutions section."`

---

### Check 4: Every Project Has Complete Details (`CHK-PROJECT-DETAILS`)
- **Weight**: 15 points
- **Method**: Project section parser inspecting project blocks for (1) title, (2) description, (3) tech stack, (4) impact metrics, (5) live URL, (6) GitHub repository URL.
- **Pass Criteria**: All parsed projects contain tech stack, clear description, impact, live link, and GitHub repository URL.
- **Evidence Example**:
  - *Pass*: `"All 2 projects contain clear descriptions, declared tech stacks, measurable impact, GitHub repository links, and live deployment URLs."`
  - *Fail*: `"Project 'Readiness Copilot' has description and GitHub link, but is missing a live demo URL. Project 'Task Queue' lacks quantifiable impact metrics."`
- **Specific Fix Example**:
  - *Fail*: `"Add a live deployment URL (e.g., https://your-app.vercel.app) to 'Readiness Copilot' and quantify its throughput improvement."`

---

### Check 5: LeetCode & GitHub Profile Links Present (`CHK-PROFILE-LINKS`)
- **Weight**: 10 points
- **Method**: Hyperlink annotations (`page.get_links()`) and regex scanning over contact header text.
- **Pass Criteria**: Found active GitHub URL matching `github.com/[a-zA-Z0-9_-]+` and LeetCode URL matching `leetcode.com/(u/)?[a-zA-Z0-9_-]+`.
- **Evidence Example**:
  - *Pass*: `"Found both GitHub (https://github.com/alexrivera) and LeetCode (https://leetcode.com/u/alexrivera) profile links in header."`
  - *Fail*: `"Found GitHub link (https://github.com/alexrivera), but LeetCode profile link is missing from contact information."`
- **Specific Fix Example**:
  - *Fail*: `"Add your LeetCode profile URL (e.g., https://leetcode.com/u/yourhandle) to the top contact header next to your GitHub link."`

---

### Check 6: Co-curricular Achievements Included (`CHK-ACHIEVEMENTS`)
- **Weight**: 10 points
- **Method**: Section heading detection (`achievements`, `awards`, `certifications`, `hackathons`) and content parsing.
- **Pass Criteria**: Contains a distinct achievements section with at least 1 verified achievement, certification, hackathon placement, or leadership role.
- **Evidence Example**:
  - *Pass*: `"Achievements section detected with 2 items: '1st Place Winner at HackCal 2023', 'AWS Certified Cloud Practitioner'."`
  - *Fail*: `"No co-curricular achievements, hackathons, certifications, or leadership section detected."`
- **Specific Fix Example**:
  - *Fail*: `"Add an 'Achievements' or 'Certifications' section highlighting hackathon awards, cloud certifications (e.g. AWS), or tech club leadership."`

---

### Check 7: Bullet Points Start with Action Verbs & Show Measurable Results (`CHK-ACTION-RESULTS`)
- **Weight**: 15 points
- **Method**: Analyzes all bullet points across Experience and Projects. Evaluates leading token against strong action verb taxonomy and checks presence of quantifiable metric patterns (`\d+[%kKmMbB]?`, numbers, percentages).
- **Pass Criteria**: >= 80% of bullets start with strong action verbs and >= 60% of bullets include measurable numerical results.
- **Evidence Example**:
  - *Pass*: `"5 of 6 bullets start with strong action verbs (Developed, Containerized, Improved, Built, Implemented); 4 of 6 bullets contain quantified results (50k DAU, 35% query speedup)."`
  - *Fail*: `"Bullets lack active verbs or measurable impact: 'Worked on stuff for the website' starts with weak passive phrasing and contains zero metrics."`
- **Specific Fix Example**:
  - *Fail*: `"Rewrite 'Worked on stuff for the website' to start with an action verb and add a measurable metric (e.g., 'Engineered responsive checkout UI in React, reducing drop-off by 18%')."`

---

### Check 8: ATS-Friendly Formatting (`CHK-ATS-FRIENDLY`)
- **Weight**: 15 points
- **Method**: PyMuPDF text stream extraction (`page.get_text("text")`), section heading recognition, and image-to-text density analysis.
- **Pass Criteria**:
  - Extracted digital text length >= 250 characters.
  - Document is not an image-only rasterized/scanned PDF (image coverage with 0 extractable text).
  - Recognizes standard section headings (`Education`, `Experience`, `Projects`, `Skills`).
- **Evidence Example**:
  - *Pass*: `"Document contains 2,450 characters of searchable digital text and all 4 standard ATS headings (Education, Experience, Projects, Technical Skills)."`
  - *Fail*: `"Document contains 0 characters of readable text. The resume is an image-only scanned PDF, which will be completely unreadable by ATS systems."`
- **Specific Fix Example**:
  - *Fail*: `"Export your resume directly as a PDF from Google Docs, Microsoft Word, or LaTeX so that text is digitally selectable rather than a scanned image."`

---

## 4. Scoring Computation & Grade Tiers

- **Total Score**: Sum of weighted points for passed checks (with calibrated partial credit for checks like links or bullets where 1 of 2 criteria passes).
- **Tiers**:
  - **90 - 100**: *Placement Ready (Tier 1)* – Strong competitive candidate ready for top-tier applications.
  - **75 - 89**: *Interview Ready with Minor Fixes (Tier 2)* – Strong foundation; addressing specific fixes will maximize interview callbacks.
  - **60 - 74**: *Needs Revision (Tier 3)* – Missing key links, metrics, or layout standards.
  - **< 60**: *Critical Formatting Overhaul Required (Tier 4)* – Multi-page, image-only, or major missing sections.

---

# Placement Readiness Benchmark: LinkedIn Rubric

This section specifies the official placement readiness benchmark rubric for student LinkedIn profiles in the **Placement Readiness Copilot**. It evaluates profile completeness, specificity, alignment with the candidate's verified resume, and relevance to their declared target role.

---

## 5. Overview & Philosophy

1. **Benchmark-Driven & Rule 2 Compliant**: Every LinkedIn review returns the standard review schema `{ checks, score, fixes, rewrites }`, where each check is `{ id, label, pass, evidence, fix }`.
2. **Deterministic-First Computation**: Computes photo presence, headline length/format, About section length/structure, experience/project resume alignment, and skill-role relevance directly in code. Subjective checks and rewrites use the LLM provider at temperature 0 with strict schema enforcement to guarantee score consistency within ±3 points.
3. **Specific, Non-Generic Fixes**: Fixes state concrete adjustments (e.g., *"Update your headline to highlight your primary stack and target role: Full Stack Engineer | React, Node.js, Python"*, *"Update LinkedIn experience to include 'Acme Corp' as 'Software Engineer Intern' to match your resume"*).
4. **Ready-to-Paste Profile Rewrites**: Returns verified, ready-to-paste rewrites for Headline (strictly $\le 220$ characters) and About summary. Rewrites are grounded 100% in verified candidate facts from their profile and resume, with zero invented companies, degrees, or skills.
5. **Dual Input Support**: Evaluates both official LinkedIn PDF export documents and direct pasted profile text.

---

## 6. LinkedIn Benchmark Checklist Specification

| Check ID | Label | Evaluation Method | Weight | Description & Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **`CHK-LI-PHOTO`** | Professional Profile Photo | Deterministic (Image stream / profile metadata) | 10 pts | Profile photo must be present. In PDF export, detects embedded header photo; in pasted text, verifies profile photo indicator/declaration. |
| **`CHK-LI-HEADLINE`** | Headline Present & Specific | Deterministic + Rule Evaluator | 20 pts | Must be non-empty, $\le 220$ characters, and specific. Rejects generic titles (e.g., *"Student at MSOT"*, *"Aspiring Developer"*, *"Looking for opportunities"*). Must declare target technical role and key skills/domains. |
| **`CHK-LI-ABOUT`** | About Section Present & Substantive | Deterministic + Content Inspector | 20 pts | Must be present, substantive ($\ge 150$ characters and $\ge 30$ words), with structured career focus, core competencies, and career objectives. Rejects empty or 1-sentence summaries. |
| **`CHK-LI-RESUME-MATCH`** | Experience & Projects Match Resume | Deterministic Cross-Reference Comparator | 25 pts | LinkedIn work experience titles, companies, and project titles must align with the candidate's verified resume. Contradictions (e.g., conflicting job titles, unverified senior positions) or omission of major experiences are flagged with the exact conflicting item. |
| **`CHK-LI-SKILLS-ROLE`** | Skills Listed & Relevant to Role | Deterministic Skills Taxonomy | 25 pts | Must list at least 5 relevant technical skills directly aligned with the candidate's target placement role (e.g., Full Stack, Backend, Frontend, Data/ML). Flags missing foundational stack competencies. |

**Total Score**: 100 Points

---

## 7. Detailed Check Definitions

### Check 1: Professional Profile Photo (`CHK-LI-PHOTO`)
- **Weight**: 10 points
- **Method**: PyMuPDF page-1 image object analysis or profile metadata parsing.
- **Pass Criteria**: Profile image object detected in top header region or profile photo confirmed present.
- **Evidence Example**:
  - *Pass*: `"Profile photo detected in header (dimensions: 240x240px)."`
  - *Fail*: `"No profile photo detected. Profiles without a professional photo receive up to 21x fewer profile views."`
- **Specific Fix Example**:
  - *Fail*: `"Upload a clear, high-resolution professional headshot with good lighting and a neutral background."`

---

### Check 2: Headline Present & Specific (`CHK-LI-HEADLINE`)
- **Weight**: 20 points
- **Method**: Character length validator ($\le 220$ characters) + regex heuristic for generic phrasing (`student`, `seeking`, `aspiring`, `looking for`).
- **Pass Criteria**: Headline is present, length is between 15 and 220 characters, specifies target role (e.g., *Full Stack Engineer*, *Backend Developer*), and names at least 2 concrete technical skills or domains.
- **Evidence Example**:
  - *Pass*: `"Headline is specific (76 chars): 'Full Stack Developer | React, Node.js, Python | Building Scalable Web Apps'."`
  - *Fail*: `"Headline is generic (15 chars): 'Student at MSOT'. Does not declare target technical role or core competencies."`
- **Specific Fix Example**:
  - *Fail*: `"Replace generic headline with a specific, value-driven title under 220 chars: 'Full Stack Engineer | React, TypeScript, Python & FastAPI | MSOT'."`

---

### Check 3: About Section Present & Substantive (`CHK-LI-ABOUT`)
- **Weight**: 20 points
- **Method**: Text length and paragraph structure analysis ($\ge 150$ chars, $\ge 30$ words).
- **Pass Criteria**: About section is present, exceeds 150 characters, and articulates technical expertise, key project achievements, and placement career goals.
- **Evidence Example**:
  - *Pass*: `"About section is substantive (412 chars, 68 words) covering full-stack experience, key projects, and placement objectives."`
  - *Fail*: `"About section is too brief (42 chars): 'I love coding and building web applications.' Lacks technical depth and background details."`
- **Specific Fix Example**:
  - *Fail*: `"Expand About section to 2-3 structured paragraphs highlighting your technical skills, key projects with measurable impact, and what roles you are targeting."`

---

### Check 4: Experience & Projects Match Resume (`CHK-LI-RESUME-MATCH`)
- **Weight**: 25 points
- **Method**: Cross-reference entity matching between parsed LinkedIn experience/projects and stored resume data.
- **Pass Criteria**: All listed positions match resume company names and role levels. Zero contradictory job titles (e.g. "VP of Engineering" vs "Software Engineer Intern") and major resume experiences are represented.
- **Evidence Example**:
  - *Pass*: `"All 2 LinkedIn experiences ('Software Engineer Intern at Acme Corp', 'Frontend Developer at Beta Labs') match the verified resume."`
  - *Fail*: `"Mismatch detected: LinkedIn lists 'VP of Engineering at Stripe' whereas Resume lists 'Frontend Intern at Stripe'. Experience records do not align."`
- **Specific Fix Example**:
  - *Fail*: `"Update LinkedIn role title from 'VP of Engineering' to 'Frontend Intern' at Stripe to ensure consistency across job applications."`

---

### Check 5: Skills Listed & Relevant to Target Role (`CHK-LI-SKILLS-ROLE`)
- **Weight**: 25 points
- **Method**: Matches extracted LinkedIn skills against curated placement role skill taxonomies.
- **Pass Criteria**: Contains $\ge 5$ verified technical skills relevant to target role (e.g., for Full Stack: React, JavaScript, Python, FastAPI, Docker, PostgreSQL).
- **Evidence Example**:
  - *Pass*: `"Found 8 relevant technical skills for Full Stack Engineer: React, TypeScript, Python, FastAPI, PostgreSQL, Docker, Git, Tailwind CSS."`
  - *Fail*: `"Found only 2 skills (HTML, CSS). Missing core competencies for Full Stack Engineer role (e.g., Python, React, SQL, Docker)."`
- **Specific Fix Example**:
  - *Fail*: `"Add core technical skills to your LinkedIn profile: Python, React, FastAPI, PostgreSQL, and Docker."`

---

## 8. Ready-to-Paste Profile Rewrites Specification

Every LinkedIn benchmark review generates two tailored suggestions ready for one-click copy to clipboard:

1. **`headline` rewrite**:
   - Synthesizes student's target role, top 2-3 verified languages/frameworks, and domain focus.
   - Guaranteed $\le 220$ characters.
   - Strictly derived from verified profile and resume data; no invented titles or seniority levels.
2. **`about` rewrite**:
   - Structured in 2 concise, engaging paragraphs:
     - Paragraph 1: Background, technical focus, and core technologies mastered.
     - Paragraph 2: Key project achievements (with real metrics from resume) and candidate's immediate career goal/availability.
   - Strictly derived from verified profile and resume data; zero hallucinations.

---

## 9. LinkedIn Scoring Computation & Grade Tiers

- **Total Score**: Sum of weighted points (0 to 100).
- **Tiers**:
  - **90 - 100**: *Tier 1 (Placement Ready)* – Highly optimized profile aligned with hiring recruiter search criteria.
  - **75 - 89**: *Tier 2 (Interview Ready with Minor Fixes)* – Strong profile; applying specific rewrites and fixes maximizes recruiter inbounds.
  - **60 - 74**: *Tier 3 (Needs Revision)* – Missing substantive About section, skills, or has discrepancies with resume.
  - **< 60**: *Tier 4 (Critical Overhaul Required)* – Incomplete profile, generic headline, or significant contradictions with verified resume.

---

# Placement Readiness Benchmark: GitHub & Live Deployment Rubric

This section specifies the official placement readiness benchmark rubric for student GitHub repositories, codebase quality, and live production deployments in the **Placement Readiness Copilot**. It systematically checks developer consistency, repo professionalism, code cleanliness, secrets security, and live deployment stability via headless browser automation.

---

## 10. Overview & Core Philosophy

1. **Benchmark-Driven & Rule 2 Compliant**: Every GitHub and live deployment review returns the standard review schema `{ checks, score, summary, repo_details, live_link_results, screenshots }`, where each check is `{ id, label, pass, evidence, fix }`.
2. **Deterministic-First Computation**: Repository metadata, branch trees, profile README, commit intervals, secret scanning (regex), folder hierarchy, test discovery, and Playwright network/console captures are evaluated deterministically in code. The LLM is used only for subjective code quality (structure, readability, obvious bugs) at temperature 0 with strict schema enforcement so repeated runs score within ±3 points.
3. **Specific, Non-Generic Fixes**: Fixes state concrete adjustments (e.g., *"Add a .gitignore to exclude .env and invalidate the leaked AWS key 'AKIA...' immediately"*, *"Add setup instructions (e.g. 'npm install && npm run dev') and UI screenshot images to README.md"*).
4. **Public Data & Privacy Compliance**: Only public GitHub profile and repository data are evaluated. Optional GitHub tokens can be provided by the user to lift rate limits (from 60 to 5,000 req/hr). No private credentials or student logins are ever scraped.
5. **Robust Timeouts & Resilience**: Headless browser automation enforces strict maximum page-load timeouts (default 15 seconds) so unreachable or slow domains fail gracefully with clear diagnostic messages instead of hanging.

---

## 11. GitHub & Live Link Benchmark Checklist Specification

| Check ID | Label | Evaluation Method | Weight | Description & Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **`CHK-GH-PROFILE-README`** | Profile README Present | Deterministic GitHub REST API | 5 pts | Profile repository `<username>/<username>` must exist and contain a non-empty `README.md` introducing the candidate and their technical stack. |
| **`CHK-GH-PINNED-REPOS`** | Pinned / Featured Repositories | Deterministic GitHub REST API | 5 pts | Candidate must feature or pin repositories (or maintain public featured projects) rather than presenting an uncurated profile. |
| **`CHK-GH-COMMIT-ACTIVITY`** | Regular Commit Activity | Deterministic GitHub Events API | 10 pts | Active public commits or push events within the last 90 days, demonstrating sustained coding momentum rather than an abandoned profile. |
| **`CHK-GH-REPO-README`** | Project README with Setup & Visuals | Deterministic Markdown AST & Regex | 10 pts | Target repository README must contain concrete setup steps (commands such as `npm`, `pip`, `docker`, `cargo`) and visual UI screenshots or architecture diagrams. |
| **`CHK-GH-FOLDER-STRUCTURE`** | Clean Directory Structure | Deterministic Git Tree Inspector | 5 pts | Standard project organization (`src/`, `app/`, `components/`, `tests/`, `.gitignore`). Rejects dumping build artifacts (`node_modules/`, `dist/`, `.DS_Store`) or flat root dumps. |
| **`CHK-GH-COMMIT-MESSAGES`** | Meaningful Commit Messages | Deterministic Commit Log Parser | 5 pts | Analyzes recent commits. Rejects lazy single-word messages (e.g., *"update"*, *"fix"*, *"wip"*, *"asdf"*, *"test"*). Requires descriptive imperative messages with average length $\ge 12$ characters. |
| **`CHK-GH-NO-SECRETS`** | Zero Committed Secrets & Tokens | Deterministic Security Regex Scanner | 15 pts | Codebase must be 100% free of leaked AWS access keys, private keys, GitHub PATs, Slack tokens, OpenAI keys, or database credentials. |
| **`CHK-GH-TESTS-PRESENT`** | Automated Test Suite Present | Deterministic File Pattern Matcher | 10 pts | Target repository must contain automated unit or integration tests (e.g., `test_*.py`, `*.test.js`, `*.spec.ts`, `tests/` directory). |
| **`CHK-GH-CODE-REVIEW`** | Code Structure, Readability & Bug Scan | LLM Review (Temp 0 Structured Output) | 10 pts | Evaluates main application entry points for modularity, clean naming conventions, basic error handling, and absence of obvious bugs. |
| **`CHK-LIVE-LOAD-STATUS`** | Live URL Loads Successfully | Playwright Headless Browser | 10 pts | Live deployment URL loads with HTTP 200–299 status code within a strict 15-second timeout, with no unhandled connection/DNS errors. |
| **`CHK-LIVE-CONSOLE-HEALTH`** | Zero JavaScript Console Errors | Playwright Console Event Listener | 5 pts | Web page renders without uncaught exceptions or `console.error` logs fired during execution. |
| **`CHK-LIVE-CONTENT-MATCH`** | Content Matches Project Claims | NLP / Text Heuristic Comparator | 5 pts | Extracted live page text and headings roughly correspond to the project title, README description, and declared tech stack. |
| **`CHK-LIVE-MOBILE-VIEWPORT`** | Mobile Responsive & Screenshots | Playwright Viewport Capture | 5 pts | Renders cleanly in a mobile viewport (`375x667`) without horizontal blowout; generates and saves desktop (`1280x720`) and mobile screenshots. |

**Total Score**: 100 Points

---

## 12. Detailed Check Definitions

### Check 1: Profile README Present (`CHK-GH-PROFILE-README`)
- **Weight**: 5 points
- **Method**: GitHub REST API `GET /repos/{username}/{username}/readme`
- **Pass Criteria**: Status 200, content length $\ge 100$ characters.
- **Evidence Example**:
  - *Pass*: `"Profile README detected in repository 'alexrivera/alexrivera' (1,420 characters) introducing candidate focus and tech stack."`
  - *Fail*: `"No profile README detected for GitHub user 'alexrivera'. Creating a profile README showcases technical identity to recruiters."`
- **Specific Fix Example**:
  - *Fail*: `"Create a special public repository named exactly 'alexrivera' with a README.md introducing your technical background, featured projects, and core languages."`

---

### Check 2: Pinned / Featured Repositories (`CHK-GH-PINNED-REPOS`)
- **Weight**: 5 points
- **Method**: GitHub API profile inspection
- **Pass Criteria**: User has at least 2 public repositories with stars, descriptions, or pinned status.
- **Evidence Example**:
  - *Pass*: `"Candidate features 4 public showcase repositories with descriptions and defined topics."`
  - *Fail*: `"Only 1 public repository found, or repositories lack descriptions and topics."`
- **Specific Fix Example**:
  - *Fail*: `"Pin your top 2-4 strongest full-stack and systems projects to your GitHub profile header with clear one-line descriptions and topic tags."`

---

### Check 3: Regular Commit Activity (`CHK-GH-COMMIT-ACTIVITY`)
- **Weight**: 10 points
- **Method**: GitHub Events API `GET /users/{username}/events/public`
- **Pass Criteria**: Candidate has at least 5 public push events or commit events across the past 90 days.
- **Evidence Example**:
  - *Pass*: `"Consistent developer activity verified: 28 public commit events recorded over the last 90 days."`
  - *Fail*: `"Zero public commit events detected in the last 90 days. Recruiter perception flags inactive or abandoned profiles."`
- **Specific Fix Example**:
  - *Fail*: `"Commit code regularly (at least 2-3 times per week) across your ongoing coursework, capstone projects, or open-source repositories."`

---

### Check 4: Project README with Setup & Visuals (`CHK-GH-REPO-README`)
- **Weight**: 10 points
- **Method**: AST and regex parsing of repository `README.md`
- **Pass Criteria**: README contains setup instructions (`npm install`, `docker run`, `pip install`, `make`, etc.) AND visual screenshots or demo media (`<img ...>`, `![...](...)`).
- **Evidence Example**:
  - *Pass*: `"README contains clear setup commands ('npm install', 'npm run dev') and 2 application screenshot images."`
  - *Fail*: `"README exists (420 chars) but is missing local installation/setup commands and visual demo screenshots."`
- **Specific Fix Example**:
  - *Fail*: `"Add a 'Getting Started' section with exact local run commands and embed at least one screenshot or GIF demo in README.md."`

---

### Check 5: Clean Directory Structure (`CHK-GH-FOLDER-STRUCTURE`)
- **Weight**: 5 points
- **Method**: Inspects recursive git tree for standard directory hierarchies and unwanted build artifacts.
- **Pass Criteria**: Standard layout present (`src/`, `app/`, `components/`, etc.); `.gitignore` present; zero committed build directories (`node_modules/`, `dist/`, `.env`, `.DS_Store`).
- **Evidence Example**:
  - *Pass*: `"Clean modular directory layout verified (src/, tests/, public/) with active .gitignore."`
  - *Fail*: `"Unwanted artifacts committed in repository root: 'node_modules/' folder (4,120 files) and '.DS_Store' detected."`
- **Specific Fix Example**:
  - *Fail*: `"Add a .gitignore excluding 'node_modules/', 'dist/', and '.DS_Store', then run 'git rm -r --cached node_modules' and commit the change."`

---

### Check 6: Meaningful Commit Messages (`CHK-GH-COMMIT-MESSAGES`)
- **Weight**: 5 points
- **Method**: Analyzes recent commit messages from repository history.
- **Pass Criteria**: $< 20\%$ lazy commit messages (e.g. *"fix"*, *"update"*, *"commit"*, *"test"*, *"wip"*); average commit message length $\ge 12$ characters.
- **Evidence Example**:
  - *Pass*: `"All 10 recent commit messages are descriptive (avg length 38 chars), e.g., 'feat: integrate Stripe checkout webhook handler'."`
  - *Fail*: `"5 of 10 recent commits use generic low-quality messages: 'fix', 'update', 'test', 'wip'."`
- **Specific Fix Example**:
  - *Fail*: `"Use conventional imperative commit messages explaining the change (e.g., 'fix(auth): handle expired JWT refresh token' instead of 'fix')."`

---

### Check 7: Zero Committed Secrets & Tokens (`CHK-GH-NO-SECRETS`)
- **Weight**: 15 points
- **Method**: Deterministic multi-pattern regex scanner over text files in repo tree.
- **Pass Criteria**: Zero detected credentials (AWS keys, private keys, PATs, Slack/OpenAI tokens, database passwords).
- **Evidence Example**:
  - *Pass*: `"Zero committed secrets or credentials detected across all repository files."`
  - *Fail*: `"CRITICAL SECURITY ALERT: Leaked AWS Access Key ID ('AKIAIOSFODNN7...') found in 'config/aws.py:L14'."`
- **Specific Fix Example**:
  - *Fail*: `"Immediately revoke the leaked AWS key in AWS IAM Console, remove the secret from 'config/aws.py', and load credentials using environment variables (.env with python-dotenv)."`

---

### Check 8: Automated Test Suite Present (`CHK-GH-TESTS-PRESENT`)
- **Weight**: 10 points
- **Method**: Searches repo tree for test files (`test_*.py`, `*_test.py`, `*.test.js`, `*.spec.ts`, `tests/` directory).
- **Pass Criteria**: At least 1 automated test file or test suite configuration detected.
- **Evidence Example**:
  - *Pass*: `"Automated test suite detected: 4 test files found in 'backend/tests/' (pytest configured)."`
  - *Fail*: `"Zero test files or test directories detected in the repository."`
- **Specific Fix Example**:
  - *Fail*: `"Add automated unit tests in a 'tests/' directory (e.g. using pytest or Jest) and include a test script in package.json or Makefile."`

---

### Check 9: Code Structure, Readability & Bug Scan (`CHK-GH-CODE-REVIEW`)
- **Weight**: 10 points
- **Method**: LLM analysis of primary source files at `temperature=0` with structured JSON output schema.
- **Pass Criteria**: Clean modular functions, descriptive naming, basic exception handling, no unhandled null pointer or fatal syntax bugs.
- **Evidence Example**:
  - *Pass*: `"Clean modular architecture with descriptive variable names, type hints, and robust try/catch error boundaries."`
  - *Fail*: `"Monolithic 600-line function detected in 'server.js'; unhandled database connection rejection on lines 112-118."`
- **Specific Fix Example**:
  - *Fail*: `"Refactor the 600-line route handler in 'server.js' into distinct service functions and wrap database calls in try/catch blocks."`

---

### Check 10: Live URL Loads Successfully (`CHK-LIVE-LOAD-STATUS`)
- **Weight**: 10 points
- **Method**: Playwright headless Chromium navigation with maximum 15s timeout.
- **Pass Criteria**: HTTP response status is between 200 and 299; page navigation completes within timeout.
- **Evidence Example**:
  - *Pass*: `"Live application at 'https://copilot.msot.edu' loaded successfully with HTTP 200 OK (load time: 820ms)."`
  - *Fail*: `"Live link failed: Server returned HTTP 404 Not Found at 'https://broken-demo.vercel.app'."`
- **Specific Fix Example**:
  - *Fail*: `"Verify your hosting provider (Vercel, Render, Railway, Netlify) deploy status and update the repository live demo URL."`

---

### Check 11: Zero JavaScript Console Errors (`CHK-LIVE-CONSOLE-HEALTH`)
- **Weight**: 5 points
- **Method**: Playwright console listener (`page.on('console')`, `page.on('pageerror')`).
- **Pass Criteria**: Zero fatal `console.error` logs or unhandled script errors during initial render.
- **Evidence Example**:
  - *Pass*: `"Clean browser execution: 0 console errors or uncaught JavaScript exceptions detected."`
  - *Fail*: `"Browser console error detected: 'Uncaught TypeError: Cannot read properties of undefined (reading 'map')' in main.js:45."`
- **Specific Fix Example**:
  - *Fail*: `"Add defensive null-checks before mapping arrays in your frontend component to prevent runtime TypeError crashes."`

---

### Check 12: Content Matches Project Claims (`CHK-LIVE-CONTENT-MATCH`)
- **Weight**: 5 points
- **Method**: Extracts page text, meta description, and `<h1>`-`<h3>` headings; computes keyword similarity with project title, README, and resume tech stack.
- **Pass Criteria**: Keyword overlap ratio $\ge 0.35$ with declared project name and core technologies.
- **Evidence Example**:
  - *Pass*: `"Live page content confirms active application: headings and text match project title ('Readiness Copilot') and tech stack (React, FastAPI)."`
  - *Fail*: `"Content mismatch: Live URL displays generic hosting provider placeholder ('Welcome to your default NGINX page') instead of your project."`
- **Specific Fix Example**:
  - *Fail*: `"Deploy your actual project build to your hosting provider so the public URL displays your application rather than a default landing page."`

---

### Check 13: Mobile Responsive & Screenshots (`CHK-LIVE-MOBILE-VIEWPORT`)
- **Weight**: 5 points
- **Method**: Playwright dual viewport evaluation: Desktop (`1280x720`) and Mobile (`375x667`).
- **Pass Criteria**: Desktop and mobile screenshots captured and saved to disk; no horizontal body overflow (`scrollWidth > clientWidth`).
- **Evidence Example**:
  - *Pass*: `"Desktop (1280x720) and mobile (375x667) screenshots captured successfully. Clean mobile layout with 0 horizontal overflow."`
  - *Fail*: `"Horizontal overflow detected in mobile viewport: content width exceeds screen width by 142px."`
- **Specific Fix Example**:
  - *Fail*: `"Add 'overflow-x-hidden' or adjust responsive grid columns with CSS media queries so UI components fit a standard 375px mobile screen."`

---

## 13. Rate Limits & Graceful Degradation Specification

1. **GitHub API Rate Limits**:
   - Unauthenticated REST API requests are subject to GitHub's 60 requests/hour limit per public IP.
   - If an optional `GITHUB_TOKEN` is supplied via Settings or environment, requests use `Authorization: Bearer <token>`, raising the quota to 5,000 requests/hour.
   - When a 403 or 429 rate limit response is received from GitHub:
     - The system halts cleanly without throwing an unhandled exception or 500 error.
     - Returns a clean diagnostic payload: `"GitHub API rate limit exceeded. Provide an optional GitHub Personal Access Token in Settings to enjoy 5,000 requests/hour, or wait until the rate limit resets."`
2. **Playwright Timeout Safeguard**:
   - Navigation operations are hard-capped at 15,000ms.
   - If a URL is down, hangs, or drops connections, the Playwright promise rejects within the timeout and marks `CHK-LIVE-LOAD-STATUS` as failed with exact diagnostic details, returning immediate results to the user.

---

## 14. Scoring Computation & Grade Tiers

- **Total Score**: Sum of weighted points for passed checks (0 to 100).
- **Tiers**:
  - **90 - 100**: *Tier 1 (Placement Ready)* – Exemplary GitHub presence, clean code, tests present, zero secrets, and flawless live deployment.
  - **75 - 89**: *Tier 2 (Interview Ready with Minor Fixes)* – Solid technical project; addressing README visuals or test coverage will boost recruiter callbacks.
  - **60 - 74**: *Tier 3 (Needs Revision)* – Missing setup instructions, tests, or live link issues require attention.
  - **< 60**: *Tier 4 (Critical Overhaul Required)* – Leaked secrets, broken live link, missing README, or unorganized codebase.

---

# Placement Readiness Benchmark: Mock Interview Rubric

This section specifies the official placement readiness benchmark rubric for interactive technical & behavioral mock interview simulations in the **Placement Readiness Copilot**. It evaluates candidate technical depth, structured communication, grounded project experience, and architectural critical thinking.

---

## 15. Overview & Philosophy

1. **Benchmark-Driven & Rule 2 Compliant**: Each student answer is evaluated against a fixed 4-dimension rubric totaling 100 points. The overall session score is the arithmetic mean of all scored answers, feeding directly into the institutional Placement Readiness Score (Weight: 20 points).
2. **Grounded Question Generation**: Questions are never generic trivia. They are dynamically generated from the candidate's verified resume, parsed projects (e.g. *Readiness Copilot*, *Distributed Task Queue*), declared skills, and target placement role:
   - **Technical Questions**: Fundamental architecture, concurrency, database patterns, and API design tailored to candidate skills.
   - **Project Deep-Dive Questions**: Probing the deployment pipeline, infrastructure, challenges, and scalability bottlenecks of actual candidate projects.
   - **Behavioral Questions**: Assessing conflict resolution, ownership, and communication using the STAR framework.
3. **Adaptive Follow-Up Interrogation**: The AI interviewer acts adaptively—acknowledging answers, probing vague or superficial responses deeper, and transitioning smoothly across topics.
4. **Countdown Timer Session Discipline**: The student selects a 15-minute (standard) or 20-minute (comprehensive) session. Sessions enforce strict timer boundaries; when time expires, the session completes gracefully, grades completed questions, and synthesizes actionable tips.
5. **Replayable Transcripts**: All messages, timestamps, per-question rubric grades, and feedback summaries are permanently saved to SQLite (`interview_sessions`), enabling instant UI replay.

---

## 16. Fixed Per-Answer Benchmark Checklist Specification

| Rubric ID | Dimension | Evaluation Method | Weight | Description & Pass Criteria |
| :--- | :--- | :--- | :--- | :--- |
| **`CRIT-TECH-DEPTH`** | Technical Accuracy & Depth | Hybrid (Keyword heuristics + LLM Temp 0) | 35 pts | Evaluates correctness of technical concepts, frameworks, data structures, and architectural principles. Strong answers ($\ge 25$) name specific mechanisms (e.g. WAL mode, connection pooling, indexing, async event loops). Weak answers ($< 15$) rely on surface buzzwords without explanatory depth. |
| **`CRIT-CLARITY-COMM`** | Communication & Structural Clarity | Content Analyzer + LLM Temp 0 | 25 pts | Evaluates structure, conciseness, and articulation. For behavioral questions, rewards clear STAR framing (Situation, Task, Action, Result). For technical questions, rewards direct logical explanation. Weak answers ($< 12$) are fragmented, rambling, or one-word replies. |
| **`CRIT-GROUNDED-EXP`** | Grounded Experience & Relevance | Repository/Project Comparator + LLM | 25 pts | Evaluates whether claims are grounded in real project artifacts, tools, and measurable outcomes. Strong answers ($\ge 18$) cite exact tools used (Docker, Redis, ECS), deployment steps, and metrics (e.g. *reduced latency by 35%*, *50k DAU*). Weak answers speak in generic hypotheticals. |
| **`CRIT-CRITICAL-THINK`** | Problem-Solving & Trade-offs | LLM Temp 0 + Semantic Rationale Scan | 15 pts | Evaluates awareness of trade-offs, edge cases, scalability bottlenecks, and reasons why alternatives were rejected. Strong answers ($\ge 10$) explain *why* a particular library, cache, or database was chosen over alternatives. |

**Total Per-Answer Score**: 100 Points

---

## 17. Detailed Check Definitions

### Check 1: Technical Accuracy & Depth (`CRIT-TECH-DEPTH`)
- **Weight**: 35 points (Passing threshold: $\ge 25.0$ points)
- **Pass Criteria**: Answer uses precise terminology, accurately describes mechanisms, and explains underlying system behaviors without conceptual errors.
- **Evidence Example**:
  - *Pass (30/35 pts)*: `"Demonstrates accurate understanding of FastAPI async handlers, SQLAlchemy connection pooling, and Redis cache invalidation strategies."`
  - *Fail (12/35 pts)*: `"Mentioned using Python and Docker but did not explain container orchestration, networking, or database connection management."`
- **Specific Fix Example**:
  - *Fail*: `"Deepen technical precision with specific architectures, frameworks, and mechanisms (e.g. explain how Redis key TTLs and eviction policies are configured)."`

---

### Check 2: Communication & Structural Clarity (`CRIT-CLARITY-COMM`)
- **Weight**: 25 points (Passing threshold: $\ge 18.0$ points)
- **Pass Criteria**: Clear logical progression, concise delivery without filler, structured into coherent stages (Situation $\rightarrow$ Task $\rightarrow$ Action $\rightarrow$ Result for behavioral).
- **Evidence Example**:
  - *Pass (22/25 pts)*: `"Structured response clearly following the STAR framework: identified deadlock situation, defined action taken, and reported zero production errors as result."`
  - *Fail (8/25 pts)*: `"Answer was a single 3-word phrase lacking context, structure, and professional articulation."`
- **Specific Fix Example**:
  - *Fail*: `"Structure answers using the STAR method (Situation, Task, Action, Result) for behavioral questions and direct progressive logic for technical explanations."`

---

### Check 3: Grounded Experience & Relevance (`CRIT-GROUNDED-EXP`)
- **Weight**: 25 points (Passing threshold: $\ge 18.0$ points)
- **Pass Criteria**: Directly cites real repository code, verified project tools, deployment pipelines, and quantifiable metrics from the candidate's profile.
- **Evidence Example**:
  - *Pass (22/25 pts)*: `"Directly references 'Readiness Copilot' deployment pipeline using Docker Compose, PyMuPDF background threads, and 50ms latency metrics."`
  - *Fail (9/25 pts)*: `"Answers in generic hypotheticals ('one could use a server') without mentioning candidate's own projects or technologies."`
- **Specific Fix Example**:
  - *Fail*: `"Reference concrete repository code, deployed tools, and quantifiable metrics from your projects (e.g. 'reduced latency by 35%', 'deployed on AWS with Docker')."`

---

### Check 4: Problem-Solving & Trade-offs (`CRIT-CRITICAL-THINK`)
- **Weight**: 15 points (Passing threshold: $\ge 10.0$ points)
- **Pass Criteria**: Proactively addresses architectural trade-offs, limitations, edge cases, failure modes, and why alternatives were rejected.
- **Evidence Example**:
  - *Pass (13/15 pts)*: `"Discusses trade-offs between Redis in-memory caching and database load, noting memory constraints and eventual consistency considerations."`
  - *Fail (5/15 pts)*: `"No discussion of trade-offs, constraints, or why Redis was chosen over alternative cache backends."`
- **Specific Fix Example**:
  - *Fail*: `"Proactively discuss trade-offs, rejected alternatives, and why you selected specific solutions (e.g., explain why SQLite WAL mode was selected over PostgreSQL for local testing)."`

---

## 18. Overall Session Scoring & Tier Classification

- **Overall Session Score Formula**:
  $$\text{Interview Score} = \text{round}\left( \frac{1}{N} \sum_{i=1}^N S_i \right) \in [0, 100]$$
  where $S_i$ is the composite score for answer $i$ and $N$ is the count of completed answers.
- **Contribution to Readiness Index**:
  $$\Delta \text{Readiness} = \text{Interview Score} \times \frac{20}{100}$$
- **Performance Tiers**:
  - **75 – 100**: *Placement Ready (Tier 1)* – Strong competitive candidate demonstrating technical mastery, structured STAR communication, and deep project grounding.
  - **50 – 74**: *Almost Ready (Tier 2)* – Good foundational grasp; needs deeper technical precision or more structured behavioral delivery.
  - **0 – 49**: *Needs Revision (Tier 3)* – Very brief, generic, or off-topic answers requiring comprehensive interview coaching.


