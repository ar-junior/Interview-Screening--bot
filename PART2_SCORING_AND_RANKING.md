# 📊 Part 2: Scoring, Ranking & Final Reports

**Status:** ✅ COMPLETE & INTEGRATED WITH PART 1

---

## 🎯 What's New in Part 2?

Part 2 adds the final layer to the screening system:

✅ **Final Scoring** — interview_performance_score calculation
✅ **Combined Score** — blend of requirement_match + interview_performance
✅ **Candidate Ranking** — top N candidates by combined_score
✅ **Report Generation** — Agent 7 integration with full report
✅ **Statistics & Analytics** — overall candidate pipeline insights
✅ **Report API Endpoints** — retrieve reports, rankings, statistics

---

## 📐 Scoring Formula

### Interview Performance Score
```
For each skill/topic interviewed:
  - Easy tier: weight=1, earned based on correct answers
  - Medium tier: weight=2, earned based on correct answers
  - High tier: weight=3, earned based on correct answers

Partial-correct answers earn 50% weight

interview_performance_score = (weighted_earned / weighted_total) * 100
```

### Combined Score (Final)
```
combined_score = (requirement_match_score + interview_performance_score) / 2
```

**Example:**
```
Requirement Match Score: 75
Interview Performance Score: 82
Combined Score: (75 + 82) / 2 = 78.5
```

### Recommendation (Deterministic)
```
combined_score >= 70  → "Recommended for Human Interview" ✅
combined_score 50-69  → "Borderline - Consider for Human Interview" ⚠️
combined_score < 50   → "Not Recommended" ❌

If interview terminated early → "Not Recommended" ❌
```

---

## 📡 New API Endpoints (Part 2)

### Generate Report
```
POST /report/{candidate_id}/generate

Response:
{
  "candidate_name": "John Doe",
  "interview_status": "Completed",
  "total_questions_asked": 28,
  "total_correct": 18,
  "total_partial": 4,
  "total_wrong": 6,
  "technical_accuracy_score": 71.4,
  "logical_accuracy_score": 78.6,
  "average_confidence_score": 76.2,
  "interview_performance_score": 82.0,
  "requirement_match_score": 75.0,
  "combined_score": 78.5,
  "overall_recommendation": "Recommended for Human Interview",
  "recommendation_reasoning": "Strong technical foundation with good problem-solving skills...",
  "strengths": [
    "Excellent Python knowledge across all difficulty levels",
    "Good understanding of Django and REST APIs",
    "Clear and structured approach to problem-solving"
  ],
  "weaknesses": [
    "Limited experience with Docker and containerization",
    "Some gaps in advanced Python concepts like decorators",
    "Could improve database optimization knowledge"
  ],
  "hr_summary": "John demonstrated solid technical expertise with a requirement match of 75%...",
  "per_skill_breakdown": [
    {
      "skill_name": "Python",
      "mandatory": true,
      "context_type": "skill",
      "tier_reached": "high",
      "easy_correct": 4,
      "easy_total": 4,
      "medium_correct": 4,
      "medium_total": 5,
      "high_correct": 3,
      "high_total": 3,
      "skill_passed": true
    },
    ...
  ],
  "per_step_summary": [
    {
      "step_number": 1,
      "step_name": "Personal Information",
      "questions_asked": 3,
      "average_confidence": 85.0
    },
    ...
  ]
}
```

### Get Report
```
GET /report/{candidate_id}

Returns: Same structure as above (if already generated)
```

### Get Candidate Rankings
```
GET /report/ranking/by-score?limit=10

Response:
{
  "total_completed": 25,
  "total_ranked": 10,
  "rankings": [
    {
      "candidate_id": "abc-123",
      "name": "John Doe",
      "status": "Completed",
      "requirement_match_score": 75.0,
      "interview_performance_score": 82.0,
      "combined_score": 78.5,
      "recommendation": "Recommended for Human Interview",
      "created_at": "2026-08-21T10:30:00+00:00"
    },
    {
      "candidate_id": "def-456",
      "name": "Jane Smith",
      "status": "Completed",
      "requirement_match_score": 72.0,
      "interview_performance_score": 80.0,
      "combined_score": 76.0,
      "recommendation": "Recommended for Human Interview",
      "created_at": "2026-08-21T10:15:00+00:00"
    },
    ...
  ]
}
```

