# AI-Powered Multi-Agent Technical Interview Screening System

## 🎯 Project Overview

A production-grade, multi-agent AI system that automates the first-round technical screening of job candidates. The system parses resumes and job descriptions, matches candidates against role requirements, conducts adaptive AI-driven technical interviews with intelligent question difficulty progression, evaluates answers in real-time, and generates comprehensive scoring reports.

**Important:** This system assists recruiters in shortlisting candidates — it does NOT make hiring decisions. Final hiring decisions remain with human interviewers.

---

## 📋 What This Backend Does (Part 1)

### Admin Flow
1. **Upload Job Description** (PDF) → Agent 2 parses it → cached for all candidates
2. **View Candidate List** → all candidates (Eligible, Disqualified, Interviewed, etc.)

### Candidate Flow
1. **Upload Resume** (PDF) → Agent 1 parses → Agent 3 matches against JD
   - If `requirement_match_score < 30` → **Disqualified** (added to admin list, no interview)
   - If `requirement_match_score >= 30` → **Eligible** (can start interview)
2. **Start Interview** (if eligible) → Agent 4 generates interview plan
3. **Interview Loop** (each turn):
   - Agent 5 asks a question (phrased naturally)
   - Candidate answers
   - Agent 6 evaluates (relevance, technical correctness, logical correctness)
   - Interview Controller decides next action (retry, hint, new question, escalate difficulty, move to next skill, terminate)
   - Repeat until interview complete or terminated
4. **Interview Complete** → all data persisted, candidate status updated

---

## 🏗️ Architecture Overview

### 7 Agents + 1 Deterministic Controller

| Agent | File | Responsibility |
|-------|------|-----------------|
| **Agent 1** | `agent1.py` | Resume Parser → extracts into `StructuredResume` JSON |
| **Agent 2** | `agent2.py` | JD Parser → extracts into `JobDescription` JSON (admin uploads PDF once) |
| **Agent 3** | `agent3.py` | Requirement Matcher → compares resume vs JD, produces match_score & eligibility |
| **Agent 4** | `agent4.py` | Interview Planner → builds 6-step interview plan with relevant skills/topics |
| **Agent 5** | `interview_manager.py` | Interview Manager → **phrases** questions (does NOT decide flow) |
| **Agent 6** | `answer_evaluator.py` | Answer Evaluator → judges relevance / technical / logical correctness |
| **Agent 7** | `agent7_report.py` | Report Generator → aggregates scores and writes final report *(Part 2)* |
| **Controller** | `interview_controller.py` | **Deterministic state machine** that owns all flow logic (retry, hint, difficulty, tier progression, termination) |

### The Easy → Medium → High Tiered Question Engine

**Why this design?** Early testing showed that asking an LLM to track state (retry counts, difficulty progression) purely from conversation history caused it to drift (e.g., re-asking the same question forever). The solution: all flow logic lives in **deterministic Python code** (`InterviewController`); the LLM only phrases decisions already made.

**How it works (per skill/topic in Steps 2-4, and Projects):**

```
EASY TIER (4 questions, no hints):
  ├─ If 2+ correct → advance to MEDIUM
  └─ If <2 correct → ask 1 probe question
       ├─ If correct → continue in MEDIUM
       └─ If wrong   → skill ends, move to next skill

MEDIUM TIER (5 questions max):
  ├─ For each answer:
  │  ├─ Correct              → ask NEW question
  │  ├─ Partial-correct      → ask SIMILAR question (no hint)
  │  └─ Wrong                → ask NEW question
  └─ After 5 questions, count total correct:
       ├─ 4+ correct (5+ earned)   → HIGH tier with budget=5
       ├─ 2-3 correct (earned 2-3) → HIGH tier with budget=correct_count
       └─ 0-1 correct             → skill ends, move to next skill

HIGH TIER (budget: 2, 3, or 5 questions):
  ├─ For each answer:
  │  ├─ Correct              → ask NEW question
  │  ├─ Partial-correct      → **HINT** + ask SIMILAR question
  │  └─ Wrong                → ask NEW question
  └─ After tier budget exhausted → skill ends, move to next skill

STEP 1 (Personal Information) / STEP 6 (Reasoning):
  ├─ Wrong/vague answer on attempt 1 → retry with HINT on attempt 2
  └─ Still wrong on attempt 2        → move on regardless
```

---

## 📂 Project Structure (Part 1)

