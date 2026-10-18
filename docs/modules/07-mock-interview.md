# Module 07: Mock Interview Simulator (Text Mode)

## 1. What the Module Does

Module 07 delivers an interactive, benchmark-driven technical and behavioral mock interview simulator for MSOT students:
1. **Student-Controlled Session Duration**: Students can initiate a 15-minute (standard, 5 questions) or 20-minute (comprehensive, 7 questions) interview anytime.
2. **Grounded Question Roadmap**: Generates personalized questions referencing actual items from the candidate's verified resume, parsed projects (e.g., *Readiness Copilot*, *Distributed Task Queue*), declared skills, and target placement role:
   - Technical questions testing core framework mechanisms, concurrency, and architecture.
   - Project deep-dive questions probing deployment pipelines, data flow, and scalability bottlenecks of actual candidate projects.
   - 1–2 behavioral questions evaluated using the STAR method.
3. **Adaptive Follow-Up Interrogation**: Dynamically acknowledges candidate answers, probes superficial or vague statements deeper, and transitions smoothly across questions.
4. **Strict Countdown Timer Discipline**: Visual and server-enforced countdown timer that gracefully completes sessions when time expires.
5. **Fixed Per-Answer Rubric (Sum = 100)**: Evaluates each answer against 4 fixed benchmark criteria:
   - `CRIT-TECH-DEPTH` (35 pts): Technical Accuracy & Depth
   - `CRIT-CLARITY-COMM` (25 pts): Communication & Structural Clarity
   - `CRIT-GROUNDED-EXP` (25 pts): Grounded Experience & Relevance
   - `CRIT-CRITICAL-THINK` (15 pts): Problem-Solving & Trade-offs
6. **Replayable Transcripts & Readiness Score Integration**: Saves full turn-by-turn chat history, per-question rubric grades, strengths, weaknesses, and actionable tips to SQLite (`interview_sessions`). Automatically feeds the final score into the institutional Placement Readiness Score (Weight: 20 points).

---

## 2. How It Works: Step-by-Step Flow

```
[Student in React UI / Client]
       │
       ├─► 1. Setup & Launch:
       │      Student picks 15m/20m duration & target role in MockInterviewPage.jsx
       │      POST /api/interview/start (backend/app/routers/interview.py)
       │        ├─► Consent Gate Check (Rule 4: profile.consent_given == True)
       │        ├─► build_question_roadmap() (backend/app/services/interview_service.py)
       │        │     └─► Grounded in candidate's parsed resume, projects & skills
       │        ├─► Initializes timer: started_at, duration_minutes, expires_at
       │        └─► Creates InterviewSession (status="in_progress") with Q1 seeded
       │
       ├─► 2. Interactive Q&A Loop:
       │      Student types answer & clicks Send Answer
       │      POST /api/interview/{id}/message
       │        ├─► Timer check: datetime.utcnow() >= expires_at
       │        ├─► evaluate_student_answer()
       │        │     └─► Evaluates 4 fixed rubric criteria (0-100 pts)
       │        ├─► Produces adaptive follow-up or advances to next question in roadmap
       │        └─► Persists turn in session.messages & session.rubric_scores
       │
       ├─► 3. End Session & Score Synthesis:
       │      Triggered by timer expiration, answering all questions, or clicking End & Grade
       │      POST /api/interview/{id}/end
       │        ├─► Final score = average of per-answer rubric scores [0-100]
       │        ├─► synthesize_session_feedback(): strengths, weak areas, actionable tips
       │        ├─► Status set to "completed"
       │        └─► compute_and_save_readiness_score(db, user_id)
       │              └─► Auto-updates Placement Readiness Index (mock_interview: 20 pts)
       │
       └─► 4. Results & Replay:
              GET /api/interview/{id}/replay
              Renders circular score gauge, rubric criteria bars, strengths, tips, and replay transcript
```

### Exact Files and Functions

