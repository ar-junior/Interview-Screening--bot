from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import json


class MatchResult(BaseModel):
    requirement_match_score: float = Field(description="Overall requirement match score between 0 and 100.")
    matched_skills: List[str] = Field(default_factory=list, description="Skills present in both the resume and the job description.")
    missing_required_skills: List[str] = Field(default_factory=list, description="Required skills from the job description that are missing in the resume.")
    matched_preferred_skills: List[str] = Field(default_factory=list, description="Preferred skills that are also present in the resume.")
    strengths: List[str] = Field(default_factory=list, description="Major strengths of the candidate for this job.")
    weaknesses: List[str] = Field(default_factory=list, description="Major weaknesses or gaps for this job.")
    interview_eligible: bool = Field(description="Whether the candidate should proceed to the AI interview.")
    recommendation: str = Field(description="Short recommendation such as Strong Match, Moderate Match, or Weak Match.")
    reason: str = Field(description="Brief explanation supporting the recommendation.")


def parse_matcher(
    resume_data: dict,
    jd_data: dict,
    eligibility_floor: float = 30.0,
) -> MatchResult:
    """
    Compares a structured resume against the structured JD. A candidate
    with requirement_match_score below `eligibility_floor` is forced
    ineligible regardless of the LLM's own eligibility call, as a
    deterministic safety net — this is what drives the "Disqualified"
    status on the candidate route.
    """
    load_dotenv()

    matcher_prompt = PromptTemplate(
        template="""
    You are an experienced technical recruiter.
    Your task is to compare the candidate's structured resume with the structured job description.

    Rules:
    - Compare only the provided information.
    - Do not assume or invent information.
    - Match skills semantically when appropriate (for example, Git may satisfy part of "Git and GitHub", but do not over-match unrelated skills).
    - Distinguish technical skills from soft skills.
    - Use projects, education and experience as supporting evidence.
    - Base the requirement_match_score primarily on required skills.
    - Return the output exactly according to the provided schema.

    Structured Resume
    {resume}
    Structured Job Description:
    {job_description}
    """,
        input_variables=["resume", "job_description"],
    )

    llm = ChatGroq(model="openai/gpt-oss-120b")
    structured_llm = llm.with_structured_output(MatchResult)
    chain = matcher_prompt | structured_llm

    try:
        structured_matcher = chain.invoke(
            {"job_description": json.dumps(jd_data, indent=2), "resume": json.dumps(resume_data, indent=2)}
        )
    except Exception as e:
        raise RuntimeError(f"The AI model failed to compute the requirement match: {e}")

    if structured_matcher.requirement_match_score < eligibility_floor:
        structured_matcher.interview_eligible = False

    return structured_matcher
