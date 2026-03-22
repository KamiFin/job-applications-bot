"""Tests for the CV parser module."""

import tempfile
from pathlib import Path

from job_bot.cv_parser import parse_cv


def test_parse_txt_cv():
    """Test parsing a plain text CV."""
    cv_text = """John Doe
john.doe@example.com
+1 555-123-4567
linkedin.com/in/johndoe
github.com/johndoe

Summary
Experienced software engineer with 8 years of experience building web applications.

Skills
Python, JavaScript, TypeScript, React, Django, PostgreSQL, Docker, AWS

Experience
Senior Software Engineer
Acme Corp
January 2020 - Present
Led development of microservices platform serving 1M+ users.

Software Engineer
StartupXYZ
June 2016 - December 2019
Built and maintained full-stack web applications.

Education
MIT
B.S. Computer Science
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        f.write(cv_text)
        f.flush()

        cv = parse_cv(f.name)

    assert cv.personal.first_name == "John"
    assert cv.personal.last_name == "Doe"
    assert cv.personal.email == "john.doe@example.com"
    assert "555" in cv.personal.phone
    assert "johndoe" in cv.personal.linkedin_url
    assert "johndoe" in cv.personal.github_url
    assert cv.full_name() == "John Doe"


def test_parse_nonexistent_file():
    """Test that parsing a missing file raises an error."""
    try:
        parse_cv("/nonexistent/file.pdf")
        assert False, "Should have raised FileNotFoundError"
    except FileNotFoundError:
        pass


def test_parse_unsupported_format():
    """Test that an unsupported format raises an error."""
    with tempfile.NamedTemporaryFile(suffix=".xyz", delete=False) as f:
        try:
            parse_cv(f.name)
            assert False, "Should have raised ValueError"
        except ValueError:
            pass
