import json
import re

from app.llm.lmstudio_client import LMStudioClient
from app.profile.experience_tagger import (
    ground_domains,
    ground_technologies,
)


RESUME_SCHEMA = {
    "name": "resume_facts",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "name": {"type": "string"},
            "email": {"type": "string"},
            "phone": {"type": "string"},
            "location": {"type": "string"},
            "linkedin": {"type": "string"},
            "github": {"type": "string"},
            "headline": {"type": "string"},
            "summary": {"type": "string"},
            "languages": {
                "type": "array",
                "items": {"type": "string"},
            },
            "interests": {
                "type": "array",
                "items": {"type": "string"},
            },
            "skills": {
                "type": "array",
                "items": {"type": "string"},
            },
            "certifications": {
                "type": "array",
                "items": {"type": "string"},
            },
            "experience": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "company": {"type": "string"},
                        "title": {"type": "string"},
                        "start_date": {"type": "string"},
                        "end_date": {"type": "string"},
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "technologies": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "company",
                        "title",
                        "start_date",
                        "end_date",
                        "bullets",
                        "technologies",
                        "domains",
                    ],
                },
            },
            "projects": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "name": {"type": "string"},
                        "bullets": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "technologies": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "domains": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                    },
                    "required": [
                        "name",
                        "bullets",
                        "technologies",
                        "domains",
                    ],
                },
            },
            "education": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "degree": {"type": "string"},
                        "institution": {"type": "string"},
                        "year": {"type": "string"},
                    },
                    "required": [
                        "degree",
                        "institution",
                    ],
                },
            },
        },
        "required": [
            "name",
            "email",
            "phone",
            "location",
            "linkedin",
            "github",
            "headline",
            "summary",
            "languages",
            "interests",
            "skills",
            "certifications",
            "experience",
            "projects",
            "education",
        ],
    },
}


