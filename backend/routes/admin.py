"""Admin routes: JD upload, candidate list."""

from fastapi import APIRouter, UploadFile, File, HTTPException
from backend.services.pipeline_utils import parse_and_cache_jd_pdf, jd_is_ready
from backend.services.candidate_store import list_candidates
from backend.models.schemas import JDUploadResponse, JDStatusResponse, CandidateListItem

router = APIRouter(prefix="/admin", tags=["admin"])


@router.post("/upload-jd", response_model=JDUploadResponse)
async def upload_jd(file: UploadFile = File(...)):
    """Admin uploads the job description PDF (once per role)."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for JD.")
    
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="File is empty.")
    
    try:
        jd = parse_and_cache_jd_pdf(pdf_bytes, file.filename)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse JD: {str(e)}")
    
    return JDUploadResponse(
        job_title=jd.get("job_title", "Unknown"),
        message=f"JD parsed successfully: {jd.get('job_title', 'Job')} at {jd.get('company_name', 'Company')}"
    )


@router.get("/jd-status", response_model=JDStatusResponse)
async def jd_status():
    """Check if JD has been uploaded and cached."""
    return JDStatusResponse(ready=jd_is_ready())


@router.get("/candidates", response_model=list[CandidateListItem])
async def list_all_candidates():
    """Get all candidates (Eligible, Disqualified, Interviewed, etc.)."""
    candidates = list_candidates()
    return [
        CandidateListItem(
            candidate_id=c.get("candidate_id"),
            name=c.get("name"),
            status=c.get("status", "Unknown"),
            requirement_match_score=c.get("requirement_match_score"),
            interview_performance_score=c.get("interview_performance_score"),
            combined_score=c.get("combined_score"),
            recommendation=c.get("recommendation"),
            created_at=c.get("created_at"),
        )
        for c in candidates
    ]
