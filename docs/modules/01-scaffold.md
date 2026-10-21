# Module 01: Scaffold & LLM Interface

## 1. What the Module Does
Module 01 sets up the full-stack foundation for the **Placement Readiness Copilot**:
- Monorepo structure with `backend/` (FastAPI, SQLite via SQLAlchemy, Pydantic v2, Pytest) and `frontend/` (React, Vite, Tailwind CSS).
- Unified multi-provider LLM interface in `backend/app/llm/` supporting **Ollama (local-first)**, **OpenAI**, **Anthropic Claude**, **Google Gemini**, and a deterministic **Mock Adapter**.
- Resilient JSON structured-output parser with self-correcting retry loop and schema validation.
- Secure local settings persistence with strict API key redacting across all logs and response payloads.
- Role-based access control (RBAC) supporting `student` and `admin` roles, JWT authentication, and secure password hashing.
- Chat-style UI shell with responsive sidebar navigation (`Profile`, `Reviews`, `Interview`, `Score`, `Jobs`, `Tracker`, `Settings`, `Admin`), chat message stream, and file upload button.
- One-command developer workflows via `Makefile` (`make dev`, `make test`, `make clean`).

---

## 2. How It Works (Flow with Exact Files and Functions)

### A. Authentication & Role Authorization Flow
1. **Registration & Password Hashing**:
   - The user submits email, password, and role to `POST /api/auth/register` in [auth.py](../../backend/app/routers/auth.py).
   - `hash_password(password)` in [auth.py](../../backend/app/auth.py) uses Python standard library `hashlib.pbkdf2_hmac` with a cryptographically secure 16-byte salt and 100,000 iterations of SHA-256 (`pbkdf2$sha256$100000$<salt>$<key>`).
   - The user record and an initial empty `Profile` are created in the SQLite database via [database.py](../../backend/app/database.py).
2. **Login & Token Generation**:
   - The user sends credentials to `POST /api/auth/login`.
   - `verify_password(plain, hashed)` in [auth.py](../../backend/app/auth.py) securely unpacks the stored salt and uses `hmac.compare_digest` to prevent timing attacks.
   - `create_access_token(data)` creates a signed HS256 JWT containing `sub` (user ID) and `role`.
3. **Role Enforcement**:
   - Protected endpoints declare dependencies: `get_current_user` decodes the token from the `Authorization: Bearer <token>` header.
   - Admin routes (such as `GET /api/admin/jobs` in [admin.py](../../backend/app/routers/admin.py)) inject `require_admin`. If `user.role != "admin"`, it immediately raises `HTTPException(status_code=403, detail="Admin privileges required")`.

### B. Settings & Zero-Leak Secret Management Flow
1. **Retrieval**:
   - The frontend calls `GET /api/settings` in [settings.py](../../backend/app/routers/settings.py).
   - `get_public_settings()` in [settings_service.py](../../backend/app/services/settings_service.py) reads `backend/data/settings.json`, but returns only boolean flags (`has_openai_key: bool`) and sanitized configs.
2. **Persistence**:
   - When updating settings via `POST /api/settings`, new keys are saved to `backend/data/settings.json` (git-ignored).
   - Sensitive strings and registered keys are passed to `register_secret_for_redaction(secret)` in [logging_config.py](../../backend/app/logging_config.py).
   - `SensitiveDataFilter` intercepts all Python and Uvicorn log records, redacting any API key pattern (`sk-...`, `AIza...`, `ant-...`) before it reaches stdout.

### C. LLM Provider Adapter & Structured Output Retry Loop
1. **Provider Resolution**:
   - `get_llm_adapter(provider, model)` in [factory.py](../../backend/app/llm/factory.py) reads the active configuration and instantiates the chosen adapter subclassing `BaseLLMAdapter` in [base.py](../../backend/app/llm/base.py).
2. **Ollama Execution**:
   - `OllamaAdapter.generate(...)` in [ollama_adapter.py](../../backend/app/llm/adapters/ollama_adapter.py) issues a POST request to `http://localhost:11434/api/chat` using `httpx`.
   - Explicitly configures `"format": "json"` and `"options": {"num_ctx": 8192}` with a 120-second timeout.
   - If Ollama is unreachable, it raises: `"Ollama is not running at <url>. Start it with: 'ollama serve'"`.
   - If the model is not found, it raises: `"Model '<model>' not found in Ollama. Pull it with: 'ollama pull <model>'"`.
3. **Structured Output Resilience**:
   - `generate_structured_output(adapter, prompt, schema, max_retries=2)` in [structured.py](../../backend/app/llm/structured.py) formats the user prompt with the JSON schema requirements at temperature 0.0.
   - `extract_json_from_text` strips markdown code blocks or conversational wrappers.
   - It validates the parsed JSON using `schema.model_validate(...)`.
   - If JSON decoding or schema validation fails, it records the exact error, adds a corrective user message to the conversation history, and invokes the model again.
   - If all retries fail, it raises `StructuredOutputError` containing the exact validation error message and raw output.

