import json
import re

from app.llm.lmstudio_client import LMStudioClient
from app.models.candidate import (
    CandidateProfile,
    Education,
    Experience,
)
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
    r"skills|additional\s+information|projects|"
    r"certifications)\s*$",
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
    "skills",
    "experience",
    "education",
    "summary",
}


class ResumeIngestor:

    def __init__(
        self,
        llm: LMStudioClient | None = None,
    ):
        self.llm = llm or LMStudioClient()

    def parse_text(self, text: str) -> dict:

        heuristic = self._heuristic_parse(text)
        extracted = self._llm_extract(text)

        if extracted:
            facts = self._merge_facts(heuristic, extracted)
        else:
            facts = heuristic

        if not facts.get("name") or FAKE_NAME_RE.match(
            str(facts.get("name") or "")
        ):
            facts["name"] = self._guess_name(text)

        return facts

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
            for item in facts.get("experience") or []
            if isinstance(item, dict)
            and (
                item.get("company")
                or item.get("title")
                or item.get("role")
            )
        ]

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
        preferred = (
            [location]
            if location
            else list(
                existing.preferred_locations
                if existing
                else []
            )
        )

        base = existing.model_dump() if existing else {}

        base.update(
            {
                "name": facts.get("name") or base.get("name") or "",
                "email": facts.get("email") or base.get("email"),
                "phone": facts.get("phone") or base.get("phone"),
                "linkedin": facts.get("linkedin")
                or base.get("linkedin"),
                "github": facts.get("github")
                or base.get("github"),
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
                "preferred_locations": preferred
                or base.get("preferred_locations")
                or [],
            }
        )

        if not base.get("professional_summary"):
            base["professional_summary"] = (
                facts.get("summary") or ""
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
        sections = self._split_sections(text)
        facts["experience"] = self._parse_experience(
            sections.get("experience", "")
        )
        facts["education"] = self._parse_education(
            sections.get("education", "")
        )
        facts["skills"] = self._parse_skills(
            sections.get("skills", "")
            or text
        )
        return facts

    def _llm_extract(self, text: str) -> dict | None:

        try:
            import requests

            response = requests.get(
                f"{self.llm.base_url}/models",
                timeout=0.4,
            )

            if not response.ok:
                return None
        except Exception:
            return None

        user_prompt = (
            "RESUME TEXT:\n\n"
            f"{text[:12000]}\n\n"
            "END OF RESUME TEXT.\n\n"
            "Return the extracted resume JSON now.\n"
            "Remember:\n"
            "- JSON only\n"
            "- no function call\n"
            "- no parameters\n"
            "- no resume_text field"
        )

        try:
            raw = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": self._extraction_prompt(),
                    },
                    {
                        "role": "user",
                        "content": user_prompt,
                    },
                ],
                max_tokens=2500,
            )
            parsed = self._parse_llm_json(raw)

            if parsed:
                return self._normalize_extracted(parsed)
        except Exception:
            return None

        return None

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
            "skills": [],
            "experience": [],
            "education": [],
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

        jobs: list[dict] = []
        current: dict | None = None

        for raw in text.splitlines():
            line = raw.strip()

            if not line:
                continue

            if cls._is_bullet(line):
                if current is None:
                    continue

                bullet = cls._strip_bullet(line)
                current["bullets"].append(bullet)
                continue

            date_match = DATE_RANGE_RE.search(line)

            if date_match:
                start, end = cls._normalize_dates(date_match)
                title = DATE_RANGE_RE.sub("", line).strip(" -,|")

                if current is None:
                    current = cls._new_job()
                    jobs.append(current)

                if title and not current.get("title"):
                    current["title"] = title
                elif title and current.get("title") and not current.get("company"):
                    current["company"] = current["title"]
                    current["title"] = title
                elif title and current.get("bullets"):
                    current = cls._new_job()
                    jobs.append(current)
                    current["title"] = title

                current["start_date"] = start
                current["end_date"] = end
                continue

            if current and current.get("bullets"):
                last = current["bullets"][-1]

                if cls._is_wrapped_line(line, last):
                    current["bullets"][-1] = (
                        last + " " + line
                    ).strip()
                    continue

                current = cls._new_job()
                jobs.append(current)
                current["company"] = line
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
            else:
                current = cls._new_job()
                jobs.append(current)
                current["company"] = line

        return [
            job
            for job in jobs
            if job.get("company") or job.get("title")
        ]

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
    def _is_bullet(line: str) -> bool:

        return bool(re.match(r"^[•●▪◦\-–—*]\s+", line))

    @staticmethod
    def _strip_bullet(line: str) -> str:

        return re.sub(r"^[•●▪◦\-–—*]\s+", "", line).strip()

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
    def _parse_education(cls, text: str) -> list[dict]:

        entries = []
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        for index, line in enumerate(lines):
            if re.search(
                r"bachelor|master|b\.e|b\.tech|m\.tech|"
                r"degree|engineering|diploma",
                line,
                re.I,
            ):
                institution = ""

                if index > 0:
                    institution = re.sub(
                        r"\s+\d{4}\s*[-–]\s*\d{4}\s*$",
                        "",
                        lines[index - 1],
                    ).strip(" ,")

                year = ""
                year_match = re.search(
                    r"(\d{4})\s*[-–]\s*(\d{4})",
                    lines[index - 1] if index else line,
                )

                if year_match:
                    year = year_match.group(2)

                entries.append(
                    {
                        "degree": line,
                        "institution": institution,
                        "year": year,
                    }
                )

        return entries

    @classmethod
    def _parse_skills(cls, text: str) -> list[str]:

        skills: list[str] = []

        for raw in text.splitlines():
            line = cls._strip_bullet(raw.strip())

            if not line:
                continue

            if ":" in line:
                line = line.split(":", 1)[1]

            for item in re.split(r"[,;/]| and ", line):
                skill = item.strip(" .")

                if 1 <= len(skill) < 40 and not SECTION_RE.match(skill):
                    skills.append(skill)

        return list(dict.fromkeys(skills))

    @staticmethod
    def _guess_name(text: str) -> str:

        for line in text.splitlines():
            line = line.strip(" •|-")

            if not line:
                continue

            if "@" in line or SECTION_RE.match(line):
                continue

            if FAKE_NAME_RE.match(line) or "_" in line:
                continue

            if any(char.isdigit() for char in line):
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
