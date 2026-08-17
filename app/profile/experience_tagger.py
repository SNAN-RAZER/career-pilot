import json
import re

from app.llm.lmstudio_client import LMStudioClient
from app.models.candidate import CandidateProfile, Experience, Project


TAG_SCHEMA = {
    "name": "experience_tags",
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "additionalProperties": False,
                    "properties": {
                        "id": {"type": "string"},
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
                        "id",
                        "technologies",
                        "domains",
                    ],
                },
            }
        },
        "required": ["items"],
    },
}


class ExperienceTagger:
    """Fill per-job and per-project technologies and domains."""

    def __init__(
        self,
        llm: LMStudioClient | None = None,
    ):
        self.llm = llm or LMStudioClient()
        self.last_error = ""

    def enrich_facts(self, facts: dict) -> dict:

        jobs = [
            item
            for item in facts.get("experience") or []
            if isinstance(item, dict)
        ]
        projects = [
            item
            for item in facts.get("projects") or []
            if isinstance(item, dict)
        ]

        records = []

        for index, job in enumerate(jobs):
            text = _blob(
                job.get("bullets") or job.get("description")
            )
            records.append(
                {
                    "id": f"job-{index}",
                    "kind": "job",
                    "name": str(job.get("company") or ""),
                    "role": str(
                        job.get("title") or job.get("role") or ""
                    ),
                    "text": text,
                    "needs_tech": not job.get("technologies"),
                    "needs_domains": not job.get("domains"),
                }
            )

        for index, project in enumerate(projects):
            text = _blob(
                project.get("bullets")
                or project.get("description")
            )
            records.append(
                {
                    "id": f"project-{index}",
                    "kind": "project",
                    "name": str(project.get("name") or ""),
                    "role": "",
                    "text": text,
                    "needs_tech": not project.get("technologies"),
                    "needs_domains": not project.get("domains"),
                }
            )

        tagged = self._tag(records)

        for index, job in enumerate(jobs):
            tags = tagged.get(f"job-{index}") or {}
            text = _blob(
                job.get("bullets") or job.get("description")
            )
            if not job.get("technologies"):
                job["technologies"] = tags.get(
                    "technologies"
                ) or []
            if not job.get("domains"):
                job["domains"] = tags.get("domains") or []
            job["technologies"] = ground_technologies(
                job.get("technologies") or [],
                text,
            )
            job["domains"] = ground_domains(
                job.get("domains") or [],
                text,
            )

        for index, project in enumerate(projects):
            tags = tagged.get(f"project-{index}") or {}
            text = _blob(
                project.get("bullets")
                or project.get("description")
            )
            if not project.get("technologies"):
                project["technologies"] = tags.get(
                    "technologies"
                ) or []
            if not project.get("domains"):
                project["domains"] = tags.get("domains") or []
            project["technologies"] = ground_technologies(
                project.get("technologies") or [],
                text,
            )
            project["domains"] = ground_domains(
                project.get("domains") or [],
                text,
            )

        return facts

    def enrich_profile(
        self,
        profile: CandidateProfile,
    ) -> CandidateProfile:

        facts = {
            "experience": [
                {
                    "company": item.company,
                    "title": item.role,
                    "bullets": item.description,
                    "technologies": list(item.technologies),
                    "domains": list(item.domains),
                }
                for item in profile.experiences
            ],
            "projects": [
                {
                    "name": item.name,
                    "description": item.description,
                    "technologies": list(item.technologies),
                    "domains": list(item.domains),
                }
                for item in profile.projects
            ],
        }
        self.enrich_facts(facts)

        profile.experiences = [
            Experience(
                **{
                    **item.model_dump(),
                    "technologies": job.get("technologies")
                    or [],
                    "domains": job.get("domains") or [],
                }
            )
            for item, job in zip(
                profile.experiences,
                facts["experience"],
            )
        ]
        profile.projects = [
            Project(
                **{
                    **item.model_dump(),
                    "technologies": project.get(
                        "technologies"
                    )
                    or [],
                    "domains": project.get("domains") or [],
                }
            )
            for item, project in zip(
                profile.projects,
                facts["projects"],
            )
        ]
        return profile

    def _tag(self, records: list[dict]) -> dict[str, dict]:

        pending = [
            item
            for item in records
            if item["text"]
            and (item["needs_tech"] or item["needs_domains"])
        ]

        if not pending:
            return {}

        if not str(self.llm.llm_model or "").strip():
            self.last_error = "No chat model selected."
            return {}

        try:
            raw = self.llm.chat(
                [
                    {
                        "role": "system",
                        "content": _prompt(),
                    },
                    {
                        "role": "user",
                        "content": (
                            "ITEMS:\n"
                            f"{_items_json(pending)}\n\n"
                            "Return JSON only."
                        ),
                    },
                ],
                temperature=0,
                max_tokens=3000,
                response_schema=TAG_SCHEMA,
            )
        except Exception as exc:
            self.last_error = str(exc)
            return {}

        parsed = _parse_json(raw)

        if not parsed:
            return {}

        by_id = {}

        for item in parsed.get("items") or []:
            if not isinstance(item, dict):
                continue

            key = str(item.get("id") or "")
            source = next(
                (
                    record["text"]
                    for record in pending
                    if record["id"] == key
                ),
                "",
            )
            by_id[key] = {
                "technologies": ground_technologies(
                    item.get("technologies") or [],
                    source,
                ),
                "domains": ground_domains(
                    item.get("domains") or [],
                    source,
                ),
            }

        return by_id


