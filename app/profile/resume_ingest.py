import json
import re

from app.llm.lmstudio_client import LMStudioClient
from app.models.candidate import (
    CandidateProfile,
    Education,
    Experience,
    Project,
)
from app.profile.resume_parse_agent import ResumeParseAgent
from app.resume.source_document import extract_contact


MONTHS = {
    "jan": "01",
    "january": "01",
    "feb": "02",
    "february": "02",
    "mar": "03",
    "march": "03",
    "apr": "04",
    "april": "04",
    "may": "05",
    "jun": "06",
    "june": "06",
    "jul": "07",
    "july": "07",
    "aug": "08",
    "august": "08",
    "sep": "09",
    "sept": "09",
    "september": "09",
    "oct": "10",
    "october": "10",
    "nov": "11",
    "november": "11",
    "dec": "12",
    "december": "12",
}

MONTH_RE = (
    r"(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|"
    r"Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|"
    r"Aug(?:ust)?|Sep(?:t(?:ember)?)?|"
    r"Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)"
)

DATE_RANGE_RE = re.compile(
    rf"({MONTH_RE})\s+(\d{{4}})\s*[–\-—to]+\s*"
    rf"(present|current|{MONTH_RE}\s+\d{{4}})",
    re.I,
)

SECTION_RE = re.compile(
    r"^(professional\s+experience|work\s+experience|"
    r"experience|education|technical\s+skills|"
    r"skills|additional\s+information|"
    r"projects?|ai\s*/.+\bproject\b|"
    r"certifications?|languages)\s*$",
    re.I,
)

BULLET_RE = re.compile(
    r"^[\u2022\u25cf\u25a0\u25e6\u2013\u2014\-\*\uf0b7]\s*",
)

ROLE_HINT_RE = re.compile(
    r"\b(engineer|developer|associate|analyst|intern|"
    r"consultant|manager|scientist|specialist)\b",
    re.I,
)

FAKE_NAME_RE = re.compile(
    r"^(extract_|parse_|get_|resume_)",
    re.I,
)

VALID_FACT_KEYS = {
    "name",
    "email",
    "phone",
    "location",
    "linkedin",
            "github",
            "headline",
            "skills",
            "experience",
            "education",
            "summary",
            "certifications",
            "languages",
            "interests",
            "projects",
        }


