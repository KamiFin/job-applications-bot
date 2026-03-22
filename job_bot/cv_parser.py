"""CV/Resume parser supporting PDF and DOCX formats."""

from __future__ import annotations

import re
from pathlib import Path

from job_bot.models import CVData, Education, PersonalInfo, WorkExperience


def parse_cv(file_path: str) -> CVData:
    """Parse a CV file (PDF or DOCX) into structured data."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"CV file not found: {file_path}")

    suffix = path.suffix.lower()
    if suffix == ".pdf":
        text = _extract_pdf_text(path)
    elif suffix in (".docx", ".doc"):
        text = _extract_docx_text(path)
    elif suffix == ".txt":
        text = path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file format: {suffix}. Use PDF, DOCX, or TXT.")

    return _parse_text_to_cv(text)


def _extract_pdf_text(path: Path) -> str:
    """Extract text from a PDF file."""
    import pdfplumber

    text_parts = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text_parts.append(page_text)
    return "\n".join(text_parts)


def _extract_docx_text(path: Path) -> str:
    """Extract text from a DOCX file."""
    from docx import Document

    doc = Document(str(path))
    return "\n".join(para.text for para in doc.paragraphs if para.text.strip())


def _parse_text_to_cv(text: str) -> CVData:
    """Parse raw text into structured CV data using heuristics."""
    cv = CVData(raw_text=text)
    lines = [line.strip() for line in text.split("\n") if line.strip()]

    cv.personal = _extract_personal_info(lines, text)
    cv.skills = _extract_skills(text)
    cv.work_experience = _extract_work_experience(text)
    cv.education = _extract_education(text)
    cv.summary = _extract_summary(text)

    return cv


def _extract_personal_info(lines: list[str], text: str) -> PersonalInfo:
    """Extract personal information from CV text."""
    info = PersonalInfo()

    # Name is typically the first non-empty line
    if lines:
        name_parts = lines[0].split()
        if 1 < len(name_parts) <= 4:
            info.first_name = name_parts[0]
            info.last_name = " ".join(name_parts[1:])

    # Email
    email_match = re.search(r"[\w.+-]+@[\w-]+\.[\w.-]+", text)
    if email_match:
        info.email = email_match.group()

    # Phone
    phone_match = re.search(r"[\+]?[\d\s\-\(\)]{7,15}", text)
    if phone_match:
        info.phone = phone_match.group().strip()

    # LinkedIn
    linkedin_match = re.search(r"(?:https?://)?(?:www\.)?linkedin\.com/in/[\w-]+", text)
    if linkedin_match:
        info.linkedin_url = linkedin_match.group()

    # GitHub
    github_match = re.search(r"(?:https?://)?(?:www\.)?github\.com/[\w-]+", text)
    if github_match:
        info.github_url = github_match.group()

    return info


def _extract_skills(text: str) -> list[str]:
    """Extract skills from the CV text."""
    skills_section = re.search(
        r"(?:skills|technical skills|technologies|competencies)[:\s]*\n(.*?)(?:\n\n|\n[A-Z])",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not skills_section:
        return []

    skills_text = skills_section.group(1)
    # Split by common delimiters
    raw_skills = re.split(r"[,;|•·\n]", skills_text)
    return [s.strip().strip("-").strip() for s in raw_skills if s.strip() and len(s.strip()) < 50]


def _extract_work_experience(text: str) -> list[WorkExperience]:
    """Extract work experience entries."""
    section = re.search(
        r"(?:experience|work history|employment)[:\s]*\n(.*?)(?:\n(?:education|skills|certifications|projects)|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        return []

    entries = []
    # Split by date patterns that typically start new entries
    blocks = re.split(r"\n(?=\w.*(?:\d{4}|\bpresent\b))", section.group(1), flags=re.IGNORECASE)

    for block in blocks:
        if not block.strip():
            continue
        exp = WorkExperience()
        block_lines = [l.strip() for l in block.split("\n") if l.strip()]
        if block_lines:
            exp.title = block_lines[0]
        if len(block_lines) > 1:
            exp.company = block_lines[1]
        if len(block_lines) > 2:
            exp.description = "\n".join(block_lines[2:])
        date_match = re.search(r"(\w+\s+\d{4})\s*[-–]\s*(\w+\s+\d{4}|present)", block, re.I)
        if date_match:
            exp.start_date = date_match.group(1)
            exp.end_date = date_match.group(2)
            exp.current = "present" in exp.end_date.lower()
        entries.append(exp)

    return entries


def _extract_education(text: str) -> list[Education]:
    """Extract education entries."""
    section = re.search(
        r"(?:education)[:\s]*\n(.*?)(?:\n(?:experience|skills|certifications|projects)|$)",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if not section:
        return []

    entries = []
    blocks = re.split(r"\n(?=\w)", section.group(1))

    for block in blocks:
        if not block.strip():
            continue
        edu = Education()
        block_lines = [l.strip() for l in block.split("\n") if l.strip()]
        if block_lines:
            edu.institution = block_lines[0]
        if len(block_lines) > 1:
            edu.degree = block_lines[1]
        entries.append(edu)

    return entries


def _extract_summary(text: str) -> str:
    """Extract professional summary."""
    summary_match = re.search(
        r"(?:summary|profile|about|objective)[:\s]*\n(.*?)(?:\n\n|\n[A-Z])",
        text,
        re.IGNORECASE | re.DOTALL,
    )
    if summary_match:
        return summary_match.group(1).strip()
    return ""
