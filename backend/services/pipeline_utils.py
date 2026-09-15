"""
Pipeline helpers wiring Agents 1-4 together.

FLOW:
  Admin, once (or whenever the role/JD changes):
      parse_and_cache_jd_pdf()  -->  Agent 2 (now parses a PDF)  -->  data/jd.json

  Candidate, per resume upload:
      run_screening_pipeline()  -->  Agent 1 (resume, per-candidate folder)
                                 -->  loads the already-parsed JD (no re-run)
                                 -->  Agent 3 (match)
                                 -->  Agent 4 (plan) — only if eligible
"""

import json
import os

from backend.services.agent1 import parse_resume
from backend.services.agent2 import parse_jd
from backend.services.agent3 import parse_matcher
from backend.services.agent4 import parse_interview_plan

JD_PDF_PATH = "data/jd.pdf"
JD_JSON_PATH = "data/jd.json"


def candidate_dir(candidate_id: str) -> str:
    path = f"data/candidates/{candidate_id}"
    os.makedirs(path, exist_ok=True)
    return path


def save_uploaded_resume(candidate_id: str, pdf_bytes: bytes, filename: str) -> str:
    path = os.path.join(candidate_dir(candidate_id), "resume.pdf")
    with open(path, "wb") as f:
        f.write(pdf_bytes)
    return path


def parse_and_cache_jd_pdf(pdf_bytes: bytes, filename: str) -> dict:
    """Admin-side: run once whenever the JD PDF is uploaded/changed."""
    os.makedirs("data", exist_ok=True)
    with open(JD_PDF_PATH, "wb") as f:
        f.write(pdf_bytes)

    jd_obj = parse_jd(JD_PDF_PATH)
    jd = json.loads(jd_obj.model_dump_json())
    with open(JD_JSON_PATH, "w", encoding="utf-8") as f:
        json.dump(jd, f, indent=2)
    return jd


def jd_is_ready() -> bool:
    return os.path.exists(JD_JSON_PATH)


def run_screening_pipeline(candidate_id: str, pdf_path: str):
    """
    Runs Agents 1, 3, 4 for one candidate (Agent 2/JD is NOT re-run here).

    Returns (resume, jd, matcher, interview_plan) as plain dicts, and
    persists them under data/candidates/{candidate_id}/.
    """
    if not jd_is_ready():
        raise RuntimeError("The job description hasn't been uploaded by the admin yet.")
    with open(JD_JSON_PATH, "r", encoding="utf-8") as f:
        jd = json.load(f)

    base = candidate_dir(candidate_id)

    resume_obj = parse_resume(pdf_path)
    resume = json.loads(resume_obj.model_dump_json())
    with open(f"{base}/resume.json", "w", encoding="utf-8") as f:
        json.dump(resume, f, indent=2)

    matcher_obj = parse_matcher(resume_data=resume, jd_data=jd)
    matcher = json.loads(matcher_obj.model_dump_json())
    with open(f"{base}/matcher.json", "w", encoding="utf-8") as f:
        json.dump(matcher, f, indent=2)

    interview_plan = {"interview_eligible": False, "reason": "Not eligible based on requirement match."}
    if matcher["interview_eligible"]:
        plan_obj = parse_interview_plan(resume_data=resume, jd_data=jd, matcher_data=matcher)
        interview_plan = json.loads(plan_obj.model_dump_json())
    with open(f"{base}/planner.json", "w", encoding="utf-8") as f:
        json.dump(interview_plan, f, indent=2)

    return resume, jd, matcher, interview_plan
