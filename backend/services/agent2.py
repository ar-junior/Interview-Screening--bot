from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import os


class JobDescription(BaseModel):
    job_title: str = Field(description="Job title")
    company_name: Optional[str] = Field(default=None, description="Company name")
    location: Optional[str] = Field(default=None, description="Job location")
    job_type: Optional[str] = Field(default=None, description="Employment type")
    experience_required: Optional[str] = Field(default=None, description="Required experience")
    education_requirements: List[str] = Field(default_factory=list, description="Required education")
    required_skills: List[str] = Field(default_factory=list, description="Mandatory technical skills")
    preferred_skills: List[str] = Field(default_factory=list, description="Preferred technical skills")
    responsibilities: List[str] = Field(default_factory=list, description="Job responsibilities")
    nice_to_have: List[str] = Field(default_factory=list, description="Additional preferred qualifications")
    minimum_eligibility: List[str] = Field(default_factory=list, description="Minimum eligibility criteria")


def parse_jd(jd_path: str) -> JobDescription:
    """
    Parses a Job Description PDF into a JobDescription.

    CHANGE: the JD is now a PDF uploaded by the admin (once, shared across
    all candidates) rather than a manually-edited text file. Parsing uses
    the same PyPDFLoader + full-page-concatenation approach as Agent 1.
    """
    load_dotenv()

    if not os.path.exists(jd_path):
        raise FileNotFoundError(f"Job description PDF not found at: {jd_path}")

    try:
        loader = PyPDFLoader(jd_path)
        documents = loader.load()
    except Exception as e:
        raise RuntimeError(f"Failed to read the JD PDF at {jd_path}: {e}")

    if not documents:
        raise ValueError("The uploaded JD PDF could not be read (no pages found).")

    job_description = "\n".join(doc.page_content for doc in documents)
    if not job_description.strip():
        raise ValueError(
            "No extractable text was found in the JD PDF. It may be a scanned "
            "image without OCR text — please upload a text-based PDF."
        )

    jd_prompt = PromptTemplate(
        template="""
    You are an expert Job Description parser.

    Extract the information from the Job Description according to the provided schema.

    Rules:
    - Use only the information present in the Job Description.
    - Do not guess or invent any information.
    - If a field is missing, return null or an empty list.
    - Return information exactly according to the schema.

    Job Description:

    {job_description}
    """,
        input_variables=["job_description"],
    )

    llm = ChatGroq(model="openai/gpt-oss-120b")
    structured_llm = llm.with_structured_output(JobDescription)
    chain = jd_prompt | structured_llm

    try:
        return chain.invoke({"job_description": job_description})
    except Exception as e:
        raise RuntimeError(f"The AI model failed to parse this job description: {e}")
