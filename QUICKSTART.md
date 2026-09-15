# QUICK START - Part 1: Backend API

## Step 1: Install Dependencies
```bash
pip install -r requirements.txt
```

## Step 2: Set Up Environment
Create `.env` file in project root with:
```
GROQ_API_KEY=your_groq_api_key_here
PORT=8000
```

Or copy from .env.example:
```bash
cp .env.example .env
# Then edit .env and add your GROQ_API_KEY
```

## Step 3: Run the Backend
```bash
python3 -m backend.main
```

Server will start on: **http://localhost:8000**

## Step 4: Test the API

### A. Check Health
```bash
curl http://localhost:8000/health
```

### B. Upload JD (Admin)
```bash
curl -X POST http://localhost:8000/admin/upload-jd \
  -F "file=@path/to/your_jd.pdf"
```

### C. Check JD Status
```bash
curl http://localhost:8000/admin/jd-status
```

### D. Upload Resume (Candidate)
```bash
curl -X POST http://localhost:8000/candidates/resume \
  -F "file=@path/to/resume.pdf"

# Returns:
# {
#   "candidate_id": "abc-123",
#   "name": "John Doe",
#   "status": "Eligible" or "Disqualified",
#   "requirement_match_score": 72
# }
```

### E. Start Interview (if Eligible)
```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/start

# Returns:
# {
#   "bot_message": "Hello John, ...",
#   "asked_question": true,
#   "interview_completed": false
# }
```

### F. Answer a Question
```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "I have 5 years of Python experience..."}'

# Returns next question or interview complete
```

### G. View All Candidates
```bash
curl http://localhost:8000/admin/candidates
```

## Step 5: View Interactive API Docs
Open in browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

## 📁 Project Structure
```
interview-screening-backend/
├── backend/
│   ├── main.py              ← Run this: `python3 -m backend.main`
│   ├── services/            ← All agents (1-7) + controller
│   ├── routes/              ← API endpoints (admin, candidate)
│   └── models/              ← Pydantic schemas
├── data/                    ← Candidate data (auto-created)
├── .env                     ← Your API key (create from .env.example)
├── .env.example             ← Template
├── requirements.txt         ← Python dependencies
└── README.md                ← Full documentation
```

## 🚀 What Works Now (Part 1)

✅ Admin can upload JD (PDF)
✅ Candidate can upload Resume (PDF)
✅ Automatic eligibility screening (requirement matching)
✅ Disqualified candidates auto-added to admin list
✅ Eligible candidates can start interview
✅ Full interview with Easy→Medium→High tiering
✅ Real-time answer evaluation
✅ All data persisted to JSON

## 📋 What's Coming (Part 2)

⏳ Final scoring & ranking
⏳ Interview performance score calculation
⏳ Combined score (requirement match + interview)
⏳ Candidate ranking (top 5, 10, etc.)
⏳ Final report generation & viewing

## 🆘 Troubleshooting

### "ModuleNotFoundError: No module named 'backend'"
Make sure you're running from the project root directory:
```bash
cd /path/to/interview-screening-backend
python3 -m backend.main
```

### "No such file or directory: 'data/jd.json'"
This is normal on first run. Upload a JD PDF first via `/admin/upload-jd`

### Port 8000 already in use?
```bash
PORT=8001 python3 -m backend.main
```

### LLM errors?
Check your GROQ_API_KEY in `.env` is valid

## 📞 Questions?
Refer to README.md for full API documentation and architecture details.