### D. Chat UI Shell & Sidebar Navigation
1. **Frontend App Layout**:
   - [App.jsx](../../frontend/src/App.jsx) holds the active tab state and current authenticated user state.
   - [Sidebar.jsx](../../frontend/src/components/Sidebar.jsx) renders the branded navigation items and user account status.
2. **Chat & File Upload**:
   - [ChatShell.jsx](../../frontend/src/components/ChatShell.jsx) provides a scrollable conversation stream with role-based bubbles and an input form.
   - Clicking the file attachment button triggers a hidden file input, sending the file to `POST /api/chat/upload`, which saves it into `backend/data/uploads/` and feeds confirmation back into the chat stream.

---

## 3. Key Design Decisions and Rejected Alternatives

1. **Direct `httpx` REST calls vs. Official Vendor SDKs (`openai`, `anthropic`, `google-genai`)**:
   - *Decision*: Implemented direct HTTP clients using `httpx` for OpenAI, Claude, Gemini, and Ollama.
   - *Reason*: Lightweight, zero versioning conflicts, unified sync/async patterns, precise timeout handling, and custom options (`num_ctx: 8192`, `format: "json"`).
   - *Rejected*: Vendor SDKs bring heavy dependency trees, deprecate APIs rapidly, and create Pydantic v1/v2 compatibility issues.
2. **PBKDF2-HMAC-SHA256 vs. `passlib[bcrypt]`**:
   - *Decision*: Used standard library `hashlib.pbkdf2_hmac` with unique per-user salts.
   - *Reason*: 100% pure Python standard library reliability across all operating systems without requiring native C compilation or unmaintained `passlib` packages.
   - *Rejected*: `passlib` has deprecation bugs with `bcrypt>=4.0` in modern Python.
3. **Local JSON file for settings vs. SQLite Database Table**:
   - *Decision*: Persisted LLM settings in `backend/data/settings.json`.
   - *Reason*: Keeps API keys strictly outside of database dumps, migrations, and backups.
4. **Actionable Ollama Error Messages**:
   - *Decision*: Checked connection failures and model 404s to return explicit commands (`ollama serve`, `ollama pull <model>`).
   - *Reason*: Avoids confusing generic network errors and guides the student directly to resolution.

---

## 4. Shortcuts, Placeholders, or Faked Parts
- **Chat Router LLM Response**:
  - `POST /api/chat` currently generates conversational responses using the active LLM adapter. Module 02 will add the specific benchmark review parser.
- **Placeholder Pages**:
  - `Profile`, `Reviews`, `Interview`, `Score`, `Jobs`, and `Tracker` tabs render clean functional placeholder components in [Placeholders.jsx](../../frontend/src/pages/Placeholders.jsx). Their full benchmark calculation logic is scheduled for their respective modules.
- **File Upload Handler**:
  - `POST /api/chat/upload` saves uploaded resumes to `backend/data/uploads/`. PDF text extraction and deep AST parsing will be built in Module 02 (Resume Review).

---

## 5. Verify It Yourself

Run these 5 simple steps to verify the entire module:

### Step 1: Run All Tests
```bash
make test
```
**Expected Output**:
`20 passed in 0.40s` with green checkmarks across all tests.

### Step 2: Test Health and RBAC with curl
```bash
# 1. Health check
curl -s http://127.0.0.1:8000/health
# Expected: {"status":"ok","app":"Placement Readiness Copilot","service":"backend"}

# 2. Register student and capture token
STU_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{"email":"stu_demo@mirai.dev","password":"password123","role":"student"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin).get('email'))")

LOGIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"stu_demo@mirai.dev","password":"password123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin)['access_token'])")

# 3. Access admin route with student token
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $LOGIN_TOKEN" http://127.0.0.1:8000/api/admin/jobs
# Expected: 403
```

### Step 3: Verify Zero API Key Leakage
```bash
curl -s -X POST http://127.0.0.1:8000/api/settings \
  -H "Content-Type: application/json" \
  -d '{"provider":"openai","model":"gpt-4o","openai_api_key":"sk-secret-demo-key-12345"}' | grep "sk-secret"
# Expected: Empty (no output matches the secret string)
```

### Step 4: Verify Live Ollama Call
```bash
PYTHONPATH=backend backend/venv/bin/python -c "
from app.llm.adapters.ollama_adapter import OllamaAdapter
from app.llm.base import LLMMessage
adapter = OllamaAdapter(model='smollm:135m', base_url='http://localhost:11434')
res = adapter.generate([LLMMessage(role='user', content='Respond with JSON: {\"status\": \"ok\"}')], format_json=True)
print(res.content)
"
```
**Expected Output**:
Valid JSON output from Ollama (e.g. `{"status": "ok"}`).

### Step 5: Test One-Command Clean State Bootstrap
```bash
make clean
make dev
```
**Expected Output**:
Creates virtualenv, installs pip requirements, installs npm packages, starts Uvicorn at `http://0.0.0.0:8000` and Vite at `http://localhost:5173`.
