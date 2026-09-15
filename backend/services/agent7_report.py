"""
Agent 7 — Final Interview Report Generator.

All NUMBERS are computed deterministically in Python from the evaluation
reports Agent 6 already produced. The LLM only writes the qualitative
narrative (strengths, weaknesses, HR summary) and cannot alter the numbers.
"""

from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List, Dict, Optional
import json

TIER_WEIGHT = {"easy": 1, "medium": 2, "high": 3}


def _classify(evaluation: dict) -> str:
    if not evaluation.get("relevant_answer", False):
        return "wrong"
    tech = evaluation.get("technically_correct", False)
    logic = evaluation.get("logically_correct", False)
    if tech and logic:
        return "correct"
    if tech or logic:
        return "partial"
    return "wrong"


def aggregate_scores(interview_log: List[dict], requirement_match_score: float) -> dict:
    total_correct = total_partial = total_wrong = 0
    confidence_scores = []
    technically_correct_count = 0
    logically_correct_count = 0

    skill_map: Dict[str, dict] = {}
    step_map: Dict[int, dict] = {}
    weighted_earned = 0.0
    weighted_total = 0.0

    for entry in interview_log:
        ev = entry.get("evaluation") or {}
        correctness = _classify(ev)

        if correctness == "correct":
            total_correct += 1
        elif correctness == "partial":
            total_partial += 1
        else:
            total_wrong += 1

        confidence_scores.append(ev.get("confidence_score", 0) or 0)
        if ev.get("technically_correct"):
            technically_correct_count += 1
        if ev.get("logically_correct"):
            logically_correct_count += 1

        skill = entry.get("skill_name")
        tier = entry.get("tier")
        if skill and tier and tier in TIER_WEIGHT:
            s = skill_map.setdefault(skill, {
                "mandatory": entry.get("mandatory", False),
                "context_type": entry.get("context_type", "skill"),
                "tiers": {"easy": [0, 0], "medium": [0, 0], "high": [0, 0]},
            })
            s["tiers"][tier][1] += 1
            if correctness in ("correct", "partial"):
                s["tiers"][tier][0] += 1
            w = TIER_WEIGHT[tier]
            weighted_total += w
            if correctness == "correct":
                weighted_earned += w
            elif correctness == "partial":
                weighted_earned += w * 0.5

        step_key = entry["step_number"]
        st = step_map.setdefault(step_key, {
            "step_name": entry.get("step_name", f"Step {step_key}"),
            "questions_asked": 0, "confidence_sum": 0.0,
        })
        st["questions_asked"] += 1
        st["confidence_sum"] += ev.get("confidence_score", 0) or 0

    total_questions = total_correct + total_partial + total_wrong

    technical_accuracy_score = round(technically_correct_count / total_questions * 100, 1) if total_questions else 0.0
    logical_accuracy_score = round(logically_correct_count / total_questions * 100, 1) if total_questions else 0.0
    average_confidence_score = round(sum(confidence_scores) / len(confidence_scores), 1) if confidence_scores else 0.0

    interview_performance_score = (
        round(weighted_earned / weighted_total * 100, 1) if weighted_total else average_confidence_score
    )
    combined_score = round((requirement_match_score + interview_performance_score) / 2, 1)

    per_skill_breakdown = []
    for skill_name, data in skill_map.items():
        tiers = data["tiers"]
        tier_reached = "not_attempted"
        for t in ("high", "medium", "easy"):
            if tiers[t][1] > 0:
                tier_reached = t
                break
        skill_passed = any(tiers[t][0] > 0 for t in tiers) if tier_reached != "not_attempted" else False
        per_skill_breakdown.append({
            "skill_name": skill_name, "mandatory": data["mandatory"], "context_type": data["context_type"],
            "tier_reached": tier_reached,
            "easy_correct": tiers["easy"][0], "easy_total": tiers["easy"][1],
            "medium_correct": tiers["medium"][0], "medium_total": tiers["medium"][1],
            "high_correct": tiers["high"][0], "high_total": tiers["high"][1],
            "skill_passed": skill_passed,
        })

    per_step_summary = []
    for step_number, data in sorted(step_map.items()):
        avg_conf = round(data["confidence_sum"] / data["questions_asked"], 1) if data["questions_asked"] else 0.0
        per_step_summary.append({
            "step_number": step_number, "step_name": data["step_name"],
            "questions_asked": data["questions_asked"], "average_confidence": avg_conf,
        })

    return {
        "total_questions_asked": total_questions, "total_correct": total_correct,
        "total_partial": total_partial, "total_wrong": total_wrong,
        "technical_accuracy_score": technical_accuracy_score, "logical_accuracy_score": logical_accuracy_score,
        "average_confidence_score": average_confidence_score,
        "interview_performance_score": interview_performance_score,
        "requirement_match_score": requirement_match_score, "combined_score": combined_score,
        "per_skill_breakdown": per_skill_breakdown, "per_step_summary": per_step_summary,
    }


