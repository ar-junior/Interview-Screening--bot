from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class JDUploadResponse(BaseModel):
    job_title: str
    message: str


class JDStatusResponse(BaseModel):
    ready: bool


class ResumeUploadResponse(BaseModel):
    candidate_id: str
    status: str  # "Eligible" | "Disqualified"
    requirement_match_score: float
    reason: Optional[str] = None


class AnswerRequest(BaseModel):
    answer: str


class InterviewTurnResponse(BaseModel):
    candidate_id: str
    bot_message: str
    asked_question: bool
    interview_completed: bool
    interview_terminated: bool


class CandidateListItem(BaseModel):
    candidate_id: str
    name: Optional[str] = None
    status: str
    requirement_match_score: Optional[float] = None
    interview_performance_score: Optional[float] = None
    combined_score: Optional[float] = None
    recommendation: Optional[str] = None
    created_at: Optional[str] = None


class SkillBreakdown(BaseModel):
    skill_name: str
    mandatory: bool
    context_type: str
    tier_reached: str
    easy_correct: int
    easy_total: int
    medium_correct: int
    medium_total: int
    high_correct: int
    high_total: int
    skill_passed: bool


class StepSummary(BaseModel):
    step_number: int
    step_name: str
    questions_asked: int
    average_confidence: float


class FinalReport(BaseModel):
    candidate_name: str
    interview_status: str
    termination_reason: Optional[str] = None
    total_questions_asked: int
    total_correct: int
    total_partial: int
    total_wrong: int
    technical_accuracy_score: float
    logical_accuracy_score: float
    average_confidence_score: float
    interview_performance_score: float
    requirement_match_score: float
    combined_score: float
    overall_recommendation: str
    recommendation_reasoning: str
    strengths: List[str]
    weaknesses: List[str]
    hr_summary: str
    per_skill_breakdown: List[SkillBreakdown]
    per_step_summary: List[StepSummary]


class RankingResponse(BaseModel):
    total_completed: int
    total_ranked: int
    rankings: List[CandidateListItem]


class StatisticsOverview(BaseModel):
    total_candidates: int
    disqualified_count: int
    eligible_not_interviewed_count: int
    interviewing_count: int
    completed_count: int
    average_requirement_match_score: float
    average_interview_performance_score: float
    average_combined_score: float
    recommendation_breakdown: Dict[str, int]