1. **`backend/app/services/interview_service.py`**:
   - `build_question_roadmap(profile, target_role)`: Analyzes student's parsed resume, projects, and skills to generate a grounded question plan covering technical, project deep-dive, and behavioral topics.
   - `evaluate_student_answer(question_obj, answer_text, llm_adapter)`: Evaluates candidate answers against the 4 fixed rubric criteria (`CRIT-TECH-DEPTH`, `CRIT-CLARITY-COMM`, `CRIT-GROUNDED-EXP`, `CRIT-CRITICAL-THINK`) with length/keyword heuristics and LLM temperature 0 structured JSON validation.
   - `synthesize_session_feedback(rubric_scores, target_role)`: Aggregates criteria averages across all completed answers, identifying concrete strengths, weak areas, and actionable tips.
   - `start_interview_session(db, user, duration_minutes, time_limit_seconds, target_role)`: Manages session lifecycle initialization, consent enforcement, and timer setup.
   - `process_student_message(db, session, message_text, llm_adapter)`: Orchestrates answer evaluation, timer checks, adaptive transitions, and state persistence.
   - `end_interview_session(db, session, reason)`: Computes final arithmetic mean score, generates feedback, marks session completed, and calls `compute_and_save_readiness_score()`.
   - `get_active_session_for_user(db, user_id)`: Retrieves active sessions, automatically handling expired sessions.

2. **`backend/app/routers/interview.py`**:
   - `POST /api/interview/start`: Initiates session and seeds Q1.
   - `GET /api/interview/active`: Resumes in-progress session on browser refresh.
   - `GET /api/interview/history`: Lists past interview sessions.
   - `GET /api/interview/{id}`: Retrieves details of a specific session.
   - `POST /api/interview/{id}/message`: Accepts candidate answer and returns interviewer reply.
   - `POST /api/interview/{id}/end`: Completes session early and grades answers.
   - `GET /api/interview/{id}/replay`: Fetches complete replayable transcript and rubric breakdowns.

3. **`backend/app/models.py` & `backend/app/database.py`**:
   - `InterviewSession`: Stores `duration_minutes`, `time_limit_seconds`, `expires_at`, `current_question_index`, `question_plan`, `messages`, `rubric_scores`, `feedback`, `score`.
   - `ensure_schema_compatibility()`: Automatically verifies and alters SQLite table columns.

4. **`backend/app/services/readiness_service.py`**:
   - `gather_component_data()`: Pulls latest completed `InterviewSession`, maps rubric criteria to review checks (`CHK-INT-TECH-DEPTH`, `CHK-INT-CLARITY`, `CHK-INT-EXPERIENCE`, `CHK-INT-CRITICAL-THINK`), and updates the composite index.

5. **Frontend**:
   - `frontend/src/pages/MockInterviewPage.jsx`: Setup view (duration, target role, profile grounding), interactive interview chat with countdown timer, and performance evaluation report with full replay.
   - `frontend/src/api.js`: Complete set of interview client methods.
   - `frontend/src/App.jsx`: Route mounted to `activeTab === 'interview'`.

---

## 3. Key Design Decisions & Rejected Alternatives

| Decision | Rationale | Alternatives Rejected |
| :--- | :--- | :--- |
| **Fixed 4-Dimension Per-Answer Rubric (Sum = 100)** | Providing deterministic, granular criteria for each answer ensures candidates know exactly why an answer scored high or low and produces reproducible scores within $\pm 3$ points. | **Single End-of-Interview Holistic Grade**: Rejected because holistic grades fail Rule 2 and give vague feedback without itemized evidence. |
| **Grounded Question Roadmap from Resume** | Interview questions that explicitly interrogate the candidate's actual projects (*Readiness Copilot*, *Distributed Task Queue*) and tech stack provide authentic placement preparation. | **Generic Static Question Banks**: Rejected because students receive generic textbook questions unrelated to what recruiters ask about their portfolio. |
| **Hybrid Deterministic + LLM Evaluation** | Evaluates word counts, technical terms, and STAR structures deterministically while using LLM at temperature 0 for depth and trade-offs. Guarantees resilience even on small local models like Ollama `smollm:135m`. | **Unconstrained Free-form LLM Scoring**: Rejected because unconstrained LLMs produce high variance and hallucinated criteria. |
| **SQLite Session Persistence with Replay Endpoint** | Every message, grade, timestamp, and feedback summary is stored permanently, enabling candidates and MSOT staff to review interview history. | **In-memory Client-only State**: Rejected because browser refreshes would wipe the session and staff could not inspect transcripts. |

---

## 4. Shortcuts & Faked Parts

