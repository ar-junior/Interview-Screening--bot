from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List
import json


class SkillPlan(BaseModel):
    skill_name: str
    mandatory: bool = Field(description="Whether this skill is a mandatory requirement for the role.")


class StepPlan(BaseModel):
    step_number: int
    step_name: str
    topics: List[str]


class InterviewPlan(BaseModel):
    interview_eligible: bool
    interview_status: str
    reason: str
    total_steps: int
    step_plan: List[StepPlan]
    programming_languages: List[SkillPlan]
    libraries_frameworks: List[SkillPlan]
    tools: List[SkillPlan]
    project_topics: List[str]
    reasoning_topics: List[str]


EXPECTED_STEP_NAMES = [
    "Personal Information",
    "Programming Languages",
    "Libraries / Frameworks",
    "Tools",
    "Projects",
    "Reasoning",
]


def parse_interview_plan(resume_data: dict, jd_data: dict, matcher_data: dict) -> InterviewPlan:
    """
    Builds the 6-step interview plan and the relevant skill list per step.

    CHANGE vs. earlier versions: SkillPlan no longer carries
    basic_questions/intermediate_questions/advanced_questions/
    terminate_if_failed counts. The Easy -> Medium -> High question
    budgets and pass/fail thresholds are now fixed, deterministic rules
    owned entirely by `interview_controller.py`, not something the LLM
    estimates per skill. The planner's job is now just: which skills/
    topics are relevant, and which are mandatory.
    """
    load_dotenv()

    planner_prompt = PromptTemplate(
        template="""
You are a Senior Technical Interview Planner AI.
Your task is NOT to conduct the interview.
Your task is NOT to generate actual interview questions.
Your task is ONLY to decide which topics/skills are relevant to interview on.

INPUTS:
1. Structured Resume
{resume}
2. Structured Job Description
{jd}
3. Match Result
{matcher}

Rules:
1. If the candidate is NOT eligible for interview, return interview_eligible=False and explain the reason.
2. If the candidate IS eligible, create a structured interview plan.
3. The interview MUST follow exactly six steps, in this order:
- Personal Information
- Programming Languages
- Libraries / Frameworks
- Tools
- Projects
- Reasoning
4. Include ONLY the relevant skills/topics according to the Resume, Job Description, and Match Result.
5. Skills that are required by the job description should be marked mandatory=True.
6. Do NOT include unrelated skills.
7. Do NOT generate actual interview questions.
8. Return the output STRICTLY according to the provided schema.
""",
        input_variables=["resume", "jd", "matcher"],
    )

    llm = ChatGroq(model="openai/gpt-oss-120b")
    structured_llm = llm.with_structured_output(InterviewPlan)
    chain = planner_prompt | structured_llm

    try:
        plan = chain.invoke({
            "resume": json.dumps(resume_data, indent=2),
            "jd": json.dumps(jd_data, indent=2),
            "matcher": json.dumps(matcher_data, indent=2),
        })
    except Exception as e:
        raise RuntimeError(f"The AI model failed to generate the interview plan: {e}")

    actual_steps = [sp.step_name for sp in plan.step_plan]
    if plan.interview_eligible and actual_steps != EXPECTED_STEP_NAMES:
        print(f"[warning] Interview plan step order deviates from the required six steps: {actual_steps}")

    return plan