### Get Statistics Overview
```
GET /report/statistics/overview

Response:
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

---

## 🔄 Complete Interview Flow (Parts 1 + 2)

```
┌─ ADMIN SIDE ─────────────────────────────────────────┐
│                                                       │
│  1. Upload JD (PDF)                                   │
│     ↓                                                 │
│  POST /admin/upload-jd                               │
│     ↓                                                 │
│  Agent 2 parses JD → data/jd.json                     │
│     ↓                                                 │
│  GET /admin/jd-status → ready: true                   │
│                                                       │
└─────────────────────────────────────────────────────┘

┌─ CANDIDATE SIDE ──────────────────────────────────────┐
│                                                       │
│  1. Upload Resume (PDF)                               │
│     ↓                                                 │
│  POST /candidates/resume                             │
│     ↓                                                 │
│  Agent 1 parse → resume.json                          │
│  Agent 3 match → matcher.json (eligible/disqualified) │
│     ↓                                                 │
│  If Disqualified:                                     │
│    - Status = "Disqualified"                          │
│    - Added to admin list                              │
│    - Interview = STOP                                 │
│     ↓                                                 │
│  If Eligible:                                         │
│    - Status = "Eligible"                              │
│    - Can start interview                              │
│     ↓                                                 │
│  2. Start Interview                                   │
│     ↓                                                 │
│  POST /candidates/{id}/interview/start                │
│     ↓                                                 │
│  Agent 4 plans interview → planner.json               │
│  Controller starts, Agent 5 asks Q1                   │
│     ↓                                                 │
│  3. Answer Question Loop                              │
│     ↓                                                 │
│  POST /candidates/{id}/interview/answer               │
│     ↓                                                 │
│  Agent 6 evaluates answer                             │
│  Controller decides next action                       │
│  Agent 5 phrases next question                        │
│  (Repeat for all 6 steps)                             │
│     ↓                                                 │
│  4. Interview Complete                                │
│     ↓                                                 │
│  interview_log.json saved                             │
│  Status = "Completed"                                 │
│                                                       │
└─────────────────────────────────────────────────────┘