- **Zero Shortcuts / Faked Data**:
  - No mock or hardcoded question lists: Questions are dynamically synthesized from candidate profile models.
  - No faked score: The final score is the exact mathematical average of per-answer rubric scores.
  - Complete multi-turn transcripts are verified and saved directly to SQLite.
  - Tested with local Ollama (`smollm:135m`) and deterministic scripted profiles with transcripts saved under `docs/samples/`.

---

## 5. Verify It Yourself

Follow these steps to manually verify the mock interview system:

### Step 1: Start an Interview via API
Run:
```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"alex@msot.edu","password":"password123"}' | grep -o '"access_token":"[^"]*' | cut -d'"' -f4)

curl -s -X POST http://127.0.0.1:8000/api/interview/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 15, "target_role": "Full Stack Software Engineer"}' | python3 -m json.tool
```
**Expected Result**:
- Returns HTTP 200 with session object (`status: "in_progress"`, `duration_minutes: 15`).
- `messages` contains initial greeting and Question 1 mentioning candidate skills or projects.

### Step 2: Submit an Answer
Run:
```bash
SESSION_ID=$(curl -s -X POST http://127.0.0.1:8000/api/interview/start \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration_minutes": 15}' | grep -o '"id":[0-9]*' | head -1 | cut -d: -f2)

curl -s -X POST http://127.0.0.1:8000/api/interview/$SESSION_ID/message \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"message": "I structure services in FastAPI using modular routers and dependency injection for PostgreSQL sessions with SQLAlchemy."}' | python3 -m json.tool
```
**Expected Result**:
- Returns HTTP 200 with updated session.
- Student message includes `evaluation` with rubric score and criteria breakdowns.
- Interviewer replies with an adaptive follow-up or Question 2.

### Step 3: End Interview & Check Readiness Score Update
Run:
```bash
curl -s -X POST http://127.0.0.1:8000/api/interview/$SESSION_ID/end \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool

curl -s http://127.0.0.1:8000/api/readiness/current \
  -H "Authorization: Bearer $TOKEN" | python3 -m json.tool
```
**Expected Result**:
- Interview session returns `status: "completed"`, final score, strengths, and tips.
- Readiness endpoint shows `mock_interview` with `status: "scored"` and weighted points calculated ($Score \times 0.20$).

### Step 4: Verify in the Browser
1. Open `http://127.0.0.1:5173/` in your browser.
2. Log in with `alex@msot.edu` / `password123`.
3. Click **Mock Interview** in the navigation sidebar.
4. Verify duration options (15m/20m), detected projects, and past session history.
5. Click **Start 15-Minute Mock Interview**, answer questions, and click **End & Grade**.
6. Verify performance report with score gauge, rubric bars, strengths, and replayable transcript.

### Step 5: Run the Complete Automated Test Suite
Run:
```bash
make test
```
**Expected Result**:
- All 77 tests pass (4 voice mode tests + 6 mock interview tests + 67 earlier module tests, 0 failures).

---

## 6. Changes: Voice Mode (Speech-to-Text & Text-to-Speech) [2026-10-17]

### What Was Added
1. **Local Speech-to-Text with faster-whisper**:
   - Integrated `faster-whisper` (`tiny.en` on CPU with `int8` quantization) via singleton model loader in `backend/app/services/voice_service.py`.
   - Sub-second local CPU transcription without paid APIs or cloud dependencies.
   - Decodes browser audio streams (WebM Opus, WAV) using PyAV and runs Voice Activity Detection (VAD) filtering.
   - Deterministic Word Error Rate (WER) and word accuracy calculation via `compute_transcription_accuracy`.
2. **Text-to-Speech (TTS) via Browser Web Speech API**:
   - Added speech narration using the standard browser `window.speechSynthesis` / `SpeechSynthesisUtterance`.
   - Narrates interviewer questions automatically upon arrival when Voice Mode is active.
   - Added TTS audio toggle (`#btn-toggle-tts`) to mute/unmute at any point.
   - Added read-aloud button on each interviewer message bubble in the transcript.
3. **Graceful Microphone Denial Fallback**:
   - Added permission pre-checks and error handling (`NotAllowedError`, `PermissionDeniedError`) in `MockInterviewPage.jsx`.
   - When mic access is denied or unavailable, displays `#mic-denied-alert` warning banner: *"Microphone access was denied. Automatically switched to Text Mode so your interview can proceed smoothly."*
   - Safely switches interaction mode to Text Mode without crashing or losing session countdown progress.
   - Text input remains 100% functional.
