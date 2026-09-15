from langchain_groq import ChatGroq
from langchain_community.document_loaders import PyPDFLoader
from dotenv import load_dotenv
from langchain_core.prompts import PromptTemplate
from pydantic import BaseModel, Field
from typing import List, Optional
import os


class Education(BaseModel):
    degree: str = Field(description="Degree name")
    institute: str = Field(description="College or university name")
    passing_year: Optional[str] = Field(default=None, description="Passing year if available")
    cgpa: Optional[str] = Field(default=None, description="CGPA or percentage")


class Project(BaseModel):
    title: str = Field(description="Project title")
    description: str = Field(description="Short project description")
    technologies: List[str] = Field(description="Technologies used in the project")
    role: Optional[str] = Field(default=None, description="Candidate's role in the project")


class Experience(BaseModel):
    company: str = Field(description="Company name")
    role: str = Field(description="Job role")
    duration: Optional[str] = Field(default=None, description="Duration of employment")
    description: Optional[str] = Field(default=None, description="Work summary")


class Certification(BaseModel):
    name: str = Field(description="Certification name")
    provider: Optional[str] = Field(default=None, description="Certification provider")


class StructuredResume(BaseModel):
    name: str = Field(description="Candidate full name")
    email: Optional[str] = Field(default=None, description="Candidate email")
    phone: Optional[str] = Field(default=None, description="Phone number")
    location: Optional[str] = Field(default=None, description="Current location")
    summary: Optional[str] = Field(default=None, description="Professional summary")
    technical_skills: List[str] = Field(
        description="Programming languages, frameworks, databases, libraries and tools"
    )
    soft_skills: List[str] = Field(default_factory=list, description="Soft skills mentioned in the resume")
    education: List[Education]
    experience: List[Experience] = Field(default_factory=list)
    projects: List[Project] = Field(default_factory=list)
    certifications: List[Certification] = Field(default_factory=list)
    github: Optional[str] = Field(default=None, description="GitHub profile URL")
    linkedin: Optional[str] = Field(default=None, description="LinkedIn profile URL")
    languages: List[str] = Field(default_factory=list, description="Languages known")


def parse_resume(pdf_path: str) -> StructuredResume:
    """Parses a candidate's resume PDF into a StructuredResume. All pages
    are concatenated (a multi-page resume is not truncated)."""
    load_dotenv()

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"Resume PDF not found at: {pdf_path}")

    try:
        loader = PyPDFLoader(pdf_path)
        documents = loader.load()
    except Exception as e:
        raise RuntimeError(f"Failed to read the PDF at {pdf_path}: {e}")

    if not documents:
        raise ValueError("The uploaded PDF could not be read (no pages found).")

    resume_text = "\n".join(doc.page_content for doc in documents)
    if not resume_text.strip():
        raise ValueError(
            "No extractable text was found in this PDF. It may be a scanned "
            "image without OCR text — please upload a text-based PDF."
        )

    resume_prompt = PromptTemplate(
        template="""
    You are an expert resume parser.

    Extract all information from the resume into the provided schema.

    Rules:
    - Use only the information present in the resume.
    - Do not guess or invent information.
    - If any field is missing, leave it null or an empty list.
    - Extract technical skills, projects, education, certifications, experience, contact information, and links accurately.
    - Return information exactly according to the schema.

    Resume:

    {resume}
    """,
        input_variables=["resume"],
    )

    llm = ChatGroq(model="openai/gpt-oss-120b")
    structured_llm = llm.with_structured_output(StructuredResume)
    chain = resume_prompt | structured_llm

    try:
        return chain.invoke({"resume": resume_text})
    except Exception as e:
        raise RuntimeError(f"The AI model failed to parse this resume: {e}")