┌─ PART 2: REPORTING & RANKING ──────────────────────┐
│                                                      │
│  5. Generate Report (Agent 7)                        │
│     ↓                                                │
│  POST /report/{id}/generate                          │
│     ↓                                                │
│  Agent 7 aggregates:                                 │
│    - All evaluations from interview_log              │
│    - Computes scores (deterministic Python)          │
│    - LLM writes narrative (strengths/weaknesses)     │
│     ↓                                                │
│  final_report.json saved                             │
│  Candidate record updated with:                      │
│    - interview_performance_score                     │
│    - combined_score                                  │
│    - overall_recommendation                          │
│     ↓                                                │
│  6. View Report                                      │
│     ↓                                                │
│  GET /report/{id}                                    │
│     ↓                                                │
│  Returns full report with all scores                 │
│     ↓                                                │
│  7. View Rankings (Admin)                            │
│     ↓                                                │
│  GET /report/ranking/by-score?limit=10               │
│     ↓                                                │
│  Returns top N candidates sorted by combined_score   │
│     ↓                                                │
│  8. View Statistics (Admin)                          │
│     ↓                                                │
│  GET /report/statistics/overview                     │
│     ↓                                                │
│  Pipeline metrics: total, disqualified, completed,   │
│  average scores, recommendation breakdown            │
│                                                      │
└──────────────────────────────────────────────────────┘
```

---

## 📊 Report Structure (Detailed)

### Scores Section
```json
{
  "total_questions_asked": 28,
  "total_correct": 18,
  "total_partial": 4,
  "total_wrong": 6,
  
  "technical_accuracy_score": 71.4,        // % of answers with tech correctness
  "logical_accuracy_score": 78.6,          // % of answers with logic correctness
  "average_confidence_score": 76.2,        // Avg confidence across all answers
  
  "interview_performance_score": 82.0,     // Weighted by tier difficulty
  "requirement_match_score": 75.0,         // From Agent 3 (resume match)
  "combined_score": 78.5                   // (requirement + interview) / 2
}
```

### Per-Skill Breakdown
```json
[
  {
    "skill_name": "Python",
    "mandatory": true,
    "context_type": "skill",
    "tier_reached": "high",                // How far did they progress
    "easy_correct": 4,
    "easy_total": 4,
    "medium_correct": 4,
    "medium_total": 5,
    "high_correct": 3,
    "high_total": 3,
    "skill_passed": true                   // All tiers: 2+ medium or 1+ high
  },
  ...
]
```

### Narrative Section (LLM-Generated)
```json
{
  "strengths": [
    "Excellent Python knowledge across all difficulty levels",
    "Clear problem-solving approach",
    "Strong grasp of REST APIs"
  ],
  "weaknesses": [
    "Limited Docker/containerization experience",
    "Some gaps in advanced Python concepts",
    "Could improve database optimization"
  ],
  "recommendation_reasoning": "Strong technical foundation with scores above 70. Ready for senior engineer round.",
  "hr_summary": "John demonstrated solid technical expertise... The hiring team can confidently move forward with a human interview."
}
```

---

## 🔧 How Report Generation Works

### Step-by-Step (Agent 7)

```python
1. Load interview_log.json
   ├─ Iterate over every Q&A pair
   ├─ Extract evaluation (Agent 6 output)
   └─ Classify: correct / partial / wrong

2. Compute Deterministic Scores (Python)
   ├─ Count correct/partial/wrong
   ├─ Build skill tracker (per-skill breakdown)
   ├─ Calculate weighted scores (easy=1, medium=2, high=3)
   ├─ Compute interview_performance_score
   ├─ Blend with requirement_match_score → combined_score
   └─ Decide recommendation label

3. LLM Writes Narrative
   ├─ Input: transcript + computed scores
   ├─ LLM writes: strengths, weaknesses, reasoning
   └─ Lock: LLM cannot contradict computed scores

4. Save & Update
   ├─ Save final_report.json
   ├─ Update candidate record (scores + recommendation)
   └─ Candidate now appears in rankings/statistics
```

**Key:** All numbers are Python-computed (deterministic, auditable). Only text (strengths/weaknesses/summary) comes from LLM, and it's consistent with the numbers.

---

## 🎓 Recommendation Logic

```python
if was_terminated:
    recommendation = "Not Recommended"
elif combined_score >= 70:
    recommendation = "Recommended for Human Interview"
elif combined_score >= 50:
    recommendation = "Borderline - Consider for Human Interview"
else:
    recommendation = "Not Recommended"
```

---

## 📈 Ranking Algorithm

```python
# Sort all completed candidates
completed_candidates = [c for c in all_candidates if c.status == "Completed"]

# Sort by combined_score descending
ranked = sorted(completed_candidates, key=lambda c: c.combined_score, reverse=True)

# Return top N
top_n = ranked[:limit]  # e.g., limit=10 for top 10
```

**Ties:** If two candidates have the same combined_score, order is determined by creation timestamp (earlier created = higher in ranking).

---

## 📁 Files Updated/Added (Part 2)

```
backend/
├── routes/
│   ├── admin.py           (unchanged)
│   ├── candidate.py       (unchanged)
│   └── report.py          ← NEW (ranking, report generation)
├── services/
│   ├── agent7_report.py   (unchanged, already complete)
│   └── ... (all others unchanged)
├── models/
│   └── schemas.py         ← UPDATED (report response models)
└── main.py                ← UPDATED (added report router)
```

---

## 🎯 Example: Complete Interview-to-Report Flow

```
Admin uploads JD.pdf
  ↓
