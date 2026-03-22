"""Data models for the job application bot."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class ApplicationStatus(Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUBMITTED = "submitted"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PersonalInfo:
    first_name: str = ""
    last_name: str = ""
    email: str = ""
    phone: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    zip_code: str = ""
    country: str = ""
    linkedin_url: str = ""
    github_url: str = ""
    website: str = ""


@dataclass
class WorkExperience:
    company: str = ""
    title: str = ""
    start_date: str = ""
    end_date: str = ""
    current: bool = False
    description: str = ""
    location: str = ""


@dataclass
class Education:
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_date: str = ""
    end_date: str = ""
    gpa: str = ""
    description: str = ""


@dataclass
class CVData:
    personal: PersonalInfo = field(default_factory=PersonalInfo)
    summary: str = ""
    work_experience: list[WorkExperience] = field(default_factory=list)
    education: list[Education] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    raw_text: str = ""

    def full_name(self) -> str:
        return f"{self.personal.first_name} {self.personal.last_name}".strip()


@dataclass
class JobListing:
    title: str = ""
    company: str = ""
    url: str = ""
    location: str = ""
    description: str = ""
    platform: str = ""


@dataclass
class ApplicationResult:
    job: JobListing = field(default_factory=JobListing)
    status: ApplicationStatus = ApplicationStatus.PENDING
    message: str = ""
    screenshot_path: str = ""
