# 🎉 DOWNLOAD & RUN - Part 1: Backend

You have a **complete, working FastAPI backend** for the interview screening system. Here's how to get it running.

## What You Have

A full FastAPI backend with:
- 7 AI agents (Resume → Interview → Evaluation)
- New Easy→Medium→High tiered questioning engine
- Admin API (JD upload, candidate list)
- Candidate API (resume upload, full interview flow)
- Automatic eligibility screening
- JSON-based data persistence

**No frontend yet** — just the backend API. Frontend will consume these endpoints.

---

## 📥 Step 1: Download

The folder `interview-screening-backend/` contains everything. Download it.

---

## 🔧 Step 2: Install Dependencies

```bash
cd interview-screening-backend
pip install -r requirements.txt
```

**Python 3.8+** required.

---

## 🔑 Step 3: Set Up Your API Key

Copy `.env.example` to `.env`:
```bash
cp .env.example .env
```

Edit `.env` and add your Groq API key:
```
GROQ_API_KEY=your_actual_groq_api_key_here
PORT=8000
```

Get a free Groq API key at https://console.groq.com/

---

## 🚀 Step 4: Run the Backend

```bash
python3 -m backend.main
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

---

## 🌐 Step 5: Test It

### Option A: Interactive API Docs (Best)
Open in your browser:
- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc

You can test every endpoint directly in the browser.

### Option B: Command Line (curl)

**Test health:**
```bash
curl http://localhost:8000/health
```

**Upload JD (Admin):**
```bash
curl -X POST http://localhost:8000/admin/upload-jd \
  -F "file=@/path/to/your_jd.pdf"
```

**Upload Resume (Candidate):**
```bash
curl -X POST http://localhost:8000/candidates/resume \
  -F "file=@/path/to/resume.pdf"

# Response:
# {
#   "candidate_id": "abc-123",
#   "name": "John Doe",
#   "status": "Eligible",
#   "requirement_match_score": 72
# }
```

**Start Interview:**
```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/start
```

**Answer Question:**
```bash
curl -X POST http://localhost:8000/candidates/abc-123/interview/answer \
  -H "Content-Type: application/json" \
  -d '{"answer": "I have 5 years of Python experience..."}'
```

**See All Candidates:**
```bash
curl http://localhost:8000/admin/candidates
```

---

## 📚 Documentation

Inside the folder you'll find:

1. **README.md** — Full architecture, all endpoints, tech stack details
2. **QUICKSTART.md** — 5-minute quick reference
3. **PART1_SUMMARY.md** — What's implemented, what's next

**START HERE:** Read QUICKSTART.md first (5 min), then README.md for full details.

---

## 📁 Folder Structure

```
interview-screening-backend/
├── backend/                 ← All code (agents, routes, etc.)
├── data/                    ← Candidate data (auto-created)
├── requirements.txt         ← Dependencies to install
├── .env.example             ← Copy to .env and add API key
├── README.md                ← Full documentation
├── QUICKSTART.md            ← Quick reference
└── PART1_SUMMARY.md         ← What's done, what's next
```

---

## ✅ What Works Now (Part 1)

✅ Admin uploads JD (PDF)
✅ Candidate uploads resume (PDF)  
✅ Automatic eligibility screening
✅ Disqualified candidates marked immediately
✅ Eligible candidates can start interview
✅ Full interview with smart question progression
✅ Real-time answer evaluation
✅ All data saved as JSON

---

## ⏳ Coming in Part 2

Part 2 will add:
- Final scoring & ranking
- Interview performance calculations
- Combined scores
- Candidate comparison/ranking
- Final report generation

---

## 🆘 Troubleshooting

### Port 8000 already in use?
```bash
PORT=8001 python3 -m backend.main
```

### "ModuleNotFoundError: No module named 'backend'"
Make sure you're in the project root:
```bash
cd /path/to/interview-screening-backend
python3 -m backend.main
```

### "GROQ_API_KEY not found"
Check `.env` file exists in the project root and has your API key.

### Need test files?
Create dummy JD.pdf and resume.pdf for testing. Or use PDF examples from your system.

---

## 🎯 What to Do Next

1. ✅ Get it running locally (above)
2. ✅ Test the API endpoints (via Swagger UI or curl)
3. ✅ Understand the flow by reading README.md
4. ⏳ Build a frontend (not included yet)
5. ⏳ Wait for Part 2 (scoring/ranking/reports)

---

## 📞 More Info?

Read the documentation files inside the folder:
- **README.md** — Architecture, all endpoints, limitations
- **QUICKSTART.md** — Quick API reference with examples
- **PART1_SUMMARY.md** — What's implemented & what's next

---

**Backend Part 1 is READY TO USE.** 🚀