def ground_technologies(
    values: list,
    text: str,
) -> list[str]:

    return _unique(
        [
            name
            for name in _clean_names(values)
            if _tech_in_text(name, text)
        ]
    )


def ground_domains(
    values: list,
    text: str,
) -> list[str]:

    return _unique(
        [
            name
            for name in _clean_names(values)
            if _domain_in_text(name, text)
        ]
    )


def _clean_names(values: list) -> list[str]:

    names = []

    for item in values or []:
        if not isinstance(item, str):
            continue

        name = re.sub(r"\s+", " ", item).strip(" ;,")

        if not name or len(name) > 48:
            continue

        if "<" in name or ">" in name:
            continue

        lowered = name.lower()

        if lowered in {"na", "n/a", "none"}:
            continue

        names.append(name)

    return names


def _tech_in_text(name: str, text: str) -> bool:

    haystack = text or ""

    if not haystack.strip():
        return False

    needle = name.strip()

    if _as_word(needle, haystack):
        return True

    compact = re.sub(r"[^a-z0-9]+", "", needle.lower())
    hay_compact = re.sub(
        r"[^a-z0-9]+",
        "",
        haystack.lower(),
    )

    return len(compact) >= 3 and compact in hay_compact


def _domain_in_text(name: str, text: str) -> bool:

    haystack = re.sub(r"[-_/]", " ", text or "")

    if _as_word(name, haystack):
        return True

    parts = [
        part
        for part in re.split(r"[\s/,-]+", name)
        if len(part) >= 4
    ]

    if not parts:
        return False

    return any(_as_word(part, haystack) for part in parts)


def _as_word(needle: str, haystack: str) -> bool:

    body = (needle or "").strip()

    if not body:
        return False

    pattern = (
        r"(?<![a-z0-9+#./-])"
        + re.escape(body)
        + r"(?![a-z0-9+#/_-])"
    )

    return re.search(pattern, haystack, flags=re.I) is not None


def _blob(value) -> str:

    if isinstance(value, list):
        return "\n".join(
            str(item).strip()
            for item in value
            if str(item).strip()
        )

    return str(value or "").strip()


def _unique(values: list[str]) -> list[str]:

    seen = set()
    result = []

    for item in values:
        key = item.lower()

        if key in seen:
            continue

        seen.add(key)
        result.append(item)

    return result


def _items_json(records: list[dict]) -> str:

    payload = [
        {
            "id": item["id"],
            "kind": item["kind"],
            "company_or_name": item["name"],
            "role": item["role"],
            "description": item["text"],
        }
        for item in records
    ]
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _prompt() -> str:

    return """
You extract technologies and domains from one
candidate's job and project descriptions.

Each item has kind "job" or "project".
Treat projects the same as jobs: read only that
item's description and tag that item alone.

technologies: tools, languages, frameworks,
libraries, products, and platforms named in
the description. Use the short name as written
(Python, LDRA, DOORS, Embedded C, Eclipse RT,
Ada 95, VxWorks, RTRT, Node.js, Matplotlib,
LangChain, LangGraph, Qdrant, Docker, Ollama).

domains: work areas evidenced by that
description (for example Avionics, Aerospace,
Embedded Systems, Software Testing, RAG,
Agentic AI, Knowledge Graphs). Keep names short.

Rules:
- Do not invent names that are not in the text.
- Do not copy whole sentences.
- Do not copy technologies from a job onto a
  project, or from a project onto a job.
- If nothing is named, return empty arrays.
- Return JSON only.
""".strip()


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

    return loaded
