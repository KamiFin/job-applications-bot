"""Intelligent form detection and filling engine."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from playwright.async_api import Page

from job_bot.models import CVData

logger = logging.getLogger(__name__)


@dataclass
class FormField:
    """Represents a detected form field."""

    selector: str = ""
    field_type: str = ""
    label: str = ""
    name: str = ""
    placeholder: str = ""
    required: bool = False
    options: list[str] = field(default_factory=list)


FIELD_MAPPING = {
    r"first.?name": "personal.first_name",
    r"last.?name|surname|family.?name": "personal.last_name",
    r"full.?name|your.?name|^name$": "full_name",
    r"e?.?mail": "personal.email",
    r"phone|mobile|tel": "personal.phone",
    r"address|street": "personal.address",
    r"city|town": "personal.city",
    r"state|province|region": "personal.state",
    r"zip|postal": "personal.zip_code",
    r"country": "personal.country",
    r"linkedin": "personal.linkedin_url",
    r"github": "personal.github_url",
    r"website|portfolio|url": "personal.website",
    r"summary|cover.?letter|about|motivation|why.?apply": "summary",
    r"current.?title|job.?title|position": "current_title",
    r"current.?company|employer": "current_company",
    r"salary|compensation|expected.?pay": None,
    r"years?.?(?:of)?.?experience": "years_experience",
}


class FormFiller:
    """Detects and fills web forms with CV data."""

    def __init__(self, cv: CVData):
        self.cv = cv

    async def detect_fields(self, page: Page) -> list[FormField]:
        """Detect all fillable form fields on the page."""
        fields = await page.evaluate("""() => {
            const fields = [];
            const inputs = document.querySelectorAll(
                'input:not([type="hidden"]):not([type="submit"]):not([type="button"]), ' +
                'textarea, select'
            );

            for (const el of inputs) {
                // Find associated label
                let label = '';
                if (el.id) {
                    const labelEl = document.querySelector(`label[for="${el.id}"]`);
                    if (labelEl) label = labelEl.innerText.trim();
                }
                if (!label) {
                    const parent = el.closest('label, .form-group, .field, [class*="field"]');
                    if (parent) {
                        const labelEl = parent.querySelector('label, .label, [class*="label"]');
                        if (labelEl) label = labelEl.innerText.trim();
                    }
                }

                // Get options for select elements
                const options = [];
                if (el.tagName === 'SELECT') {
                    for (const opt of el.options) {
                        if (opt.value) options.push(opt.value);
                    }
                }

                // Build a robust selector
                let selector = '';
                if (el.id) {
                    selector = `#${el.id}`;
                } else if (el.name) {
                    selector = `[name="${el.name}"]`;
                } else {
                    // Use nth-of-type as fallback
                    const siblings = el.parentElement.querySelectorAll(el.tagName);
                    const idx = Array.from(siblings).indexOf(el);
                    selector = `${el.tagName.toLowerCase()}:nth-of-type(${idx + 1})`;
                }

                fields.push({
                    selector: selector,
                    field_type: el.type || el.tagName.toLowerCase(),
                    label: label,
                    name: el.name || '',
                    placeholder: el.placeholder || '',
                    required: el.required,
                    options: options,
                });
            }
            return fields;
        }""")

        return [FormField(**f) for f in fields]

    def match_field_to_cv(self, form_field: FormField) -> str | None:
        """Match a form field to the appropriate CV data using label/name/placeholder."""
        search_text = " ".join([
            form_field.label,
            form_field.name,
            form_field.placeholder,
        ]).lower()

        if not search_text.strip():
            return None

        for pattern, cv_path in FIELD_MAPPING.items():
            if re.search(pattern, search_text, re.IGNORECASE):
                if cv_path is None:
                    return None
                return self._resolve_cv_value(cv_path)

        return None

    def _resolve_cv_value(self, path: str) -> str | None:
        """Resolve a dotted path to a CV data value."""
        if path == "full_name":
            return self.cv.full_name()
        if path == "summary":
            return self.cv.summary
        if path == "current_title":
            if self.cv.work_experience:
                return self.cv.work_experience[0].title
            return None
        if path == "current_company":
            if self.cv.work_experience:
                return self.cv.work_experience[0].company
            return None
        if path == "years_experience":
            return str(len(self.cv.work_experience)) if self.cv.work_experience else None

        # Handle dotted paths like "personal.first_name"
        parts = path.split(".")
        obj = self.cv
        for part in parts:
            obj = getattr(obj, part, None)
            if obj is None:
                return None
        return str(obj) if obj else None

    async def fill_form(self, page: Page, cv_file_path: str | None = None) -> dict:
        """Detect and fill all form fields on the page.

        Returns a dict with counts of filled, skipped, and failed fields.
        """
        fields = await self.detect_fields(page)
        results = {"filled": 0, "skipped": 0, "failed": 0, "details": []}

        for form_field in fields:
            # Handle file upload fields (resume/CV upload)
            if form_field.field_type == "file" and cv_file_path:
                try:
                    await page.set_input_files(form_field.selector, cv_file_path)
                    results["filled"] += 1
                    results["details"].append(
                        {"field": form_field.label or form_field.name, "action": "uploaded_cv"}
                    )
                    logger.info("Uploaded CV to %s", form_field.label or form_field.selector)
                    continue
                except Exception as e:
                    logger.warning("Failed to upload CV: %s", e)
                    results["failed"] += 1
                    continue

            value = self.match_field_to_cv(form_field)
            if not value:
                results["skipped"] += 1
                logger.debug(
                    "Skipped field: %s", form_field.label or form_field.name or form_field.selector
                )
                continue

            try:
                if form_field.field_type == "select":
                    await self._fill_select(page, form_field, value)
                else:
                    await page.fill(form_field.selector, value)

                results["filled"] += 1
                results["details"].append({
                    "field": form_field.label or form_field.name,
                    "value": value[:50],
                })
                logger.info(
                    "Filled '%s' with '%s'",
                    form_field.label or form_field.name,
                    value[:30],
                )
            except Exception as e:
                results["failed"] += 1
                logger.warning(
                    "Failed to fill %s: %s", form_field.label or form_field.selector, e
                )

        return results

    async def _fill_select(self, page: Page, form_field: FormField, value: str) -> None:
        """Fill a select dropdown, matching the closest option."""
        value_lower = value.lower()
        best_match = None
        for option in form_field.options:
            if option.lower() == value_lower:
                best_match = option
                break
            if value_lower in option.lower() or option.lower() in value_lower:
                best_match = option

        if best_match:
            await page.select_option(form_field.selector, best_match)
        else:
                if form_field.options:
                await page.select_option(form_field.selector, form_field.options[0])
