# AI-Powered Multi-Agent Technical Interview Screening System

An API-first technical screening backend that turns a job-description PDF and candidate resume PDFs into a structured, adaptive interview, auditable scores, recruiter-ready reports, and candidate rankings.

The system combines specialized LLM agents with deterministic Python control logic. It is designed to assist recruiters with consistent first-round screening; it does **not** make final hiring decisions. Every recommendation must be reviewed by a human interviewer.

> **Current scope:** backend API only. No web, mobile, voice, or recruiter dashboard frontend is included.

## Table of Contents

- [Key Features](#key-features)
- [Tech Stack and Architecture](#tech-stack-and-architecture)
- [Prerequisites and Environment Setup](#prerequisites-and-environment-setup)
- [Installation and Getting Started](#installation-and-getting-started)
- [End-to-End Workflow](#end-to-end-workflow)
- [Project Structure](#project-structure)
- [API Reference](#api-reference)
- [Scoring, Ranking, and Reports](#scoring-ranking-and-reports)
- [Detailed Module Breakdown](#detailed-module-breakdown)
- [Persistence and Runtime Data](#persistence-and-runtime-data)
- [Testing and Verification](#testing-and-verification)
- [Known Limitations](#known-limitations)
- [Future Enhancements and Roadmap](#future-enhancements-and-roadmap)

## Key Features

### Screening and document processing

- Admin uploads one job-description PDF for a role.
- Agent 2 extracts a structured job description from every readable PDF page.
- Candidates upload resume PDFs.
- Agent 1 extracts structured resume data, including contact details, skills, education, experience, projects, certifications, and links.
- Agent 3 compares the resume with the parsed job description and returns matched skills, missing requirements, strengths, weaknesses, eligibility, and a requirement-match score from 0 to 100.
- A deterministic eligibility floor disqualifies candidates whose requirement-match score is below `30.0`, regardless of the LLM eligibility field.

### Adaptive technical interviews

- Agent 4 creates a six-step plan containing only relevant topics and skills.
- A deterministic controller owns all interview flow decisions; the LLM does not track counters or decide when to advance.
- Technical skills use Easy -> Medium -> High progression with fixed question budgets.
- Partial answers receive similar follow-up questions, with hints introduced at the high tier.
- Personal-information and reasoning questions use a one-retry-with-hint pattern.
- The controller tracks per-skill and per-tier question counts and correct answers.
- Offensive language produces a warning; a second offense terminates the interview.
- Agent 5 converts controller directives into natural, professional candidate-facing messages.
- Agent 6 evaluates relevance, technical correctness, logical correctness, confidence, and offensive language.

### Reporting and recruiter analytics

- Agent 7 aggregates the complete interview log into deterministic numeric scores.
- Easy, medium, and high answers have weights `1`, `2`, and `3` respectively.
- Partial-correct answers earn half of the applicable tier weight.
- Final reports contain scores, recommendation labels, qualitative strengths, weaknesses, HR summary, per-skill breakdowns, and per-step summaries.
- Completed candidates can be ranked by combined score.
- Pipeline statistics expose candidate funnel counts, average scores, and recommendation distribution.
- Candidate and report data are inspectable as JSON files under `data/`.

## Tech Stack and Architecture

| Area | Technology | Purpose |
| --- | --- | --- |
| HTTP API | FastAPI `0.104.1` | Async REST endpoints and automatic OpenAPI documentation |
| ASGI server | Uvicorn `0.24.0` | Local application server |
| LLM orchestration | LangChain `0.1.0` and LangChain Core | Prompt construction and structured model pipelines |
| LLM provider | Groq through `langchain-groq` | Resume parsing, JD parsing, matching, planning, interviewing, evaluation, and narrative generation |
| Config | `python-dotenv` | Loads `.env` values into the process environment |
| Structured data | Pydantic `2.5.0` | Agent schemas and API request/response models |
| PDF extraction | `pypdf` and LangChain `PyPDFLoader` | Reads text from multi-page PDF uploads |
| Persistence | JSON files | JD cache, candidate registry, per-candidate artifacts, and reports |
| Active sessions | Thread-locked in-memory dictionary | Holds controller and conversation state between interview requests |
| Testing utilities | `pytest`, `httpx` | Available for adding API and unit tests |

### High-level architecture

```text
Admin uploads JD PDF
        |
        v
 Agent 2: parse_jd -> data/jd.json
        |
        +------------------------------+
                                       |
Candidate uploads resume PDF           |
        |                              |
        v                              |
 Agent 1: parse_resume                 |
        |                              |
        v                              |
 Agent 3: parse_matcher <--------------+
        |
        +--> Disqualified when score < 30
        |
        v
 Agent 4: parse_interview_plan
        |
        v
 InterviewController (deterministic state machine)
        |                         |
        v                         v
 Agent 5: phrase question   Agent 6: evaluate answer
        |                         |
        +----------- repeat ------+
                    |
                    v
          interview_log.json
                    |
                    v
 Agent 7: deterministic scores + LLM narrative
                    |
                    v
          final_report.json
                    |
                    +--> rankings and statistics
```

### Agent responsibilities

| Component | Implementation | Responsibility |
| --- | --- | --- |
| Agent 1 | `backend/services/agent1.py` | Parse a resume PDF into `StructuredResume`. |
| Agent 2 | `backend/services/agent2.py` | Parse the shared JD PDF into `JobDescription`. |
| Agent 3 | `backend/services/agent3.py` | Compare resume and JD; calculate match and eligibility. |
| Agent 4 | `backend/services/agent4.py` | Select relevant interview topics and skills for six fixed steps. |
| Agent 5 | `backend/services/interview_manager.py` | Phrase an already-decided controller directive. |
| Agent 6 | `backend/services/answer_evaluator.py` | Evaluate each candidate answer. |
| Agent 7 | `backend/services/agent7_report.py` | Compute scores and generate qualitative report narrative. |
| Controller | `backend/services/interview_controller.py` | Deterministically control retries, tiers, hints, progression, completion, and termination. |

The LLM is intentionally excluded from state transitions and numeric scoring. This makes interview flow and ranking behavior reproducible and auditable even though the language generation and evaluations are model-assisted.

## Prerequisites and Environment Setup

### Required tools

- Python 3.8 or newer. Python 3.10+ is recommended for current FastAPI and typing behavior.
- `pip`.
- A Groq API key.
- Readable, text-based PDF files for job descriptions and resumes. Scanned image-only PDFs require OCR before upload.
- `curl` for command-line examples, or a browser for Swagger UI.

### Environment variables

Create a `.env` file in the repository root:

```dotenv
GROQ_API_KEY=your_actual_groq_api_key_here
PORT=8000
```

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `GROQ_API_KEY` | Yes for LLM-backed operations | None | API credential used by `ChatGroq`. |
| `PORT` | No | `8000` | Port used by `python3 -m backend.main`. |

Get a Groq key from [console.groq.com](https://console.groq.com/).

The older project notes refer to `.env.example`, but that template is not present in this checkout. Create `.env` manually as shown above. Never commit the real key.

The source currently instantiates `ChatGroq(model="openai/gpt-oss-120b")` in the agent modules. Older notes mention `llama-3.3-70b-versatile`; that name is not the model configured by the current implementation.

## Installation and Getting Started

### 1. Enter the project directory

```bash
cd interview-screening-backend
```

Run the following commands from the repository root because the application uses relative paths such as `data/jd.json` and `data/candidates/`.

### 2. Create and activate a virtual environment

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure the environment

```bash
touch .env
```

Add the variables described in [Environment variables](#environment-variables).

### 5. Start the API

```bash
python3 -m backend.main
```

The server listens on `http://localhost:8000` by default. To use another port:

```bash
PORT=8001 python3 -m backend.main
```

### 6. Verify the service

```bash
curl http://localhost:8000/health
```

Expected response:

```json
{"status":"healthy"}
```

Interactive documentation is available at:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

### 7. Run the complete screening flow

#### Upload a job description

```bash
curl -X POST http://localhost:8000/admin/upload-jd \
  -F "file=@/absolute/path/to/job-description.pdf"
```

Then verify that the shared JD cache exists:

```bash
curl http://localhost:8000/admin/jd-status
```

Expected shape:

```json
{"ready":true}
```

#### Upload a candidate resume

```bash
curl -X POST http://localhost:8000/candidates/resume \
  -F "file=@/absolute/path/to/resume.pdf"
```

The response includes a generated `candidate_id`, status, requirement-match score, and, when disqualified, a reason. Save the returned ID for the next calls:

```json
{
  "candidate_id": "abc-123",
  "status": "Eligible",
  "requirement_match_score": 72.0,
  "reason": null
}
```

Only candidates with status `Eligible` can start an interview.

#### Start an interview

```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/start
```

The response contains the first candidate-facing message:

```json
{
  "candidate_id": "abc-123",
  "bot_message": "Please introduce yourself and describe your background.",
  "asked_question": true,
  "interview_completed": false,
  "interview_terminated": false
}
```

#### Submit answers

Repeat this request with the answer to the latest `bot_message` until the response indicates completion or termination:

```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"answer":"I have five years of Python experience building REST APIs and data pipelines."}'
```

The API returns the next question, or a final message with `asked_question: false`.

#### Generate and retrieve the report

After the interview is complete:

```bash
curl -X POST http://localhost:8000/report/abc-123/generate
curl http://localhost:8000/report/abc-123
```

#### Inspect rankings and statistics

```bash
curl "http://localhost:8000/report/ranking/by-score?limit=10"
curl http://localhost:8000/report/statistics/overview
curl http://localhost:8000/admin/candidates
```

### One-command shell walkthrough

With `jq` installed, the core sequence can be scripted as follows. The answer call must be repeated for every question returned by the interview endpoint; the example shows the shape of one turn.

```bash
curl http://localhost:8000/health

curl -X POST http://localhost:8000/admin/upload-jd \
  -F "file=@/path/to/job-description.pdf"

CANDIDATE_ID=$(curl -s -X POST http://localhost:8000/candidates/resume \
  -F "file=@/path/to/resume.pdf" | jq -r '.candidate_id')

curl -X POST "http://localhost:8000/candidates/${CANDIDATE_ID}/interview/start"

curl -X POST "http://localhost:8000/candidates/${CANDIDATE_ID}/interview/answer" \
  -H "Content-Type: application/json" \
  -d '{"answer":"My answer to the current question."}'

# After the interview reports completion:
curl -X POST "http://localhost:8000/report/${CANDIDATE_ID}/generate"
curl "http://localhost:8000/report/${CANDIDATE_ID}"
curl "http://localhost:8000/report/ranking/by-score?limit=5"
curl http://localhost:8000/report/statistics/overview
```

## End-to-End Workflow

1. **Admin setup:** `POST /admin/upload-jd` stores the original PDF and the structured result from Agent 2 in `data/jd.json`.
2. **Candidate screening:** `POST /candidates/resume` stores the resume, runs Agent 1, loads the cached JD, runs Agent 3, and creates the candidate registry entry.
3. **Eligibility gate:** scores below `30.0` become `Disqualified`; eligible candidates receive a six-step plan from Agent 4 and become `Eligible`.
4. **Interview start:** `POST /candidates/{candidate_id}/interview/start` creates an in-memory session and asks the first question through Agent 5.
5. **Interview loop:** each answer is evaluated by Agent 6, appended to the in-memory log, passed to the deterministic controller, and converted into the next message by Agent 5.
6. **Interview completion:** the answer endpoint writes `interview_log.json` and changes the candidate status to `Completed`. A second offensive-language event causes termination through the controller.
7. **Report generation:** `POST /report/{candidate_id}/generate` loads all candidate artifacts, computes deterministic scores, asks Agent 7 for narrative fields, saves `final_report.json`, and updates the candidate registry.
8. **Recruiter review:** report retrieval, candidate listing, ranking, and statistics endpoints expose the results for a future frontend or direct API consumer.

## Project Structure

```text
interview-screening-backend/
├── backend/
│   ├── __init__.py
│   ├── main.py                         # FastAPI application entry point
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py                  # Pydantic API and report models
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── admin.py                    # JD and candidate administration
│   │   ├── candidate.py                # Resume and interview workflow
│   │   └── report.py                   # Reports, ranking, statistics
│   └── services/
│       ├── __init__.py
│       ├── agent1.py                   # Resume parser
│       ├── agent2.py                   # Job-description parser
│       ├── agent3.py                   # Requirement matcher
│       ├── agent4.py                   # Interview planner
│       ├── agent7_report.py            # Score aggregation and report narrative
│       ├── answer_evaluator.py         # Agent 6 answer evaluation
│       ├── candidate_store.py           # JSON candidate registry
│       ├── interview_controller.py     # Deterministic interview state machine
│       ├── interview_manager.py        # Agent 5 question phrasing
│       ├── pipeline_utils.py           # Agent 1-4 pipeline wiring
│       └── session_store.py            # In-memory active sessions
├── data/
│   ├── jd.pdf                          # Uploaded job description
│   ├── jd.json                         # Structured, cached job description
│   ├── candidates_index.json           # Candidate registry
│   └── candidates/
│       └── {candidate_id}/
│           ├── resume.pdf
│           ├── resume.json
│           ├── matcher.json
│           ├── planner.json
│           ├── interview_log.json
│           └── final_report.json
├── requirements.txt
├── README.md
├── DOWNLOAD_AND_RUN.md
├── QUICKSTART.md
├── PART1_SUMMARY.md
├── PART2_COMPLETE.md
├── PART2_SCORING_AND_RANKING.md
├── PROJECT_COMPLETE.md
└── README1.md
```

`data/` is runtime state. The application creates missing directories and files as requests arrive. Existing sample data may already be present in a checkout and should be treated as local runtime state, not as a required starting dataset.

## API Reference

All file upload endpoints require `multipart/form-data`. All JSON request bodies use `application/json`.

### Health and metadata

#### `GET /`

Returns basic application name, version, and top-level route prefixes.

#### `GET /health`

Returns:

```json
{"status":"healthy"}
```

### Admin endpoints

#### `POST /admin/upload-jd`

Uploads a PDF job description, parses it with Agent 2, and writes `data/jd.pdf` and `data/jd.json`. The server rejects non-PDF or empty files.

Example:

```bash
curl -X POST http://localhost:8000/admin/upload-jd \
  -F "file=@job-description.pdf"
```

Response shape:

```json
{
  "job_title": "Senior Software Engineer",
  "message": "JD parsed successfully: Senior Software Engineer at Example Corp"
}
```

#### `GET /admin/jd-status`

Checks whether `data/jd.json` exists:

```json
{"ready":true}
```

#### `GET /admin/candidates`

Returns candidates sorted by creation time, newest first. Each item can include:

```json
{
  "candidate_id": "abc-123",
  "name": "Jane Smith",
  "status": "Completed",
  "requirement_match_score": 75.0,
  "interview_performance_score": 82.0,
  "combined_score": 78.5,
  "recommendation": "Recommended for Human Interview",
  "created_at": "2026-08-21T10:30:00+00:00"
}
```

Possible workflow statuses include `Screening`, `Disqualified`, `Eligible`, `Interviewing`, and `Completed`.

### Candidate endpoints

#### `POST /candidates/resume`

Uploads a resume PDF. The endpoint stores the upload, runs Agents 1, 3, and, for eligible candidates, Agent 4. A candidate below the `30.0` match-score floor is immediately disqualified.

Example:

```bash
curl -X POST http://localhost:8000/candidates/resume \
  -F "file=@resume.pdf"
```

Eligible response:

```json
{
  "candidate_id": "abc-123",
  "status": "Eligible",
  "requirement_match_score": 72.0,
  "reason": null
}
```

Disqualified response:

```json
{
  "candidate_id": "def-456",
  "status": "Disqualified",
  "requirement_match_score": 25.0,
  "reason": "Missing critical required skills"
}
```

The route internally extracts the candidate name and stores it in the registry. The current `ResumeUploadResponse` schema exposes the fields above; older examples show a `name` field as well, but it is not declared in the current response model.

#### `POST /candidates/{candidate_id}/interview/start`

Starts an interview for an existing candidate whose status is `Eligible`. It loads the persisted resume, match, plan, and JD artifacts, creates an in-memory session, and returns the first Agent 5 message.

```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/start
```

Response:

```json
{
  "candidate_id": "abc-123",
  "bot_message": "Please explain your background and experience.",
  "asked_question": true,
  "interview_completed": false,
  "interview_terminated": false
}
```

#### `POST /candidates/{candidate_id}/interview/answer`

Submits one answer for the current active session. Empty answers are rejected. Agent 6 evaluates the answer, the controller chooses the next action, and Agent 5 generates the next message.

```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"answer":"A Python generator yields values lazily and avoids materializing the entire sequence in memory."}'
```

When the interview ends, the response has `asked_question: false`. The endpoint writes `interview_log.json` and updates the status to `Completed` for both normal completion and the current termination path.

### Report endpoints

#### `POST /report/{candidate_id}/generate`

Generates a report only for a candidate with status `Completed`. It loads `resume.json`, `matcher.json`, `planner.json`, `interview_log.json`, and `data/jd.json`; computes scores; generates narrative fields; writes `final_report.json`; and updates the registry.

#### `GET /report/{candidate_id}`

Returns the previously generated `final_report.json`. It returns `404` until the generate endpoint has succeeded.

#### `GET /report/ranking/by-score?limit=10`

Returns completed candidates with generated combined scores, sorted by descending `combined_score` and limited to `limit` entries.

Response shape:

```json
{
  "total_completed": 25,
  "total_ranked": 10,
  "rankings": [
    {
      "candidate_id": "abc-123",
      "name": "Jane Smith",
      "status": "Completed",
      "requirement_match_score": 75.0,
      "interview_performance_score": 82.0,
      "combined_score": 78.5,
      "recommendation": "Recommended for Human Interview",
      "created_at": "2026-08-21T10:30:00+00:00"
    }
  ]
}
```

#### `GET /report/statistics/overview`

Returns the funnel and score overview:

```json
{
  "total_candidates": 50,
  "disqualified_count": 15,
  "eligible_not_interviewed_count": 8,
  "interviewing_count": 0,
  "completed_count": 27,
  "average_requirement_match_score": 68.3,
  "average_interview_performance_score": 75.2,
  "average_combined_score": 71.8,
  "recommendation_breakdown": {
    "Recommended for Human Interview": 12,
    "Borderline - Consider for Human Interview": 10,
    "Not Recommended": 5
  }
}
```

## Interview Engine

Agent 4 creates exactly six ordered steps:

1. **Personal Information:** background, education, and motivation topics.
2. **Programming Languages:** relevant languages from the resume and JD.
3. **Libraries / Frameworks:** relevant frameworks and libraries.
4. **Tools:** relevant tools such as Git, Docker, or Kubernetes.
5. **Projects:** a fixed opening question followed by project-focused tiering.
6. **Reasoning:** problem-solving, debugging, and scenario topics.

### Easy -> Medium -> High rules

For each programming-language, library/framework, tool, and post-opening project tracker:

```text
EASY: ask exactly 4 questions, without hints
  2 or more correct -> MEDIUM
  fewer than 2 correct -> one medium probe
    probe correct -> MEDIUM, counting the probe as question 1
    probe wrong -> end this skill and continue to the next skill

MEDIUM: ask up to 5 questions
  correct -> new question
  partial -> similar question, without a hint
  wrong -> new question
  after the budget:
    4 or more correct -> HIGH budget 5
    2 or 3 correct -> HIGH budget equal to correct count
    0 or 1 correct -> end this skill

HIGH: use the budget selected above
  correct -> new question
  partial -> hint plus a similar question
  wrong -> new question
  after the budget -> end this skill
```

Personal-information and reasoning steps do not use the tier tracker. A wrong or irrelevant first answer receives one retry with a hint; the interview then moves on regardless of the second result.

An answer is classified by `InterviewController.classify` as:

- `correct`: relevant, technically correct, and logically correct.
- `partial`: relevant, with exactly one of technical or logical correctness true.
- `wrong`: irrelevant, or neither technical nor logical correctness is true.

Offensive language increments a warning counter. The second offense returns a `TERMINATE` directive for the whole interview.

## Scoring, Ranking, and Reports

### Interview performance score

Agent 7 computes numeric results in Python from the stored Agent 6 evaluations:

| Tier | Weight per question |
| --- | ---: |
| Easy | 1 |
| Medium | 2 |
| High | 3 |

- Correct answers earn the full tier weight.
- Partial answers earn `50%` of the tier weight.
- Wrong answers earn `0`.

```text
interview_performance_score = (weighted_earned / weighted_total) * 100
```

If no tiered skill questions contribute to `weighted_total`, the implementation falls back to the average confidence score.

### Combined score

```text
combined_score = (requirement_match_score + interview_performance_score) / 2
```

Example:

```text
Requirement match:       75.0
Interview performance:   82.0
Combined score:          (75.0 + 82.0) / 2 = 78.5
```

### Recommendation labels

```text
combined_score >= 70 -> Recommended for Human Interview
combined_score >= 50 -> Borderline - Consider for Human Interview
combined_score <  50 -> Not Recommended
```

The report service also supports a terminated-interview override that returns `Not Recommended`. The current report route calls Agent 7 with `was_terminated=False` and the candidate route stores terminated interviews as `Completed`; termination-aware report persistence is therefore a follow-up item in the roadmap.

### Report contents

The generated report contains:

- Candidate name and interview status.
- Optional termination reason.
- Total questions, correct, partial, and wrong counts.
- Technical accuracy percentage.
- Logical accuracy percentage.
- Average confidence score.
- Interview performance, requirement-match, and combined scores.
- Deterministic recommendation label.
- LLM-written recommendation reasoning, strengths, weaknesses, and HR summary.
- Per-skill counts for easy, medium, and high tiers.
- Per-step question counts and average confidence.

All report numbers and recommendation labels are system-computed. The LLM receives the computed aggregate and is instructed to write narrative text without changing numeric results.

## Detailed Module Breakdown

### Application and models

- **`backend/main.py`** creates the FastAPI application, loads dotenv, registers admin, candidate, and report routers, exposes `/` and `/health`, enables permissive CORS for future frontend development, and starts Uvicorn using `PORT`.
- **`backend/models/schemas.py`** defines Pydantic models for JD upload/status, resume upload, answer requests, interview turns, candidate list items, final reports, skill breakdowns, step summaries, ranking responses, and statistics.

### Routes

- **`backend/routes/admin.py`** validates JD PDF uploads, invokes the JD pipeline, reports readiness, and maps the candidate registry into admin-facing candidate list records.
- **`backend/routes/candidate.py`** creates candidate IDs, saves resume uploads, runs screening, sets candidate status, starts interview sessions, evaluates answers, writes interview logs, and returns candidate-facing messages.
- **`backend/routes/report.py`** loads completed-candidate artifacts, invokes Agent 7, saves and retrieves final reports, ranks scored completed candidates, and calculates pipeline statistics.

### Agents and interview services

- **`backend/services/agent1.py`** uses `PyPDFLoader` to concatenate all resume pages and asks the Groq model for a `StructuredResume` containing name, contact information, skills, education, experience, projects, certifications, and links.
- **`backend/services/agent2.py`** reads all JD PDF pages and returns a `JobDescription` with role metadata, required and preferred skills, responsibilities, and eligibility criteria.
- **`backend/services/agent3.py`** compares structured resume and JD JSON. It returns a `MatchResult` and enforces the `30.0` eligibility floor in Python after the LLM response.
- **`backend/services/agent4.py`** selects relevant skills and topics, marks mandatory skills, and returns the fixed six-step `InterviewPlan`. It does not generate questions or control budgets.
- **`backend/services/interview_controller.py`** contains `SkillTracker`, classification logic, counters, tier transitions, retries, hint directives, warning handling, and completion/termination state. It never calls an LLM.
- **`backend/services/interview_manager.py`** implements Agent 5. It receives an authoritative directive and produces one professional message without exposing internal scores, tier names, or budgets.
- **`backend/services/answer_evaluator.py`** implements Agent 6. It returns structured relevance, technical correctness, logical correctness, offensive-language detection, confidence, quality, and summary fields.
- **`backend/services/agent7_report.py`** implements Agent 7. `aggregate_scores` computes all numeric report fields; the LLM only generates `strengths`, `weaknesses`, `recommendation_reasoning`, and `hr_summary`.

### Storage and pipeline helpers

- **`backend/services/pipeline_utils.py`** defines relative data paths, creates candidate directories, saves uploaded resumes, parses and caches the JD, and wires Agents 1, 3, and 4 for each candidate.
- **`backend/services/candidate_store.py`** maintains `data/candidates_index.json` using a thread lock. It exposes create, update, get, and list operations so the file store can later be replaced by a database without changing route call sites.
- **`backend/services/session_store.py`** holds active `InterviewController` instances, conversation history, pending directives, pending outputs, and interview logs in a thread-locked process-local dictionary.

## Persistence and Runtime Data

### Shared JD files

```text
data/jd.pdf    # original admin upload
data/jd.json   # Agent 2 structured output; readiness is based on this file
```

The current implementation writes and reuses `data/jd.json` across process restarts. Older Part 1 notes describe the JD cache as non-persistent, but that description no longer matches the implementation.

### Candidate files

```text
data/candidates/{candidate_id}/
├── resume.pdf           # original upload
├── resume.json          # Agent 1 output
├── matcher.json         # Agent 3 output
├── planner.json         # Agent 4 output, or an ineligible plan marker
├── interview_log.json   # Q&A and Agent 6 evaluations after interview end
└── final_report.json    # Agent 7 output after report generation
```

### Candidate registry

`data/candidates_index.json` is implemented as a JSON object keyed by candidate ID. Each value can contain:

```json
{
  "candidate_id": "abc-123",
  "name": "Jane Smith",
  "status": "Completed",
  "requirement_match_score": 75.0,
  "interview_performance_score": 82.0,
  "combined_score": 78.5,
  "recommendation": "Recommended for Human Interview",
  "created_at": "2026-08-21T10:30:00+00:00",
  "updated_at": "2026-08-21T11:45:00+00:00"
}
```

The store uses a process-local thread lock for writes, which helps within one process but does not provide database-grade multi-process or distributed concurrency guarantees.

## Testing and Verification

The dependency file includes `pytest` and `httpx`, but this repository currently does not contain a test suite. The minimum manual verification is:

```bash
curl http://localhost:8000/health
curl http://localhost:8000/admin/jd-status
```

For a full integration check, upload a text-based JD PDF, upload a text-based resume PDF, complete the interview by repeatedly submitting answers, generate the report, then inspect ranking and statistics endpoints.

The FastAPI-generated Swagger UI at `/docs` is useful for checking request schemas and exercising every route interactively.

## Known Limitations

1. **Active sessions are in memory.** A restart loses active interviews. Multiple Uvicorn workers or horizontally scaled instances can route requests to different processes and lose session state. Use Redis or a database for shared session state.
2. **Candidate persistence is file-based.** A single JSON registry is not appropriate for high-concurrency production traffic. Replace it with a transactional database.
3. **Relative paths depend on the working directory.** Start the application from the repository root or convert storage paths to configuration-based absolute paths.
4. **PDF extraction requires text.** Scanned image PDFs without OCR are rejected because no extractable text is found.
5. **LLM availability is required for the core workflow.** Resume parsing, JD parsing, matching, planning, interviewing, evaluation, and narrative generation all call Groq.
6. **CORS is intentionally permissive for development.** The application allows all origins, methods, and headers and enables credentials. Restrict this configuration before exposing the API publicly.
7. **No authentication or authorization is implemented.** Admin and candidate routes are currently open to any caller who can reach the service.
8. **Report routes do not currently declare their response models.** Pydantic report schemas exist, but the report endpoints return dictionaries directly.
9. **Termination metadata is not fully propagated.** The session store has termination fields, but the candidate route ends terminated sessions as `Completed` and the report route currently passes `was_terminated=False`.
10. **Ranking tie-breaking is score-only in code.** Project notes describe creation-time tie-breaking, but the current route sorts only by descending combined score.
11. **The root metadata response omits report and documentation URLs.** The routes themselves remain available at the paths documented above.
12. **This is a screening aid, not an autonomous hiring system.** Model outputs, extracted documents, and recommendations require human review for correctness, fairness, and compliance.

## Future Enhancements and Roadmap

### Reliability and scale

- Replace `session_store.py` with Redis or a database-backed session service.
- Replace `candidate_store.py` and JSON artifacts with a transactional database while preserving the current service interfaces.
- Add multiple-worker and restart-safe integration tests.
- Add structured logging, request IDs, retries, timeouts, and observability around model calls.
- Make storage paths configurable rather than relative to the current directory.

### Security and operations

- Add authentication and role-based authorization for admin and candidate operations.
- Restrict CORS to approved frontend origins.
- Add upload size limits, MIME/content validation, malware scanning, and retention policies.
- Keep secrets out of source control and provide a maintained `.env.example` template.
- Add Docker, deployment configuration, health/readiness probes, and cloud storage options.

### Product capabilities

- Build a recruiter/admin frontend for candidate lists, reports, rankings, and statistics.
- Build a candidate-facing interview frontend that consumes the existing turn API.
- Add report export to PDF or CSV.
- Add role/version management so multiple job descriptions can be screened concurrently.
- Add configurable eligibility floors, tier budgets, recommendation thresholds, and weighting policies.
- Add resume/JD OCR support for scanned documents.
- Add voice input/output and accessibility-focused interview controls.

### Correctness and governance

- Persist and report termination status and termination reason accurately.
- Implement the documented creation-time tie-break for equal combined scores.
- Add unit tests for controller transitions, answer classification, score aggregation, recommendation thresholds, and ranking.
- Add API contract tests for all success and error responses.
- Add audit trails for prompt/model versions, score calculations, and report regeneration.
- Add human review workflows and fairness monitoring before using recommendations in production hiring decisions.

## License and Contribution

No license or contribution policy is defined in the current repository. Add the project license, issue workflow, and contribution guidelines before distributing the backend outside its intended evaluation environment.
