"""Report routes: final report generation, ranking, candidate details."""

from fastapi import APIRouter, HTTPException, Path
from typing import List
import json
import os

from backend.services.agent7_report import generate_final_report
from backend.services.candidate_store import get_candidate, update_candidate, list_candidates
from backend.models.schemas import CandidateListItem, FinalReport, RankingResponse, StatisticsOverview

router = APIRouter(prefix="/report", tags=["report"])


@router.post("/{candidate_id}/generate")
async def generate_report(candidate_id: str = Path(...)):
    """
    Generate final report for a completed interview.
    
    This endpoint:
    1. Loads interview_log.json
    2. Loads resume, jd, matcher, planner JSONs
    3. Calls Agent 7 to generate report
    4. Saves report to JSON
    5. Updates candidate record with scores
    6. Returns report
    """
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    
    if candidate.get("status") != "Completed":
        raise HTTPException(status_code=400, detail="Report can only be generated for completed interviews.")
    
    base = f"data/candidates/{candidate_id}"
    
    # Load all required data
    try:
        with open(f"{base}/resume.json", "r") as f:
            resume = json.load(f)
        with open(f"{base}/matcher.json", "r") as f:
            matcher = json.load(f)
        with open("data/jd.json", "r") as f:
            jd = json.load(f)
        with open(f"{base}/planner.json", "r") as f:
            interview_plan = json.load(f)
        with open(f"{base}/interview_log.json", "r") as f:
            interview_log = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load interview data: {str(e)}")
    
    # Generate report using Agent 7
    try:
        report = generate_final_report(
            interview_log=interview_log,
            matcher=matcher,
            resume=resume,
            jd=jd,
            interview_plan=interview_plan,
            was_terminated=False,
            termination_reason=None,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate report: {str(e)}")
    
    # Save report
    with open(f"{base}/final_report.json", "w") as f:
        json.dump(report, f, indent=2)
    
    # Update candidate record with scores
    update_candidate(
        candidate_id,
        status="Completed",
        interview_performance_score=report.get("interview_performance_score"),
        combined_score=report.get("combined_score"),
        recommendation=report.get("overall_recommendation"),
    )
    
    return report


@router.get("/{candidate_id}")
async def get_report(candidate_id: str = Path(...)):
    """
    Get final report for a candidate.
    
    Returns the full report if it exists, including:
    - All scores (requirement_match, interview_performance, combined)
    - Per-skill breakdown
    - Per-step summary
    - Strengths, weaknesses, recommendation
    """
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    
    report_path = f"data/candidates/{candidate_id}/final_report.json"
    if not os.path.exists(report_path):
        raise HTTPException(status_code=404, detail="Report not yet generated. Call /report/{id}/generate first.")
    
    try:
        with open(report_path, "r") as f:
            report = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load report: {str(e)}")
    
    return report


@router.get("/ranking/by-score")
async def get_ranking_by_score(limit: int = 10):
    """
    Get top N candidates ranked by combined_score (descending).
    
    Only includes candidates with completed interviews and generated reports.
    """
    candidates = list_candidates()
    
    # Filter: only completed with scores
    ranked = [
        c for c in candidates
        if c.get("status") == "Completed" and c.get("combined_score") is not None
    ]
    
    # Sort by combined_score descending
    ranked.sort(key=lambda c: c.get("combined_score", 0), reverse=True)
    
    # Limit
    ranked = ranked[:limit]
    
    return {
        "total_completed": len([c for c in candidates if c.get("status") == "Completed"]),
        "total_ranked": len(ranked),
        "rankings": [
            CandidateListItem(
                candidate_id=c.get("candidate_id"),
                name=c.get("name"),
                status=c.get("status"),
                requirement_match_score=c.get("requirement_match_score"),
                interview_performance_score=c.get("interview_performance_score"),
                combined_score=c.get("combined_score"),
                recommendation=c.get("recommendation"),
                created_at=c.get("created_at"),
            )
            for c in ranked
        ],
    }


@router.get("/statistics/overview")
async def get_statistics_overview():
    """
    Get overall statistics across all candidates.
    
    Returns:
    - Total candidates
    - Disqualified count
    - Eligible but not interviewed
    - Completed count
    - Average scores
    - Recommendation breakdown
    """
    candidates = list_candidates()
    
    completed = [c for c in candidates if c.get("status") == "Completed"]
    disqualified = [c for c in candidates if c.get("status") == "Disqualified"]
    eligible = [c for c in candidates if c.get("status") == "Eligible"]
    interviewing = [c for c in candidates if c.get("status") == "Interviewing"]
    
    recommendation_breakdown = {}
    for c in completed:
        rec = c.get("recommendation", "Unknown")
        recommendation_breakdown[rec] = recommendation_breakdown.get(rec, 0) + 1
    
    avg_requirement_match = (
        sum(c.get("requirement_match_score", 0) for c in candidates if c.get("requirement_match_score")) / len([c for c in candidates if c.get("requirement_match_score")])
        if [c for c in candidates if c.get("requirement_match_score")] else 0
    )
    
    avg_interview_performance = (
        sum(c.get("interview_performance_score", 0) for c in completed if c.get("interview_performance_score")) / len([c for c in completed if c.get("interview_performance_score")])
        if [c for c in completed if c.get("interview_performance_score")] else 0
    )
    
    avg_combined = (
        sum(c.get("combined_score", 0) for c in completed if c.get("combined_score")) / len([c for c in completed if c.get("combined_score")])
        if [c for c in completed if c.get("combined_score")] else 0
    )
    
    return {
        "total_candidates": len(candidates),
        "disqualified_count": len(disqualified),
        "eligible_not_interviewed_count": len(eligible),
        "interviewing_count": len(interviewing),
        "completed_count": len(completed),
        "average_requirement_match_score": round(avg_requirement_match, 1),
        "average_interview_performance_score": round(avg_interview_performance, 1),
        "average_combined_score": round(avg_combined, 1),
        "recommendation_breakdown": recommendation_breakdown,
    }