```
project-root/
├── backend/
│   ├── __init__.py
│   ├── main.py                          # FastAPI app (run this)
│   ├── services/
│   │   ├── __init__.py
│   │   ├── agent1.py                    # Resume Parser
│   │   ├── agent2.py                    # JD Parser
│   │   ├── agent3.py                    # Requirement Matcher
│   │   ├── agent4.py                    # Interview Planner
│   │   ├── interview_controller.py      # Deterministic state machine (Easy→Medium→High)
│   │   ├── interview_manager.py         # Agent 5 (question phrasing)
│   │   ├── answer_evaluator.py          # Agent 6 (answer evaluation)
│   │   ├── agent7_report.py             # Agent 7 (report generation — Part 2)
│   │   ├── candidate_store.py           # File-backed candidate index (candidates_index.json)
│   │   ├── session_store.py             # In-memory interview session storage
│   │   └── pipeline_utils.py            # Wires agents 1-4 together
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py                     # Admin routes (JD upload, candidate list)
│   │   └── candidate.py                 # Candidate routes (resume upload, interview)
│   └── models/
│       ├── __init__.py
│       └── schemas.py                   # FastAPI request/response Pydantic models
├── data/
│   ├── jd.pdf                           # Admin-uploaded JD (via POST /admin/upload-jd)
│   ├── jd.json                          # Parsed & cached JD (Agent 2 output)
│   ├── candidates_index.json            # Registry of all candidates (Disqualified, Eligible, Completed)
│   └── candidates/
│       ├── {candidate_id_1}/
│       │   ├── resume.pdf
│       │   ├── resume.json              # Agent 1 output
│       │   ├── matcher.json             # Agent 3 output
│       │   ├── planner.json             # Agent 4 output
│       │   └── interview_log.json       # Full Q&A log (created on interview complete)
│       └── {candidate_id_2}/
│           └── ... (same structure)
├── .env                                 # GROQ_API_KEY
├── requirements.txt
└── README.md                            # This file

```

---

## 🚀 Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set up environment

Create a `.env` file in the project root:
```
GROQ_API_KEY=your_groq_api_key_here
```

### 3. Run the backend

```bash
python3 -m backend.main
```

Server starts on `http://localhost:8000`.

Check the API docs: `http://localhost:8000/docs`

---

## 📡 API Endpoints (Part 1)

### Health & Info
- `GET /` → API info
- `GET /health` → health check

### Admin Routes

#### Upload Job Description
```
POST /admin/upload-jd
Content-Type: multipart/form-data

Body:
  file: (PDF file)

Response:
{
  "job_title": "Senior Software Engineer",
  "message": "JD parsed successfully: Senior Software Engineer at Acme Corp"
}
```

#### Check JD Status
```
GET /admin/jd-status

Response:
{
  "ready": true
}
```

#### List All Candidates
```
GET /admin/candidates

Response:
[
  {
    "candidate_id": "abc-123",
    "name": "John Doe",
    "status": "Disqualified",
    "requirement_match_score": 25,
    "interview_performance_score": null,
    "combined_score": null,
    "recommendation": "Not Recommended",
    "created_at": "2026-08-21T10:30:00+00:00"
  },
  {
    "candidate_id": "def-456",
    "name": "Jane Smith",
    "status": "Completed",
    "requirement_match_score": 75,
    "interview_performance_score": 82,
    "combined_score": 78.5,
    "recommendation": "Recommended for Human Interview",
    "created_at": "2026-08-21T10:15:00+00:00"
  },
  ...
]
```

### Candidate Routes

#### Upload Resume & Get Screening Result
```
POST /candidates/resume
Content-Type: multipart/form-data

Body:
  file: (PDF file)

Response (if Eligible):
{
  "candidate_id": "xyz-789",
  "name": "Arjun Rathwa",
  "status": "Eligible",
  "requirement_match_score": 72,
  "reason": null
}

Response (if Disqualified):
{
  "candidate_id": "xyz-790",
  "name": "Another Candidate",
  "status": "Disqualified",
  "requirement_match_score": 25,
  "reason": "Missing critical required skills (Python, REST APIs)"
}
```

#### Start Interview
```
POST /candidates/{candidate_id}/interview/start

Response:
{
  "candidate_id": "xyz-789",
  "bot_message": "Hello Arjun, thank you for joining. Let's start with a bit about yourself. Can you briefly introduce yourself?",
  "asked_question": true,
  "interview_completed": false,
  "interview_terminated": false
}
```