class ResumeIngestor:

    def __init__(
        self,
        llm: LMStudioClient | None = None,
    ):
        self.llm = llm or LMStudioClient()
        self.agent = ResumeParseAgent(self.llm)

    def parse_text(self, text: str) -> dict:

        extracted = self._llm_extract(text)

        if extracted and ResumeParseAgent._usable(extracted):
            return self._fill_contact(extracted, text)

        if extracted is None:
            return self._heuristic_parse(text)

        return self._fill_contact(extracted, text)

    def to_profile(
        self,
        facts: dict,
        existing: CandidateProfile | None = None,
    ) -> CandidateProfile:

        experiences = [
            Experience(
                company=str(item.get("company") or ""),
                role=str(
                    item.get("title")
                    or item.get("role")
                    or ""
                ),
                start_date=item.get("start_date") or None,
                end_date=item.get("end_date") or None,
                description=list(
                    item.get("bullets")
                    or item.get("description")
                    or []
                ),
                technologies=list(
                    item.get("technologies") or []
                ),
            )
            for item in (
                ResumeParseAgent._repair_job(
                    {
                        "company": str(
                            item.get("company") or ""
                        ),
                        "title": str(
                            item.get("title")
                            or item.get("role")
                            or ""
                        ),
                        "start_date": item.get("start_date")
                        or "",
                        "end_date": item.get("end_date")
                        or "",
                        "bullets": list(
                            item.get("bullets")
                            or item.get("description")
                            or []
                        ),
                    }
                )
                for item in facts.get("experience") or []
                if isinstance(item, dict)
            )
            if item.get("company") or item.get("title")
        ]
        experiences = [
            item
            for item in experiences
            if not ResumeIngestor._is_bullet(item.company)
            and not ResumeIngestor._is_bullet(item.role)
            and len(item.company) < 80
        ]

        projects = []

        for item in facts.get("projects") or []:
            if not isinstance(item, dict):
                continue

            bullets = item.get("bullets") or []
            description = item.get("description") or ""

            if isinstance(description, list):
                bullets = description
                description = ""

            projects.append(
                Project(
                    name=str(item.get("name") or "Project"),
                    description=(
                        " ".join(bullets)
                        if bullets
                        else str(description)
                    ),
                    technologies=list(
                        item.get("technologies") or []
                    ),
                )
            )

        education = [
            Education(
                degree=str(
                    item.get("degree")
                    or item.get("field_of_study")
                    or ""
                ),
                institution=str(
                    item.get("institution") or ""
                ),
                year=str(
                    item.get("end_date")
                    or item.get("year")
                    or ""
                ) or None,
            )
            for item in facts.get("education") or []
            if isinstance(item, dict)
            and (
                item.get("degree")
                or item.get("institution")
            )
        ]

        location = str(facts.get("location") or "")

        if re.search(
            r"engineer|python|embedded|automation",
            location,
            re.I,
        ):
            location = ""

        preferred = (
            [location]
            if location
            else [
                item
                for item in (
                    existing.preferred_locations
                    if existing
                    else []
                )
                if not re.search(
                    r"engineer|python|embedded|automation",
                    item,
                    re.I,
                )
            ]
        )

        base = existing.model_dump() if existing else {}

        headline = facts.get("headline") or base.get("headline") or ""

        if re.search(r"cgpa|pcmb|institute|college", headline, re.I):
            headline = ""

        base.update(
            {
                "name": facts.get("name") or base.get("name") or "",
                "email": facts.get("email") or base.get("email"),
                "phone": facts.get("phone") or base.get("phone"),
                "linkedin": facts.get("linkedin")
                or base.get("linkedin"),
                "github": facts.get("github")
                or base.get("github"),
                "headline": headline,
                "languages": facts.get("languages")
                or base.get("languages")
                or [],
                "interests": facts.get("interests")
                or base.get("interests")
                or [],
                "skills": facts.get("skills")
                or base.get("skills")
                or [],
                "experiences": [
                    item.model_dump()
                    for item in experiences
                ]
                or base.get("experiences")
                or [],
                "education": [
                    item.model_dump()
                    for item in education
                ]
                or base.get("education")
                or [],
                "projects": [
                    item.model_dump()
                    for item in projects
                ]
                or base.get("projects")
                or [],
                "preferred_locations": preferred
                or base.get("preferred_locations")
                or [],
            }
        )

        if facts.get("summary"):
            base["professional_summary"] = facts["summary"]
        elif not base.get("professional_summary"):
            base["professional_summary"] = ""

        if facts.get("certifications"):
            base["certifications"] = list(
                facts["certifications"]
            )

        if not base.get("name"):
            raise ValueError(
                "Could not extract a name from the resume."
            )

        return CandidateProfile.model_validate(base)

    def _heuristic_parse(self, text: str) -> dict:

        facts = self._empty()
        contact = extract_contact(text)
        facts.update(
            {
                key: value
                for key, value in contact.items()
                if value
            }
        )
        facts["name"] = self._guess_name(text)
        extra = self._parse_extra(text)
        facts.update(
            {
                key: value
                for key, value in extra.items()
                if value
            }
        )
        sections = self._split_sections(text)
        facts["experience"] = [
            ResumeParseAgent._repair_job(job)
            for job in self._parse_experience(
                sections.get("experience", "")
            )
        ]
        facts["projects"] = self._parse_projects(
            sections.get("projects", "")
        )
        facts["education"] = self._parse_education(
            sections.get("education", "")
        )
        facts["skills"] = self._parse_skills(
            sections.get("skills", "")
            or text
        )
        facts["certifications"] = self._parse_certs(
            sections.get("certifications", "")
        )
        return facts

    @staticmethod
    def _complete_from_heuristic(
        facts: dict,
        heuristic: dict,
    ) -> dict:

        for key in (
            "headline",
            "location",
            "summary",
            "linkedin",
            "github",
        ):
            if heuristic.get(key) and not facts.get(key):
                facts[key] = heuristic[key]

        for key in ("languages", "interests"):
            if heuristic.get(key) and not facts.get(key):
                facts[key] = heuristic[key]

        facts["experience"] = [
            ResumeParseAgent._repair_job(job)
            for job in facts.get("experience") or []
        ]

        if ResumeIngestor._jobs_look_broken(
            facts.get("experience") or []
        ) and heuristic.get("experience"):
            facts["experience"] = heuristic["experience"]

        if (
            heuristic.get("projects")
            and not facts.get("projects")
        ):
            facts["projects"] = heuristic["projects"]

        heuristic_edu = heuristic.get("education") or []
        current_edu = facts.get("education") or []

        if len(heuristic_edu) > len(current_edu):
            facts["education"] = heuristic_edu

        if (
            heuristic.get("certifications")
            and not facts.get("certifications")
        ):
            facts["certifications"] = heuristic[
                "certifications"
            ]

        return facts

    def _llm_extract(self, text: str) -> dict | None:

        return self.agent.extract(text)

    @staticmethod
    def _fill_contact(facts: dict, text: str) -> dict:

        contact = extract_contact(text)

        for key, value in contact.items():
            if value and not facts.get(key):
                facts[key] = value

        if not facts.get("name") or ResumeParseAgent._is_fake_name(
            facts.get("name")
        ):
            facts["name"] = ResumeIngestor._guess_name(text)

        return facts

    @staticmethod
    def _extraction_prompt() -> str:

        return """
You are a resume information extraction engine.

Your ONLY task is to extract information from the supplied
resume text.

IMPORTANT:
- Do NOT generate a function call.
- Do NOT generate a tool call.
- Do NOT generate fields named "parameters".
- Do NOT generate a field named "resume_text".
- Do NOT output "extract_skills".
- Do NOT output "extract_experience".
- Do NOT output "extract_education".
- Do NOT output "extract_resume_facts".
- Return the actual extracted resume data.

Return ONLY valid JSON.

Use EXACTLY this structure:

{
  "name": "",
  "email": "",
  "phone": "",
  "location": "",
  "linkedin": "",
  "github": "",
  "skills": [],
  "experience": [
    {
      "company": "",
      "title": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "employment_type": "",
      "bullets": []
    }
  ],
  "education": [
    {
      "degree": "",
      "field_of_study": "",
      "institution": "",
      "location": "",
      "start_date": "",
      "end_date": "",
      "grade": ""
    }
  ]
}

STRICT RULES:

1. Extract ONLY information explicitly present in the resume.
2. Never invent information.
3. Never infer missing companies, titles, dates, skills or degrees.
4. If a field is not present, return an empty string.
5. If a list has no entries, return [].
6. Preserve the relationship between employer, job title, dates and bullets.
7. Keep every meaningful professional experience entry.
8. Keep all meaningful technical skills explicitly listed.
9. Keep formal education separate from certifications.
10. Do not put certifications inside education.
11. Do not put interests inside skills unless they are explicitly technical skills.
12. Preserve technology names exactly where practical:
    C++, C#, .NET, Ada95, VxWorks, RTOS, Node.js,
    MongoDB, Docker, Jenkins, Git, Python, etc.
13. Return JSON only.
"""

    @staticmethod
    def _normalize_extracted(extracted: dict) -> dict:

        facts = ResumeIngestor._empty()

        for key in (
            "name",
            "email",
            "phone",
            "location",
            "linkedin",
            "github",
        ):
            facts[key] = str(extracted.get(key) or "").strip()

        skills = extracted.get("skills") or []

        if isinstance(skills, str):
            skills = [skills]

        facts["skills"] = [
            item.strip()
            for item in skills
            if isinstance(item, str) and item.strip()
        ]

        experience = extracted.get("experience") or []

        if isinstance(experience, list):
            facts["experience"] = [
                {
                    "company": str(item.get("company") or "").strip(),
                    "title": str(
                        item.get("title")
                        or item.get("role")
                        or ""
                    ).strip(),
                    "start_date": str(
                        item.get("start_date") or ""
                    ).strip(),
                    "end_date": str(
                        item.get("end_date") or ""
                    ).strip(),
                    "bullets": [
                        bullet.strip()
                        for bullet in (
                            item.get("bullets")
                            or item.get("description")
                            or []
                        )
                        if isinstance(bullet, str) and bullet.strip()
                    ],
                }
                for item in experience
                if isinstance(item, dict)
            ]

        education = extracted.get("education") or []

        if isinstance(education, list):
            facts["education"] = [
                {
                    "degree": str(
                        item.get("degree")
                        or item.get("field_of_study")
                        or ""
                    ).strip(),
                    "institution": str(
                        item.get("institution") or ""
                    ).strip(),
                    "year": str(
                        item.get("end_date")
                        or item.get("year")
                        or ""
                    ).strip(),
                }
                for item in education
                if isinstance(item, dict)
            ]

        return facts

    @classmethod
    def _parse_llm_json(cls, raw: str) -> dict | None:

        if not raw or not raw.strip():
            return None

        text = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            raw.strip(),
            flags=re.I,
        )
        text = re.sub(r"\s*```\s*$", "", text).strip()

        candidates = []

        try:
            loaded = json.loads(text)
            if isinstance(loaded, dict):
                candidates.append(loaded)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()

            for match in re.finditer(r"\{", text):
                try:
                    obj, _ = decoder.raw_decode(
                        text[match.start():]
                    )
                    if isinstance(obj, dict):
                        candidates.append(obj)
                        break
                except json.JSONDecodeError:
                    continue

        for parsed in candidates:
            cleaned = cls._normalize_llm_output(parsed)

            if cleaned:
                return cleaned

        return None

    @staticmethod
    def _normalize_llm_output(parsed: dict) -> dict | None:

        name = str(parsed.get("name") or "")

        if "parameters" in parsed or "resume_text" in parsed:
            return None

        if FAKE_NAME_RE.match(name) or name in {
            "extract_resume",
            "extract_contact",
            "extract_skills",
            "extract_experience",
            "extract_education",
            "extract_resume_facts",
            "parse_resume",
            "parse_document",
        }:
            return None

        if not any(key in parsed for key in VALID_FACT_KEYS):
            return None

        return {
            key: value
            for key, value in parsed.items()
            if key in VALID_FACT_KEYS
        }

    @staticmethod
    def _empty() -> dict:

        return {
            "name": "",
            "email": "",
            "phone": "",
            "location": "",
            "linkedin": "",
            "github": "",
            "headline": "",
            "summary": "",
            "skills": [],
            "languages": [],
            "interests": [],
            "experience": [],
            "education": [],
            "projects": [],
        }

    @staticmethod
    def _merge_facts(
        base: dict,
        extracted: dict,
    ) -> dict:

        merged = dict(base)

        for key, value in extracted.items():
            if key not in VALID_FACT_KEYS:
                continue

            if value in (None, "", [], {}):
                continue

            if key == "name" and (
                FAKE_NAME_RE.match(str(value))
                or "_" in str(value)
            ):
                continue

            if key in {"skills", "experience", "education"}:
                current = merged.get(key) or []

                if (
                    isinstance(value, list)
                    and len(value) >= len(current)
                ):
                    merged[key] = value
                continue

            merged[key] = value

        if isinstance(extracted.get("skills"), list) and merged.get("skills"):
            merged["skills"] = list(
                dict.fromkeys(
                    list(merged["skills"])
                    + [
                        item.strip()
                        for item in extracted["skills"]
                        if isinstance(item, str) and item.strip()
                    ]
                )
            )

        return merged

    @staticmethod
    def _split_sections(text: str) -> dict[str, str]:

        lines = text.replace("\r\n", "\n").splitlines()
        buckets = {
            "header": [],
            "experience": [],
            "education": [],
            "skills": [],
            "certifications": [],
            "projects": [],
            "other": [],
        }
        current = "header"

        for line in lines:
            heading = SECTION_RE.match(line.strip())

            if heading:
                label = heading.group(1).lower()

                if "experience" in label:
                    current = "experience"
                elif "education" in label:
                    current = "education"
                elif "skill" in label:
                    current = "skills"
                elif "project" in label:
                    current = "projects"
                    buckets[current].append(line.strip())
                    continue
                elif "certification" in label:
                    current = "certifications"
                else:
                    current = "other"
                continue

            buckets[current].append(line)

        return {
            key: "\n".join(value)
            for key, value in buckets.items()
        }

    @classmethod
    def _parse_experience(cls, text: str) -> list[dict]:

        text = cls._join_wrapped_headers(text)

        jobs: list[dict] = []
        current: dict | None = None

        for raw in text.splitlines():
            line = raw.strip()

            if not line or cls._is_page_noise(line):
                continue

            if cls._is_bullet(line):
                if current is None:
                    continue

                current["bullets"].append(
                    cls._strip_bullet(line)
                )
                continue

            date_match = DATE_RANGE_RE.search(line)

            if date_match:
                start, end = cls._normalize_dates(date_match)
                remainder = DATE_RANGE_RE.sub(
                    "",
                    line,
                ).strip(" -,|()")

                if current is None:
                    current = cls._new_job()
                    jobs.append(current)

                current["start_date"] = start
                current["end_date"] = end

                if remainder:
                    company, role = cls._split_company_role(
                        remainder
                    )
                    if company:
                        current["company"] = company
                    if role:
                        current["title"] = cls._clean_title(
                            role
                        )
                continue

            if current and current.get("bullets"):
                last = current["bullets"][-1]

                if cls._is_wrapped_line(line, last):
                    current["bullets"][-1] = (
                        last + " " + line
                    ).strip()
                    continue

            if cls._is_job_header(line):
                if (
                    current
                    and not current.get("bullets")
                    and not current.get("title")
                    and not re.search(r"[—–]", line)
                ):
                    current["title"] = cls._clean_title(line)
                    continue

                current = cls._new_job()
                jobs.append(current)
                company, role = cls._split_company_role(line)
                current["company"] = company or ""
                current["title"] = cls._clean_title(
                    role or line
                )
                continue

            if current is None:
                current = cls._new_job()
                jobs.append(current)
                current["company"] = line
                continue

            if not current.get("company"):
                current["company"] = line
            elif not current.get("title"):
                current["title"] = line
            elif not current.get("bullets"):
                current["title"] = (
                    current.get("title") or line
                )
            else:
                current = cls._new_job()
                jobs.append(current)
                current["company"] = line

        return [
            job
            for job in jobs
            if (job.get("company") or job.get("title"))
            and not cls._is_bullet(job.get("company") or "")
        ]

    @staticmethod
    def _is_job_header(line: str) -> bool:

        if ResumeIngestor._is_bullet(line):
            return False

        if len(line) > 120:
            return False

        return bool(
            re.search(r"[—–]", line)
            or ROLE_HINT_RE.search(line)
        )

    @staticmethod
    def _new_job() -> dict:

        return {
            "company": "",
            "title": "",
            "start_date": "",
            "end_date": "",
            "bullets": [],
        }

    @staticmethod
    def _is_page_noise(line: str) -> bool:

        return bool(
            re.match(
                r"^--?\s*\d+\s+of\s+\d+"
                r"|^\d+\s*/\s*\d+$"
                r"|^page\s+\d+"
                r"|^nayaab ahmed n$",
                line,
                re.I,
            )
        )

    @staticmethod
    def _join_wrapped_headers(text: str) -> str:

        lines: list[str] = []

        for raw in text.splitlines():
            line = raw.strip()

            if not line:
                if lines and lines[-1]:
                    lines.append("")
                continue

            if (
                lines
                and re.search(r"[–—\-]\s*$", lines[-1])
                and re.match(
                    rf"^(present|current|\)|{MONTH_RE})",
                    line,
                    re.I,
                )
            ):
                lines[-1] = f"{lines[-1]} {line}".strip()
                continue

            lines.append(line)

        return "\n".join(lines)

    @staticmethod
    def _split_company_role(text: str) -> tuple[str, str]:

        cleaned = text.strip(" -,|")

        for sep in (" — ", " – ", " - ", "—", "–"):
            if sep in cleaned:
                left, right = cleaned.split(sep, 1)
                left = left.strip(" ,")
                right = right.strip(" ,")
                company, role = ResumeIngestor._order_company_role(
                    left,
                    right,
                )
                return (
                    ResumeIngestor._normalize_company(company),
                    role,
                )

        return "", cleaned

    @staticmethod
    def _order_company_role(
        left: str,
        right: str,
    ) -> tuple[str, str]:

        if ROLE_HINT_RE.search(left) and not ROLE_HINT_RE.search(
            right
        ):
            return right, left

        return left, right

    @staticmethod
    def _normalize_company(name: str) -> str:

        compact = re.sub(r"\s+", " ", name).strip()
        return compact.rstrip(",")

    @staticmethod
    def _clean_title(title: str | None) -> str:

        text = (title or "").strip()
        return re.sub(r"\s*\(\s*\)\s*$", "", text).strip()

    @staticmethod
    def _is_bullet(line: str) -> bool:

        return bool(BULLET_RE.match(line or ""))

    @staticmethod
    def _strip_bullet(line: str) -> str:

        return BULLET_RE.sub("", line).strip()

    @staticmethod
    def _jobs_look_broken(jobs: list[dict]) -> bool:

        if not jobs:
            return True

        empty = sum(
            1
            for job in jobs
            if not (job.get("bullets") or job.get("description"))
        )
        long_company = sum(
            1
            for job in jobs
            if len(str(job.get("company") or "")) > 80
            or ResumeIngestor._is_bullet(
                str(job.get("company") or "")
            )
        )
        return empty >= 3 or long_company >= 2 or len(jobs) > 8

    @staticmethod
    def _is_wrapped_line(line: str, last_bullet: str) -> bool:

        if line[:1].islower():
            return True

        return bool(
            last_bullet
            and not re.search(r'[.!?]"?$', last_bullet.rstrip())
        )

    @staticmethod
    def _normalize_dates(match: re.Match) -> tuple[str, str]:

        start_month = MONTHS[match.group(1).lower()[:3]]
        start_year = match.group(2)
        end_raw = match.group(3).strip()

        if end_raw.lower() in {"present", "current"}:
            return f"{start_year}-{start_month}", "Present"

        end_parts = end_raw.split()
        end_month = MONTHS[end_parts[0].lower()[:3]]
        end_year = end_parts[1]
        return (
            f"{start_year}-{start_month}",
            f"{end_year}-{end_month}",
        )

    @classmethod
    def _parse_projects(cls, text: str) -> list[dict]:

        if not text.strip():
            return []

        name = "Project"
        bullets: list[str] = []

        for raw in text.splitlines():
            line = raw.strip()

            if not line or cls._is_page_noise(line):
                continue

            if cls._is_bullet(line):
                bullets.append(cls._strip_bullet(line))
                continue

            if bullets and cls._is_wrapped_line(line, bullets[-1]):
                bullets[-1] = f"{bullets[-1]} {line}".strip()
                continue

            if "project" in line.lower():
                name = line
                continue

        if not bullets:
            return []

        return [
            {
                "name": name,
                "bullets": bullets,
                "description": " ".join(bullets),
            }
        ]

    @classmethod
    def _parse_education(cls, text: str) -> list[dict]:

        entries = []
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        for index, line in enumerate(lines):
            if not re.search(
                r"bachelor|master|b\.e|b\.tech|m\.tech|"
                r"degree|engineering|diploma|pcmb|"
                r"college|institute|university|cgpa|"
                r"\d+\.\d+\s*%",
                line,
                re.I,
            ):
                continue

            institution = ""
            degree = line
            year = ""

            for sep in (" — ", " – ", " - ", "—", "–"):
                if sep in line:
                    left, right = line.split(sep, 1)
                    left = left.strip()
                    right = right.strip()
                    years = ""

                    if "|" in right:
                        right, years = [
                            part.strip()
                            for part in right.split("|", 1)
                        ]

                    if re.search(
                        r"institute|college|university|vidya",
                        left,
                        re.I,
                    ) and re.search(
                        r"b\.e|b\.tech|pcmb|bachelor|master|"
                        r"engineering",
                        right,
                        re.I,
                    ):
                        institution = left
                        degree = right
                    else:
                        degree = left
                        institution = right

                    year_match = re.search(
                        r"(\d{4})\s*[–\-]\s*(\d{4})",
                        years or right,
                    )

                    if year_match:
                        year = year_match.group(2)
                    break

            if not institution and index > 0:
                institution = re.sub(
                    r"\s+\d{4}\s*[-–]\s*\d{4}\s*$",
                    "",
                    lines[index - 1],
                ).strip(" ,")

            if not year:
                year_match = re.search(
                    r"(\d{4})\s*[-–]\s*(\d{4})",
                    lines[index - 1] if index else line,
                )

                if year_match:
                    year = year_match.group(2)

            entries.append(
                {
                    "degree": degree,
                    "institution": institution,
                    "year": year,
                }
            )

        return entries

    @classmethod
    def _parse_skills(cls, text: str) -> list[str]:

        lines: list[str] = []

        for raw in text.splitlines():
            line = cls._strip_bullet(raw.strip())

            if not line:
                continue

            if lines and ":" not in line:
                lines[-1] = f"{lines[-1]} {line}".strip()
                continue

            lines.append(line)

        skills: list[str] = []

        for line in lines:
            if ":" in line:
                line = line.split(":", 1)[1]

            for item in re.split(r"[,;|]|\sand\s", line):
                skill = item.strip(" .")

                if 1 <= len(skill) < 60 and not SECTION_RE.match(skill):
                    skills.append(skill)

        return list(dict.fromkeys(skills))

    @classmethod
    def _parse_certs(cls, text: str) -> list[str]:

        certs = []

        for raw in text.splitlines():
            line = cls._strip_bullet(raw.strip())

            if line:
                line = re.sub(r"^[•●▪◦\-–—*]+\s*", "", line)
                certs.append(line)

        return certs

    @staticmethod
    def _parse_extra(text: str) -> dict:

        headline = ""

        for line in text.splitlines():
            line = re.sub(r"\s+", " ", line.strip())

            if not line:
                continue

            email_split = re.split(
                r"\s+(?=\S+@\S+)",
                line,
                maxsplit=1,
            )
            candidate = email_split[0].strip(" |")

            if (
                "|" in candidate
                and "linkedin" not in candidate.lower()
                and not re.search(
                    r"\d{4}|cgpa|pcmb|hindi|kannada",
                    candidate,
                    re.I,
                )
            ):
                headline = candidate
                if headline.isupper() or headline == headline.upper():
                    headline = " | ".join(
                        ResumeIngestor._title_headline_part(part)
                        for part in headline.split("|")
                    )
                break

        languages = []
        interests = []
        lang = re.search(r"Languages:\s*(.+)", text, re.I)
        interest = re.search(r"Interests:\s*(.+)", text, re.I)
        lang_block = re.search(
            r"LANGUAGES\s+([^\n]+)",
            text,
            re.I,
        )

        if lang:
            languages = [
                part.strip()
                for part in re.split(r"[,;/|]", lang.group(1))
                if part.strip()
            ]
        elif lang_block:
            languages = [
                part.strip()
                for part in re.split(
                    r"[,;/|]",
                    lang_block.group(1),
                )
                if part.strip()
            ]

        if interest:
            interests = [
                part.strip()
                for part in interest.group(1).split(",")
                if part.strip()
            ]

        summary = ""
        block = re.search(
            r"PROFESSIONAL SUMMARY\s+(.+?)"
            r"(?:\nTECHNICAL|\nPROFESSIONAL EXPERIENCE)",
            text,
            re.I | re.S,
        )

        if block:
            summary = re.sub(
                r"\s+",
                " ",
                block.group(1),
            ).strip()

        return {
            "headline": headline,
            "languages": languages,
            "interests": interests,
            "summary": summary,
        }

    @staticmethod
    def _title_headline_part(part: str) -> str:

        words = []

        acronyms = {
            "RTOS",
            "AI",
            "RAG",
            "LLM",
            "HSI",
            "C",
            "CI",
            "CD",
        }

        for word in part.split():
            upper = word.upper()

            if upper in acronyms:
                words.append(upper)
            elif word.isupper():
                words.append(word.title())
            else:
                words.append(word)

        return " ".join(words).strip()

    @staticmethod
    def _guess_name(text: str) -> str:

        for line in text.splitlines():
            line = line.strip(" •|-")

            if not line:
                continue

            if "@" in line or SECTION_RE.match(line):
                continue

            if line.isupper() and len(line.split()) >= 2:
                return line.title()

            if FAKE_NAME_RE.match(line) or "_" in line:
                continue

            if any(char.isdigit() for char in line):
                continue

            if "|" in line:
                continue

            words = line.split()

            if 2 <= len(words) <= 6:
                return line

        return ""


def profile_gaps(
    profile: CandidateProfile | None,
) -> list[str]:

    if profile is None:
        return [
            "name",
            "skills",
            "experiences",
        ]

    missing = []

    if not profile.name:
        missing.append("name")

    if not profile.skills:
        missing.append("skills")

    if not profile.experiences:
        missing.append("experiences")

    return missing
