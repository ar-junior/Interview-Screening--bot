from langchain_groq import ChatGroq
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import Optional
import json


class EvaluationReport(BaseModel):
    relevant_answer: bool = Field(description="Whether the candidate answered the asked question.")
    technically_correct: bool = Field(description="Whether the answer is technically correct.")
    logically_correct: bool = Field(description="Whether the answer is logically correct.")
    offensive_language: bool = Field(description="Whether the answer contains offensive or inappropriate language.")
    need_warning: bool = Field(description="Whether the candidate should receive a warning.")
    confidence_score: float = Field(description="Confidence score between 0 and 100.")
    answer_quality: str = Field(description="Excellent, Good, Average, Poor etc.")
    evaluation_summary: str = Field(description="Short summary of the answer evaluation.")


def evaluate_answer(
    question: str,
    answer: str,
    resume: dict,
    jd: dict,
    matcher: dict,
    interview_plan: dict,
) -> EvaluationReport:
    """
    Evaluates a single candidate answer for relevance, technical
    correctness, and logical correctness. The interview_controller uses
    technically_correct + logically_correct together to classify each
    answer as correct / partial / wrong, which drives the Easy->Medium->
    High tier engine.
    """
    load_dotenv()

    if not answer or not answer.strip():
        return EvaluationReport(
            relevant_answer=False, technically_correct=False, logically_correct=False,
            offensive_language=False, need_warning=False, confidence_score=0,
            answer_quality="Poor", evaluation_summary="No answer was provided.",
        )

    evaluator_prompt = PromptTemplate(
        template="""
You are a Senior Technical Interview Answer Evaluator AI.
Your task is ONLY to evaluate the candidate's answer — you never conduct
the interview, ask questions, or decide what happens next.

Structured Resume:
{resume}

Structured Job Description:
{jd}

Match Result:
{matcher}

Current Interview Question:
{question}

Candidate Answer:
{answer}

YOUR RESPONSIBILITIES:
1. Determine if the answer is relevant to the question asked.
2. Determine if the answer is technically correct.
3. Determine if the answer is logically correct/coherent.
4. Detect offensive or inappropriate language.
5. Generate a confidence score (0-100) reflecting how well-reasoned and
   clear the answer is.
6. Write a short evaluation summary.

RULES:
- Be strict but fair.
- If the answer is completely unrelated to the question, mark relevant_answer=False.
- A partially correct answer should have EITHER technically_correct OR
  logically_correct set True, not both, and not neither.
- If offensive language is detected, set need_warning=True.

Return the output STRICTLY according to the provided schema.
""",
        input_variables=["resume", "jd", "matcher", "question", "answer"],
    )

    llm = ChatGroq(model="openai/gpt-oss-120b")
    structured_llm = llm.with_structured_output(EvaluationReport)
    chain = evaluator_prompt | structured_llm

    return chain.invoke({
        "resume": json.dumps(resume, indent=2),
        "jd": json.dumps(jd, indent=2),
        "matcher": json.dumps(matcher, indent=2),
        "question": question,
        "answer": answer,
    })
