"""Candidate routes: resume upload, interview start/continue."""

from fastapi import APIRouter, UploadFile, File, HTTPException, Path
from typing import Optional
import json
import uuid
import os

from backend.services.pipeline_utils import save_uploaded_resume, run_screening_pipeline
from backend.services.candidate_store import create_candidate, update_candidate, get_candidate
from backend.services.session_store import start_session, get_session, update_session, end_session
from backend.services.interview_controller import InterviewController
from backend.services.interview_manager import generate_bot_message
from backend.services.answer_evaluator import evaluate_answer
from backend.models.schemas import ResumeUploadResponse, AnswerRequest, InterviewTurnResponse

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("/resume", response_model=ResumeUploadResponse)
async def upload_resume(file: UploadFile = File(...)):
    """Candidate uploads resume PDF. Agent 1 parses, Agent 3 matches."""
    if not file.filename.lower().endswith('.pdf'):
        raise HTTPException(status_code=400, detail="Only PDF files are allowed for resume.")
    
    pdf_bytes = await file.read()
    if not pdf_bytes:
        raise HTTPException(status_code=400, detail="File is empty.")
    
    candidate_id = str(uuid.uuid4())
    
    try:
        resume_path = save_uploaded_resume(candidate_id, pdf_bytes, file.filename)
        resume, jd, matcher, interview_plan = run_screening_pipeline(candidate_id, resume_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to process resume: {str(e)}")
    
    # Extract candidate name from resume
    name = resume.get("name", "Candidate")
    
    # Store candidate in the index
    create_candidate(candidate_id, name)
    
    if not matcher["interview_eligible"]:
        # Disqualified
        update_candidate(
            candidate_id,
            status="Disqualified",
            requirement_match_score=matcher["requirement_match_score"],
            recommendation="Not Recommended",
        )
        return ResumeUploadResponse(
            candidate_id=candidate_id,
            name=name,
            status="Disqualified",
            requirement_match_score=matcher["requirement_match_score"],
            reason=matcher.get("reason", "Does not meet minimum requirements."),
        )
    else:
        # Eligible for interview
        update_candidate(
            candidate_id,
            status="Eligible",
            requirement_match_score=matcher["requirement_match_score"],
        )
        return ResumeUploadResponse(
            candidate_id=candidate_id,
            name=name,
            status="Eligible",
            requirement_match_score=matcher["requirement_match_score"],
        )


@router.post("/{candidate_id}/interview/start", response_model=InterviewTurnResponse)
async def start_interview(candidate_id: str = Path(...)):
    """Start the interview for an eligible candidate."""
    candidate = get_candidate(candidate_id)
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found.")
    
    if candidate.get("status") != "Eligible":
        raise HTTPException(status_code=400, detail="Candidate is not eligible for interview.")
    
    # Load the candidate's data
    base = f"data/candidates/{candidate_id}"
    try:
        with open(f"{base}/resume.json", "r") as f:
            resume = json.load(f)
        with open(f"{base}/matcher.json", "r") as f:
            matcher = json.load(f)
        with open(f"{base}/planner.json", "r") as f:
            interview_plan = json.load(f)
        with open("data/jd.json", "r") as f:
            jd = json.load(f)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load interview data: {str(e)}")
    
    # Set up the interview session
    controller = InterviewController(interview_plan)
    start_session(candidate_id, controller)
    
    # Get the first question
    directive = controller.next_action(None)
    output = generate_bot_message(directive, resume, jd, matcher, interview_plan, [], None)
    
    update_session(
        candidate_id,
        pending_directive=directive,
        pending_output=output,
        resume=resume,
        jd=jd,
        matcher=matcher,
        interview_plan=interview_plan,
    )
    
    update_candidate(candidate_id, status="Interviewing")
    
    return InterviewTurnResponse(
        candidate_id=candidate_id,
        bot_message=output.bot_response,
        asked_question=output.asked_question,
        interview_completed=False,
        interview_terminated=False,
    )


@router.post("/{candidate_id}/interview/answer", response_model=InterviewTurnResponse)
async def submit_answer(candidate_id: str = Path(...), req: AnswerRequest = None):
    """Candidate submits an answer. Agent 6 evaluates, Agent 5 gets next question."""
    session = get_session(candidate_id)
    if not session:
        raise HTTPException(status_code=404, detail="No active interview session for this candidate.")
    
    if not req or not req.answer.strip():
        raise HTTPException(status_code=400, detail="Answer cannot be empty.")
    
    controller = session["controller"]
    resume = session["resume"]
    jd = session["jd"]
    matcher = session["matcher"]
    interview_plan = session["interview_plan"]
    conversation_history = session["conversation_history"]
    interview_log = session["interview_log"]
    
    directive = session["pending_directive"]
    output = session["pending_output"]
    
    # Add to conversation history
    conversation_history.append({"question": output.bot_response, "answer": req.answer})
    
    # Agent 6 evaluates
    try:
        evaluation = evaluate_answer(
            question=output.bot_response,
            answer=req.answer,
            resume=resume,
            jd=jd,
            matcher=matcher,
            interview_plan=interview_plan,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to evaluate answer: {str(e)}")
    
    # Log the Q&A
    interview_log.append({
        "step_number": directive.get("step_number"),
        "step_name": directive.get("step_name"),
        "skill_name": directive.get("skill_name"),
        "tier": directive.get("tier"),
        "topic": directive.get("topic"),
        "context_type": directive.get("context_type"),
        "mandatory": directive.get("mandatory"),
        "question": output.bot_response,
        "answer": req.answer,
        "evaluation": evaluation.model_dump(),
    })
    
    # Get next action from controller
    next_directive = controller.next_action(evaluation)
    
    if next_directive.get("terminate") or next_directive.get("complete"):
        # Interview is done
        end_session(candidate_id)
        update_candidate(candidate_id, status="Completed")
        
        # Save interview log
        with open(f"data/candidates/{candidate_id}/interview_log.json", "w") as f:
            json.dump(interview_log, f, indent=2)
        
        return InterviewTurnResponse(
            candidate_id=candidate_id,
            bot_message="Interview complete. Thank you for your time!",
            asked_question=False,
            interview_completed=next_directive.get("complete", False),
            interview_terminated=next_directive.get("terminate", False),
        )
    
    # Next question from Agent 5
    next_output = generate_bot_message(
        next_directive, resume, jd, matcher, interview_plan, conversation_history, evaluation
    )
    
    # Update session for the next turn
    update_session(
        candidate_id,
        conversation_history=conversation_history,
        interview_log=interview_log,
        last_evaluation=evaluation,
        pending_directive=next_directive,
        pending_output=next_output,
    )
    
    return InterviewTurnResponse(
        candidate_id=candidate_id,
        bot_message=next_output.bot_response,
        asked_question=next_output.asked_question,
        interview_completed=False,
        interview_terminated=False,
    )