class ResumeParseAgent:

    def __init__(
        self,
        llm: LMStudioClient | None = None,
    ):
        self.llm = llm or LMStudioClient()
        self.last_error = ""

    def reachable(self) -> bool:

        return self.llm.reachable()

    def extract(self, text: str) -> dict | None:

        self.last_error = ""

        if not text.strip():
            self.last_error = "Resume text is empty."
            return None

        if not str(self.llm.llm_model or "").strip():
            self.last_error = (
                "No chat model selected. Pick a model "
                "under LLM provider, then parse again."
            )
            return None

        if not self.reachable():
            self.last_error = (
                f"Cannot reach {self.llm.kind} at "
                f"{self.llm.base_url}."
            )
            return None

        last = None
        issues = []

        for attempt in (1, 2, 3):
            raw = self._ask(
                text,
                issues=issues,
            )

            if not raw:
                if not self.last_error:
                    self.last_error = (
                        "LLM returned an empty response."
                    )
                continue

            facts = self._normalize(raw)
            last = facts
            issues = self._quality_issues(facts)

            if not issues:
                return facts

        return last

    def _ask(
        self,
        text: str,
        issues: list[str],
    ) -> dict | None:

        extra = ""

        if issues:
            extra = (
                "\nPrevious JSON failed quality checks:\n- "
                + "\n- ".join(issues)
                + "\nFix those mistakes. Identify content by "
                "meaning, not by visual layout.\n"
            )

        try:
            raw = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": self._prompt(),
                    },
                    {
                        "role": "user",
                        "content": (
                            "RESUME TEXT:\n\n"
                            f"{text[:16000]}\n\n"
                            "END OF RESUME.\n"
                            f"{extra}"
                            "Return JSON only."
                        ),
                    },
                ],
                temperature=0,
                max_tokens=6000,
                response_schema=RESUME_SCHEMA,
            )
        except Exception as exc:
            self.last_error = str(exc)
            return None

        return self._parse_json(raw)

    @staticmethod
    def _prompt() -> str:

        return """
You extract a candidate profile from resume text.
You are not a job search agent. You do not tailor.

The text may come from any PDF layout: columns,
wrapped lines, dates on a following line, role
before company or company before role, and any
bullet glyph (•, -, , etc). Ignore layout.
Identify each field by meaning.

Return a JSON object only. No tool calls.

What each field means:
- name: the person, not a function/tool name
- headline: current target title under the name
- summary: professional summary, copied
- skills: tools/languages listed as skills
- experience: paid jobs only. company is an
  employer name (short). title is the job title.
  bullets are achievements under that job.
  technologies are tools/languages named in
  those bullets. domains are work areas named
  or clearly described in those bullets.
  Never put an achievement sentence in company
  or title.
- projects: personal/side projects, not employers.
  technologies and domains come from the project
  description, not from other jobs.
- education: every school row, including PU/12th
- languages, certifications, interests: as written
- linkedin/github: URL if present, else handle

Copy achievement wording. Join wrapped lines.
Keep numbers (75%, 200%). Dates as YYYY-MM or
Present. Do not invent companies, skills, technologies,
domains, or jobs. If a tool is not named in
that job's bullets, leave it out of that job.
Ignore page headers, page numbers, and repeated
name lines.
""".strip()

    @staticmethod
    def _usable(facts: dict | None) -> bool:

        return not ResumeParseAgent._quality_issues(facts)

    @staticmethod
    def _quality_issues(facts: dict | None) -> list[str]:

        if not facts:
            return ["no JSON object"]

        issues = []

        if ResumeParseAgent._is_fake_name(facts.get("name")):
            issues.append(
                "name must be the person, not a tool name"
            )

        jobs = [
            job
            for job in (facts.get("experience") or [])
            if isinstance(job, dict)
        ]
        skills = facts.get("skills") or []

        if len(jobs) < 1:
            issues.append("need at least one employer")

        if len(skills) < 3:
            issues.append("need skills from the resume")

        for job in jobs:
            company = str(job.get("company") or "").strip()
            bullets = job.get("bullets") or []

            if len(company) > 90:
                issues.append(
                    "company must be an employer name, "
                    "not an achievement sentence"
                )
            if not bullets:
                issues.append(
                    "each job needs its achievement bullets"
                )

        return list(dict.fromkeys(issues))

    @staticmethod
    def _is_fake_name(name: str | None) -> bool:

        text = str(name or "").strip()

        if not text:
            return True

        return bool(
            re.match(
                r"^(extract_|parse_|get_|resume_|format_)",
                text,
                re.I,
            )
        ) or "_" in text.replace(" ", "")

    @staticmethod
    def _is_school_entry(item: dict) -> bool:

        blob = " ".join(
            [
                str(item.get("company") or ""),
                str(item.get("title") or ""),
            ]
        ).lower()

        return bool(
            re.search(
                r"\b(b\.e|b\.tech|m\.tech|bachelor|"
                r"master|university|college|institute|"
                r"pcmb|school|cgpa)\b",
                blob,
            )
        )

    @staticmethod
    def _clean_link(value: str, host: str) -> str:

        text = (value or "").strip()

        if host in text.lower():
            return text

        if re.fullmatch(r"[\w-]+", text):
            if host == "github.com":
                return f"https://github.com/{text}"
            if host == "linkedin.com":
                return (
                    "https://www.linkedin.com/in/"
                    f"{text}"
                )

        return ""

    @staticmethod
    def _clean_tag_list(values) -> list[str]:

        if isinstance(values, str):
            values = [values]

        names = []

        for item in values or []:
            if not isinstance(item, str):
                continue

            name = re.sub(r"\s+", " ", item).strip()

            if name:
                names.append(name)

        return names

    @staticmethod
    def _normalize_project(item: dict) -> dict:

        bullets = item.get("bullets")
        description = item.get("description")

        if isinstance(description, list):
            bullets = description
            description = ""

        if not isinstance(bullets, list):
            bullets = []

        bullets = [
            bullet.strip()
            for bullet in bullets
            if isinstance(bullet, str) and bullet.strip()
        ]
        blob = "\n".join(bullets)

        if not blob and isinstance(description, str):
            blob = description

        return {
            "name": str(item.get("name") or "").strip(),
            "bullets": bullets,
            "technologies": ground_technologies(
                ResumeParseAgent._clean_tag_list(
                    item.get("technologies")
                ),
                blob,
            ),
            "domains": ground_domains(
                ResumeParseAgent._clean_tag_list(
                    item.get("domains")
                ),
                blob,
            ),
        }

    @staticmethod
    def _repair_job(job: dict) -> dict:

        company = str(job.get("company") or "").strip()
        title = str(job.get("title") or "").strip()

        if not company and title and len(title) < 100:
            company, role = ResumeParseAgent._split_header(
                title
            )
            if company:
                job["company"] = company
                job["title"] = role or title

        job["company"] = ResumeParseAgent._strip_city(
            str(job.get("company") or "")
        )
        job["bullets"] = [
            re.sub(r"\s+", " ", bullet).strip()
            for bullet in job.get("bullets") or []
        ]
        blob = "\n".join(job["bullets"])
        job["technologies"] = ground_technologies(
            ResumeParseAgent._clean_tag_list(
                job.get("technologies")
            ),
            blob,
        )
        job["domains"] = ground_domains(
            ResumeParseAgent._clean_tag_list(
                job.get("domains")
            ),
            blob,
        )
        return job

    @staticmethod
    def _split_header(text: str) -> tuple[str, str]:

        cleaned = text.strip(" -,|")

        for sep in (" — ", " – ", " - ", "—", "–"):
            if sep in cleaned:
                left, right = cleaned.split(sep, 1)
                right = re.sub(
                    r"\([^)]*\)\s*$",
                    "",
                    right,
                ).strip()
                left = left.strip(" ,")
                right = right.strip(" ,")

                if re.search(
                    r"engineer|developer|associate|analyst",
                    left,
                    re.I,
                ) and not re.search(
                    r"engineer|developer|associate|analyst",
                    right,
                    re.I,
                ):
                    return right, left

                return left, right

        return "", cleaned

    @staticmethod
    def _strip_city(company: str) -> str:

        return re.sub(
            r",\s*(Bangalore|Bengaluru|Chennai|"
            r"Hyderabad|Pune|Mumbai|Delhi)\s*$",
            "",
            company,
            flags=re.I,
        ).strip()

    @staticmethod
    def _normalize(extracted: dict) -> dict:

        skills = extracted.get("skills") or []

        if isinstance(skills, str):
            skills = [skills]

        experience = []

        for item in extracted.get("experience") or []:
            if not isinstance(item, dict):
                continue

            if ResumeParseAgent._is_school_entry(item):
                continue

            job = {
                "company": str(
                    item.get("company") or ""
                ).strip(),
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
                    if isinstance(bullet, str)
                    and bullet.strip()
                ],
                "technologies": ResumeParseAgent._clean_tag_list(
                    item.get("technologies")
                ),
                "domains": ResumeParseAgent._clean_tag_list(
                    item.get("domains")
                ),
            }
            experience.append(
                ResumeParseAgent._repair_job(job)
            )

        education = []

        for item in extracted.get("education") or []:
            if not isinstance(item, dict):
                continue

            education.append(
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
                        item.get("year")
                        or item.get("end_date")
                        or ""
                    ).strip(),
                }
            )

        certs = extracted.get("certifications") or []

        if isinstance(certs, str):
            certs = [certs]

        name = str(extracted.get("name") or "").strip()

        if name.isupper() and len(name.split()) >= 2:
            name = name.title()

        if ResumeParseAgent._is_fake_name(name):
            name = ""

        def _list(key: str) -> list[str]:
            items = extracted.get(key) or []
            if isinstance(items, str):
                items = [part.strip() for part in re.split(
                    r"[,;/|]", items
                ) if part.strip()]
            return [
                item.strip()
                for item in items
                if isinstance(item, str) and item.strip()
            ]

        return {
            "name": name,
            "email": str(extracted.get("email") or "").strip(),
            "phone": str(extracted.get("phone") or "").strip(),
            "location": str(
                extracted.get("location") or ""
            ).strip(),
            "headline": str(
                extracted.get("headline") or ""
            ).strip(),
            "linkedin": ResumeParseAgent._clean_link(
                str(extracted.get("linkedin") or ""),
                "linkedin.com",
            ),
            "github": ResumeParseAgent._clean_link(
                str(extracted.get("github") or ""),
                "github.com",
            ),
            "summary": str(
                extracted.get("summary") or ""
            ).strip(),
            "languages": _list("languages"),
            "interests": _list("interests"),
            "skills": [
                item.strip()
                for item in skills
                if isinstance(item, str) and item.strip()
            ],
            "certifications": [
                item.strip()
                for item in certs
                if isinstance(item, str) and item.strip()
            ],
            "experience": experience,
            "projects": [
                ResumeParseAgent._normalize_project(item)
                for item in extracted.get("projects") or []
                if isinstance(item, dict)
                and (
                    item.get("name")
                    or item.get("bullets")
                )
            ],
            "education": education,
        }

    @staticmethod
    def _parse_json(raw: str) -> dict | None:

        if not raw or not raw.strip():
            return None

        text = re.sub(
            r"^\s*```(?:json)?\s*",
            "",
            raw.strip(),
            flags=re.I,
        )
        text = re.sub(r"\s*```\s*$", "", text).strip()

        try:
            loaded = json.loads(text)
        except json.JSONDecodeError:
            decoder = json.JSONDecoder()
            loaded = None

            for match in re.finditer(r"\{", text):
                try:
                    loaded, _ = decoder.raw_decode(
                        text[match.start():]
                    )
                    break
                except json.JSONDecodeError:
                    continue

        if not isinstance(loaded, dict):
            return None

        if "parameters" in loaded or "resume_text" in loaded:
            return None

        return loaded