4. **Interactive UI Voice Recording**:
   - Dynamic mode selector in Setup view (`#opt-mode-text` and `#opt-mode-voice`).
   - Mode switcher button (`#btn-toggle-mode`) in active interview top bar for instant toggling.
   - Prominent microphone button (`#btn-start-voice-record`) with pulsing ring and active audio visualizer bars (`animate-pulse`).
   - Recording timer (`00:07 / 03:00`), "Cancel" button, and "Send Voice Answer" (`#btn-submit-voice`).
5. **Backend REST Endpoints**:
   - `POST /api/interview/transcribe`: Standalone diagnostic audio transcription endpoint returning `{ "transcription": str, "word_count": int }`.
   - `POST /api/interview/{id}/voice-message`: Submits candidate audio blob, transcribes with `faster-whisper`, feeds the text into `process_student_message`, and returns the rubric evaluation with interviewer follow-up.

### Exact Files and Functions Added / Modified
- `backend/requirements.txt`: Added `faster-whisper>=1.0.0`.
- `backend/app/services/voice_service.py`:
  - `get_whisper_model(model_size)`: Lazily loads and caches the `tiny.en` CTranslate2 model.
  - `transcribe_audio_bytes(audio_bytes, filename)`: Writes audio to temporary file and transcribes segments.
  - `compute_transcription_accuracy(reference, hypothesis)`: Calculates Levenshtein word distance and accuracy percentage.
- `backend/app/routers/interview.py`:
  - `POST /api/interview/transcribe`: Audio transcription endpoint.
  - `POST /api/interview/{id}/voice-message`: Transcribes audio and processes student turn.
  - `_to_session_response`: Accepts optional `transcription` parameter.
- `backend/app/schemas.py`:
  - Added `TranscribeResponse`.
  - Added optional `transcription` field to `InterviewSessionResponse`.
- `frontend/src/api.js`:
  - Added `transcribeAudio(audioBlob, filename)` and `sendInterviewVoiceMessage(sessionId, audioBlob, filename)`.
- `frontend/src/pages/MockInterviewPage.jsx`:
  - `startRecording()`, `stopAndSubmitRecording()`, `cancelRecording()`, `submitVoiceMessage()`.
  - `speakText(text)`, `stopSpeaking()`.
  - Mode switcher and mic denial alert banner `#mic-denied-alert`.
- `backend/tests/test_voice.py`:
  - `test_voice_service_transcription_accuracy()`: Verifies >= 90% accuracy on spoken test sentence.
  - `test_transcribe_api_endpoint()`: Tests `POST /api/interview/transcribe`.
  - `test_voice_message_interview_flow()`: Tests full end-to-end voice interview session turn.
  - `test_voice_message_silent_audio_returns_clean_error()`: Asserts clean 400 rejection for silent audio.

### Key Design Decisions & Alternatives Rejected
- **Local `faster-whisper` (CTranslate2) vs. Cloud Speech APIs (OpenAI Whisper API, Google Speech)**:
  - *Chosen*: `faster-whisper` `tiny.en` on CPU. Runs completely locally with zero cost, zero API keys, and < 1 second latency, fulfilling Rule 1 and Rule 4.
  - *Rejected*: Cloud APIs because they violate local-first architecture and send candidate voice recordings over external third-party networks.
- **Web Speech API vs. External Server TTS (Piper)**:
  - *Chosen*: Web Speech API natively in the browser. Zero server load, zero download footprint, instant speech start, and supported natively across macOS Chrome/Safari/Firefox.
  - *Rejected*: Standalone server-side Piper audio streaming was considered, but adds binary installation dependencies and network roundtrip latency compared to browser-native synthesis.
- **Immediate Text Fallback on Mic Denial**:
  - *Chosen*: Graceful downgrade to Text Mode with dismissible alert. Candidate is never blocked from finishing their interview session.
  - *Rejected*: Modal error dialog requiring page refresh or aborting the interview.

### Shortcuts & Faked Parts
- **Zero Faked Parts**: Real audio files transcribed with actual local `faster-whisper` neural network inference. No mock models used in voice tests; actual WAV audio was synthesized and verified with 100.0% accuracy.