#### Submit Answer & Get Next Question
```
POST /candidates/{candidate_id}/interview/answer
Content-Type: application/json

Body:
{
  "answer": "I'm a software engineer with 5 years of experience in Python and Node.js..."
}

Response:
{
  "candidate_id": "xyz-789",
  "bot_message": "Great! Now let's dive into Python basics. Can you explain what a Python generator is and how it differs from a regular function?",
  "asked_question": true,
  "interview_completed": false,
  "interview_terminated": false
}

Response (if interview ends):
{
  "candidate_id": "xyz-789",
  "bot_message": "Thank you for completing the interview. Your detailed responses and technical knowledge were impressive. The hiring team will review your performance and get back to you soon.",
  "asked_question": false,
  "interview_completed": true,
  "interview_terminated": false
}
```

---

## 💾 Data Persistence

All candidate data is stored in JSON files under `data/candidates/`:

### Per-Candidate Directory
```
data/candidates/xyz-789/
├── resume.pdf            # Original upload
├── resume.json           # Parsed (Agent 1)
├── matcher.json          # Match result (Agent 3)
├── planner.json          # Interview plan (Agent 4)
└── interview_log.json    # Full interview transcript (created on complete)
```

### Candidate Registry
```
data/candidates_index.json
[
  {
    "candidate_id": "xyz-789",
    "name": "Arjun Rathwa",
    "status": "Completed",
    "requirement_match_score": 72,
    "interview_performance_score": null,  # Filled in Part 2
    "combined_score": null,               # Filled in Part 2
    "recommendation": null,               # Filled in Part 2
    "created_at": "2026-08-21T10:30:00+00:00",
    "updated_at": "2026-08-21T10:45:00+00:00"
  }
]
```

---

## 🔑 Key Implementation Details

### InterviewController (Easy → Medium → High Engine)

Located in `backend/services/interview_controller.py`. This deterministic state machine:

- **Owns ALL flow decisions:** retries, hints, difficulty progression, tier transitions, skill termination
- **Classifies each answer** as `correct / partial / wrong` based on Agent 6's technical + logical correctness flags
- **Tracks per-skill state:** how many easy/medium/high questions asked, how many correct
- **Generates directives** (action + metadata) that Agent 5 phrases naturally
- **Never calls an LLM** — all logic is plain Python

Example directive:
```python
{
  "action": "ASK_SIMILAR_MEDIUM_QUESTION",
  "step_number": 2,
  "step_name": "Programming Languages",
  "skill_name": "Python",
  "tier": "medium",
  "context_type": "skill",
  "mandatory": True,
  "give_hint": False,
  "terminate": False,
  "issue_warning": False,
}
```

Agent 5 receives this and responds with something like:
> "That's a good start. Let me ask a related question about Python dictionaries..."

### Session Storage (In-Memory)

`backend/services/session_store.py` holds active interview sessions in RAM per candidate:

```python
{
  "controller": InterviewController(...),
  "conversation_history": [
    {"question": "...", "answer": "..."},
    ...
  ],
  "interview_log": [
    {
      "step_number": 1,
      "skill_name": None,
      "tier": None,
      "question": "...",
      "answer": "...",
      "evaluation": {...},
    },
    ...
  ],
  "pending_directive": {...},
  "pending_output": {...},
  "resume": {...},
  "jd": {...},
  "matcher": {...},
  "interview_plan": {...},
}
```

**Note:** This is in-memory only — suitable for a single-process deployment (one `uvicorn` worker). For horizontal scaling (multiple workers), replace with Redis or a database.

### Candidate Store (File-Backed)

`backend/services/candidate_store.py` maintains `data/candidates_index.json` with all candidates + their status.

---

## 🎓 The Six Interview Steps

All interviews follow this fixed structure (enforced by Agent 4 + Controller):

1. **Personal Information** — 2-3 open-ended questions about background, education, motivation
2. **Programming Languages** — Easy → Medium → High tier questions on languages in the JD
3. **Libraries / Frameworks** — Same tiered approach for frameworks (Django, React, etc.)
4. **Tools** — Same tiered approach for tools (Git, Docker, Kubernetes, etc.)
5. **Projects** — Starts with fixed opener ("Please explain your project"), then contextual follow-ups
6. **Reasoning** — Problem-solving, scenario-based, debugging questions with adaptive difficulty

---

## 🛠️ Tech Stack

- **Backend Framework:** FastAPI
- **LLM:** Groq (`llama-3.3-70b-versatile`) via LangChain
- **Structured Output:** Pydantic
- **PDF Parsing:** PyPDFLoader (from LangChain)
- **Session Management:** In-memory dict (Part 1) → Redis/Database (future)
- **Data Storage:** JSON files (Part 1) → Database (future)

