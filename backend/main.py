"""FastAPI application for AI-Powered Multi-Agent Interview Screening System.

This is a backend-only API. Candidate and Admin interfaces will be built as
separate frontend applications that hit these endpoints.

Endpoints:
  Admin:
    POST   /admin/upload-jd           -> upload and cache JD PDF
    GET    /admin/jd-status           -> check if JD is ready
    GET    /admin/candidates          -> list all candidates (screened, interviewed, etc.)

  Candidate:
    POST   /candidates/resume         -> upload resume, get screening result
    POST   /candidates/{id}/interview/start  -> start interview
    POST   /candidates/{id}/interview/answer -> submit answer, get next question
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
from dotenv import load_dotenv

load_dotenv()

from backend.routes import admin, candidate, report

app = FastAPI(
    title="AI Interview Screening Backend",
    description="Multi-agent system for automated technical candidate screening",
    version="1.0.0",
)

# CORS middleware (for future frontend)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your frontend domain
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routes
app.include_router(admin.router)
app.include_router(candidate.router)
app.include_router(report.router)


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


@app.get("/")
async def root():
    return {
        "name": "AI Interview Screening System (Backend Only)",
        "version": "1.0.0",
        "endpoints": {
            "admin": "/admin",
            "candidates": "/candidates",
            "health": "/health",
        },
    }


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", "8000"))
    uvicorn.run(app, host="0.0.0.0", port=port)
