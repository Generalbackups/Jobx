# agent/models.py

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class JobPostingData:
    # Core identification
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    department: Optional[str] = None

    # Location & work arrangement
    location: Optional[str] = None
    work_type: Optional[str] = None          # "remote" | "onsite" | "hybrid"

    # Employment
    employment_type: Optional[str] = None    # "full-time" | "part-time" | "contract" | "internship"
    experience_level: Optional[str] = None   # "entry" | "mid" | "senior" | "lead" | "executive"
    experience_years_min: Optional[int] = None
    experience_years_max: Optional[int] = None

    # Compensation
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: Optional[str] = None    # e.g. "INR", "USD"
    salary_period: Optional[str] = None      # "per year" | "per month"

    # Skills
    skills_required: List[str] = field(default_factory=list)
    skills_preferred: List[str] = field(default_factory=list)

    # Content
    job_description: Optional[str] = None
    responsibilities: List[str] = field(default_factory=list)
    qualifications: List[str] = field(default_factory=list)
    benefits: List[str] = field(default_factory=list)

    # Logistics
    number_of_openings: Optional[int] = None
    application_deadline: Optional[str] = None   # ISO date string "YYYY-MM-DD"

    # Session metadata — NOT part of the job posting form, used for internal tracking only
    session_id: Optional[str] = None
    recruiter_user_id: Optional[str] = None