---

## 📝 Known Limitations (Part 1)

1. **In-Memory Sessions:** Only works for single-process deployment. Multi-worker deployments will lose session state — requires Redis/database integration.
2. **File-Based Candidate Index:** Not suitable for concurrent writes at scale — use a database for production.
3. **No Agent 7 (Report Generation):** Part 2 will add final report generation with combined scoring.
4. **No Ranking:** Part 2 will add cross-candidate ranking (top 5, top 10, etc.).
5. **No Persistent JD:** JD is parsed once and cached, but if the server restarts, it's lost from memory until re-uploaded.

---

## 📊 Example: Interview Flow (Text Representation)

```
1. Admin uploads JD.pdf → Agent 2 parses → cached in data/jd.json

2. Candidate uploads resume.pdf → Agent 1 parses → Agent 3 matches → score: 72
   → Status: "Eligible" ✅

3. Candidate clicks "Start Interview"
   → Agent 4 builds plan: [Personal Info (2 Qs), Python (Easy 4 + Medium 5 + High 5), ...]
   → Controller starts at Step 1, Personal Info
   → Agent 5 asks: "Hi Arjun, tell me about yourself."
   → Candidate: "I have 5 years of Python experience..."
   → Agent 6 evaluates: relevant=True, tech=True, logic=True → CORRECT
   → Controller: move to next personal Q

4. (repeat until Step 1 complete)

5. Controller: advance to Step 2 (Programming Languages / Python skill)
   → Agent 5 asks first EASY question: "What's the difference between a list and tuple in Python?"
   → Candidate: "Lists are mutable, tuples are not."
   → Agent 6: relevant=True, tech=True, logic=True → CORRECT (1/4 EASY correct)
   → Controller: Easy question #2

6. (Easy questions 2, 3, 4 are asked. Suppose 2/4 are correct total)
   → Controller: easy_correct=2, advance to MEDIUM tier
   → (MEDIUM 5 questions asked and evaluated)
   → Suppose medium_correct=3
   → Controller: 3 correct → HIGH tier budget = 3 questions
   → (HIGH 3 questions asked)
   → Skill complete → move to next skill or step

7. (repeat for all skills until Step 6 complete)

8. Controller: interview_completed=True
   → Agent 5: "Thank you, Arjun! Interview complete."
   → Session ends
   → interview_log.json written
   → Candidate status → "Completed"
   → Admin sees in /candidates list

Part 2 will add:
   → Agent 7 computes combined_score, recommendation
   → Updates candidate record
   → Ranks all completed candidates
```

---

## 🔄 Part 2 Preview


1. **Agent 7 Integration** — final report generation with scores
2. **Candidate Scoring** — `interview_performance_score` computation (weighted by tier difficulty)
3. **Combined Scoring** — 50/50 blend of requirement match + interview performance
4. **Ranking** — rank all candidates by combined score
5. **Admin Dashboard Report Viewer** — view full interview report for each candidate
6. **Candidate Stats** — per-skill breakdowns (easy/medium/high correct/total)

---

## 🧪 Testing the Backend

### Example 1: Upload JD

```bash
curl -X POST http://localhost:8000/admin/upload-jd \
  -F "file=@path/to/jd.pdf"
```

### Example 2: Upload Resume & Check Eligibility

```bash
curl -X POST http://localhost:8000/candidates/resume \
  -F "file=@path/to/resume.pdf"

# Returns candidate_id and status (Eligible/Disqualified)
```

### Example 3: Start Interview

```bash
curl -X POST http://localhost:8000/candidates/{candidate_id}/interview/start
```

### Example 4: Answer a Question

```bash
curl -X POST http://localhost:8000/candidates/{candidate_id}/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "Python is a high-level programming language..."}'
```

### Example 5: List All Candidates

```bash
curl http://localhost:8000/admin/candidates
```

---

## 📧 Support & Feedback

- **Backend issues:** Check `/health` endpoint
- **API docs:** `http://localhost:8000/docs` (Swagger UI)
- **Alternative API docs:** `http://localhost:8000/redoc` (ReDoc)


---

## 🎯 What's Next?

**Part 2 will add:**
- ✅ Agent 7 integration (report generation)
- ✅ Candidate scoring & ranking
- ✅ Final report endpoint
- ✅ Admin report viewer

**Frontend will be built separately** to consume these APIs.

---

**Version 1.0 (Part 1)** — Backend API ready for testing.  
**Date:** August 2026