def _default_recommendation(aggregate: dict, was_terminated: bool) -> str:
    if was_terminated:
        return "Not Recommended"
    score = aggregate["combined_score"]
    if score >= 70:
        return "Recommended for Human Interview"
    if score >= 50:
        return "Borderline - Consider for Human Interview"
    return "Not Recommended"


class NarrativeReport(BaseModel):
    strengths: List[str] = Field(description="3-5 concrete strengths observed during the interview.")
    weaknesses: List[str] = Field(description="3-5 concrete weaknesses or gaps observed during the interview.")
    recommendation_reasoning: str = Field(description="1-2 sentence explanation of why the recommendation fits the data.")
    hr_summary: str = Field(description="A short (4-6 sentence) paragraph an HR reviewer can read on its own.")


def generate_final_report(
    interview_log: List[dict], matcher: dict, resume: dict, jd: dict, interview_plan: dict,
    was_terminated: bool = False, termination_reason: Optional[str] = None,
) -> dict:
    load_dotenv()

    requirement_match_score = matcher.get("requirement_match_score", 0)
    aggregate = aggregate_scores(interview_log, requirement_match_score)
    recommendation = _default_recommendation(aggregate, was_terminated)

    narrative_prompt = PromptTemplate(
        template="""
You are a senior technical recruiter writing the closing summary of a candidate's AI-conducted
technical screening interview.

You are given the FULL transcript and the ALREADY-COMPUTED scores below. Do NOT invent different
numbers — only write strengths, weaknesses, a short reasoning sentence for the recommendation, and
an HR summary paragraph, consistent with the data given.

Candidate Resume:
{resume}

Job Description:
{jd}

Requirement Match Result:
{matcher}

Full Interview Transcript:
{transcript}

Computed Scores (do not contradict these):
{aggregate}

Interview outcome: {outcome}
Recommendation label already decided by the system: {recommendation}

Write:
1. 3-5 strengths, grounded in specific things the candidate actually said.
2. 3-5 weaknesses/gaps, grounded in specific things the candidate said or failed to answer.
3. A 1-2 sentence explanation of why the recommendation label fits the data.
4. A 4-6 sentence HR summary paragraph.

Return the output strictly according to the provided schema.
""",
        input_variables=["resume", "jd", "matcher", "transcript", "aggregate", "outcome", "recommendation"],
    )

    llm = ChatGroq(model="openai/gpt-oss-120b")
    structured_llm = llm.with_structured_output(NarrativeReport)
    chain = narrative_prompt | structured_llm

    outcome_text = f"Interview terminated early: {termination_reason}" if was_terminated else "Interview completed in full."

    narrative = chain.invoke({
        "resume": json.dumps(resume, indent=2), "jd": json.dumps(jd, indent=2),
        "matcher": json.dumps(matcher, indent=2), "transcript": json.dumps(interview_log, indent=2),
        "aggregate": json.dumps(aggregate, indent=2), "outcome": outcome_text, "recommendation": recommendation,
    })

    return {
        "candidate_name": resume.get("name", "Unknown"),
        "interview_status": "Terminated Early" if was_terminated else "Completed",
        "termination_reason": termination_reason,
        **aggregate,
        "overall_recommendation": recommendation,
        "recommendation_reasoning": narrative.recommendation_reasoning,
        "strengths": narrative.strengths,
        "weaknesses": narrative.weaknesses,
        "hr_summary": narrative.hr_summary,
    }
