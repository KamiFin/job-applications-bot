"""Tests for the form filler module."""

from job_bot.form_filler import FormField, FormFiller
from job_bot.models import CVData, PersonalInfo


def _make_cv() -> CVData:
    return CVData(
        personal=PersonalInfo(
            first_name="Jane",
            last_name="Smith",
            email="jane@example.com",
            phone="+1-555-999-0000",
            linkedin_url="linkedin.com/in/janesmith",
        ),
        summary="Senior engineer with 10 years of experience.",
        skills=["Python", "Go", "Kubernetes"],
    )


def test_match_email_field():
    filler = FormFiller(_make_cv())
    field = FormField(label="Email Address", name="email", field_type="email")
    value = filler.match_field_to_cv(field)
    assert value == "jane@example.com"


def test_match_first_name():
    filler = FormFiller(_make_cv())
    field = FormField(label="First Name", name="first_name", field_type="text")
    value = filler.match_field_to_cv(field)
    assert value == "Jane"


def test_match_last_name():
    filler = FormFiller(_make_cv())
    field = FormField(label="Last Name", name="", field_type="text")
    value = filler.match_field_to_cv(field)
    assert value == "Smith"


def test_match_phone():
    filler = FormFiller(_make_cv())
    field = FormField(label="Phone Number", name="phone", field_type="tel")
    value = filler.match_field_to_cv(field)
    assert "555" in value


def test_match_full_name():
    filler = FormFiller(_make_cv())
    field = FormField(label="Your Name", name="name", field_type="text")
    value = filler.match_field_to_cv(field)
    assert value == "Jane Smith"


def test_no_match_returns_none():
    filler = FormFiller(_make_cv())
    field = FormField(label="", name="", placeholder="", field_type="text")
    value = filler.match_field_to_cv(field)
    assert value is None