Candidate 1 uploads resume.pdf
  Requirement Match: 75 → Eligible ✅
  Starts interview
  Completes all 6 steps (28 questions)
  Interview Performance: 82
  Combined Score: (75 + 82) / 2 = 78.5
  ↓
Candidate 2 uploads resume.pdf
  Requirement Match: 45 → Disqualified ❌
  No interview
  ↓
Candidate 3 uploads resume.pdf
  Requirement Match: 72 → Eligible ✅
  Starts interview
  Completes (25 questions)
  Interview Performance: 78
  Combined Score: (72 + 78) / 2 = 75
  ↓
Admin Calls: GET /report/ranking/by-score?limit=5
  ↓
Returns (sorted by combined_score):
  1. Candidate 1 (78.5) - Recommended
  2. Candidate 3 (75.0) - Recommended
  (more results...)
  ↓
Admin calls: GET /report/statistics/overview
  ↓
Returns:
  - Total: 3 candidates
  - Disqualified: 1
  - Completed: 2
  - Avg combined score: 76.75
  - Recommendations: 2 "Recommended"
```

---

## ✨ Key Features (Part 2)

✅ **Deterministic Scoring** — all numbers computed in Python, auditable
✅ **LLM Narrative** — only text (strengths/weaknesses), consistent with scores
✅ **Per-Skill Breakdown** — see how candidate performed on each skill/tier
✅ **Per-Step Summary** — confidence and question count per step
✅ **Candidate Ranking** — top N by score
✅ **Pipeline Statistics** — overall flow metrics
✅ **Easy Integration** — works seamlessly with Part 1

---

## 🚀 Using Part 2 (Example API Calls)

### Generate Report
```bash
curl -X POST http://localhost:8000/report/abc-123/generate
```

### View Report
```bash
curl http://localhost:8000/report/abc-123
```

### Top 10 Candidates
```bash
curl http://localhost:8000/report/ranking/by-score?limit=10
```

### Pipeline Statistics
```bash
curl http://localhost:8000/report/statistics/overview
```

---

## 📊 What Admin Sees (Post Part 2)

### Candidate List
```
GET /admin/candidates
```
Now shows:
- Name, status (Completed, Disqualified, etc.)
- Requirement Match Score
- Interview Performance Score (if completed)
- Combined Score (if completed)
- Recommendation (if completed)

### Rankings
```
GET /report/ranking/by-score
```
Sorted by combined score, top performers at top.

### Statistics
```
GET /report/statistics/overview
```
- Pipeline funnel (total → disqualified → completed)
- Average scores
- Recommendation distribution

---

## ⚙️ Troubleshooting Part 2

### Report not generating?
- Check interview is "Completed" status
- Check interview_log.json exists and has data
- Check all supporting JSONs exist (resume, matcher, planner, jd)

### Scores seem wrong?
- Each partial-correct answer earns 50% of the tier weight
- Easy tier = 1x weight, Medium = 2x, High = 3x
- Formula: (weighted_earned / weighted_total) * 100

### Ranking missing candidates?
- Only "Completed" candidates with reports appear
- Disqualified and Eligible (no interview yet) don't rank

---

## 🎯 Next Steps After Part 2

1. ✅ Part 1: Backend + Interview Flow — DONE
2. ✅ Part 2: Scoring + Ranking + Reports — DONE
3. ⏳ Frontend: Admin dashboard + Candidate interface (TBD)
4. ⏳ Deployment: Docker, cloud hosting (TBD)

---

**Part 2 Status: ✅ COMPLETE & PRODUCTION-READY**

All scoring logic, ranking, and reporting fully implemented and integrated.
