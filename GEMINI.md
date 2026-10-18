PROJECT: "Placement Readiness Copilot" for MSOT students. A single app with a chat interface where a student uploads their resume, LinkedIn, GitHub, LeetCode and projects, gets benchmark-based reviews, a mock interview and a placement readiness score, then finds, applies to and tracks jobs. MSOT staff can post jobs directly to students.

STACK: FastAPI (Python 3.11) + SQLite (SQLAlchemy) + React (Vite + Tailwind). Tests: pytest.

CORE RULES
1. LLM access goes ONLY through one provider interface in backend/llm/ with adapters for OpenAI, Claude, Gemini and Ollama, selectable in settings. The whole app must run fully locally with Ollama and no paid API.
2. Reviews are benchmark-driven. Each check returns {id, label, pass, evidence, fix}. Compute whatever can be computed in code (page count, link presence, headings) and use the LLM only for subjective checks. Use temperature 0 and structured JSON output so repeated runs score within ±3 points.
3. Fixes must be specific ("Move Projects above Education"), never generic ("improve your resume").
4. Privacy: the student can view, edit and delete all their data. Store only data they provide or public profile pages. Never scrape logged-in pages or use a student's login. Follow each job platform's rules: prefer official APIs, RSS, and Greenhouse/Lever public APIs, and respect robots.txt and rate limits.
5. Each module has its own folder, API routes and tests, and works on its own.
6. Everything runs with one command (make dev) and all tests with make test.
7. Work on ONLY the task I give you. Do not start later modules.

VERIFICATION RULES
- Never say a task is done until you have actually run it. Run pytest, start the backend and hit endpoints with curl, and for UI work start the frontend and test the flow in the browser.
- Finish every task with a Verification Report: the commands you ran, their real output, what passed, what failed, and what you could not verify and why.
- If anything fails, fix it and re-run before reporting. Never hide or skip failing tests.
- Mock only the LLM, never the thing being tested. Also run at least one real end-to-end check with Ollama or a real API key if one is configured.
- Re-run all earlier modules' tests after each task to confirm nothing regressed.

LEARNING RULES
- Before coding, give me a plan in plain language: which files you'll create, what each does, and how data flows between them. Wait for my approval.
- After building, give a "How it works" walkthrough: the flow from user action to result, naming the exact files and functions, in simple language.
- List the key design decisions and the alternatives you rejected.
- Give a "Verify it yourself" section: 3-5 manual steps I can run, with exact expected results.
- Flag any shortcut, placeholder, or faked part (hardcoded data, mocked responses, TODOs).
- Keep code readable, with short comments on the non-obvious parts.

DOCUMENTATION RULES (never skip)
After finishing any task, SAVE these as real files in the repo. Do not only print them in chat.
1. docs/modules/<NN>-<module-name>.md containing: what the module does, how it works (flow with exact files and functions), design decisions and rejected alternatives, shortcuts or faked parts, and "Verify it yourself" steps with expected results.
2. docs/verification/<NN>-<module-name>-report.md containing the commands run, real output, what passed, failed, and could not be verified.
3. Append a short entry to docs/test-report.md. Never overwrite earlier entries.
- NEVER delete, overwrite or shorten any file in docs/ from a previous task. Only add new files or append.
- If a later task changes an earlier module, append a dated "Changes" section to that module's file.
- A task is not complete until these files exist. List their paths at the end of your reply.
- Do not store these in scratch folders, artifact panels or anywhere outside the repo.
