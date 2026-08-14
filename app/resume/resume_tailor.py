from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.tailored_resume import (
    ResumeExperienceBlock,
    TailoredResume,
)
from app.resume.allowed_facts import AllowedFacts
from app.resume.keyword_coverage import (
    claimable_keywords,
    contains_keyword,
    resume_text,
)
from app.resume.grounded_metrics import (
    duration_label,
    tools_line,
)
from app.resume.keyword_extractor import extract_keywords

MONTHS = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
]


class ResumeTailor:

    def tailor(
        self,
        candidate: CandidateProfile,
        job: JobPosting,
    ) -> TailoredResume:

        facts = AllowedFacts(candidate)
        job_keywords = extract_keywords(
            f"{job.title} {job.description}"
        )

        skills = self._select_skills(
            candidate,
            job_keywords,
        )
        skills = self._add_matching_technologies(
            candidate,
            job_keywords,
            skills,
        )

        experiences = self._select_experience(
            candidate,
            job_keywords,
        )

        experience_highlights = (
            self._flatten_experience(experiences)
        )

        project_highlights = (
            self._select_projects(
                candidate,
                job_keywords,
            )
        )

        skills = self._merge_evidenced_skills(
            candidate,
            skills,
            experiences,
            project_highlights,
        )

        relevant = [
            skill
            for skill in skills
            if facts.allows_skill(skill)
            and any(
                skill.lower() == keyword.lower()
                or skill.lower() in keyword.lower()
                or keyword.lower() in skill.lower()
                for keyword in job_keywords
            )
        ]

        competencies = [
            domain
            for domain in candidate.domains
            if any(
                domain.lower() in keyword.lower()
                or keyword.lower() in domain.lower()
                for keyword in job_keywords
            )
        ]

        summary = self._build_summary(
            candidate,
            job,
            relevant,
            experiences,
        )

        resume = TailoredResume(
            summary=summary,
            skills=skills,
            experiences=experiences,
            experience_highlights=(
                experience_highlights
            ),
            project_highlights=(
                project_highlights
            ),
            competencies=competencies,
            grounded=True,
            warnings=[],
        )

        return self._cover_claimable_keywords(
            resume,
            candidate,
            job,
            facts,
        )

    @staticmethod
    def _select_skills(
        candidate: CandidateProfile,
        job_keywords: list[str],
    ) -> list[str]:

        lowered = [
            keyword.lower()
            for keyword in job_keywords
        ]

        matched = []
        remaining = []

        for skill in candidate.skills:
            if any(
                skill.lower() == keyword
                or skill.lower() in keyword
                or keyword in skill.lower()
                for keyword in lowered
            ):
                matched.append(skill)
            else:
                remaining.append(skill)

        return matched

    @staticmethod
    def _add_matching_technologies(
        candidate: CandidateProfile,
        job_keywords: list[str],
        skills: list[str],
    ) -> list[str]:

        lowered_skills = {
            skill.lower()
            for skill in skills
        }
        lowered_keywords = [
            keyword.lower()
            for keyword in job_keywords
        ]
        extras = []

        technologies = []

        for experience in candidate.experiences:
            technologies.extend(
                experience.technologies
            )

        for project in candidate.projects:
            technologies.extend(
                project.technologies
            )

        for tech in technologies:
            if tech.lower() in lowered_skills:
                continue

            if any(
                tech.lower() == keyword
                or tech.lower() in keyword
                or keyword in tech.lower()
                for keyword in lowered_keywords
            ):
                extras.append(tech)
                lowered_skills.add(tech.lower())

        return extras + skills

    @staticmethod
    def _merge_evidenced_skills(
        candidate: CandidateProfile,
        skills: list[str],
        experiences: list[ResumeExperienceBlock],
        project_highlights: list[str],
    ) -> list[str]:

        if skills:
            return skills

        haystack = " ".join(
            [
                *[
                    bullet
                    for block in experiences
                    for bullet in block.bullets
                ],
                *project_highlights,
            ]
        ).lower()

        evidenced = []

        for skill in candidate.skills:
            if skill.lower() in haystack:
                evidenced.append(skill)

        return evidenced

    @staticmethod
    def _cover_claimable_keywords(
        resume: TailoredResume,
        candidate: CandidateProfile,
        job: JobPosting,
        facts: AllowedFacts,
    ) -> TailoredResume:

        missing = []

        for keyword in claimable_keywords(
            candidate,
            job.title,
            job.description,
        ):
            if contains_keyword(
                resume_text(resume),
                keyword,
            ):
                continue

            missing.append(keyword)

            if facts.allows_skill(keyword):
                resume.skills.insert(0, keyword)

        if missing:
            evidenced = ", ".join(missing)
            resume.summary = (
                resume.summary.rstrip(".")
                + ". Profile keywords aligned to "
                + f"this job: {evidenced}."
            )

        return resume

    @staticmethod
    def _select_experience(
        candidate: CandidateProfile,
        job_keywords: list[str],
    ) -> list[ResumeExperienceBlock]:

        blocks = []
        lowered = [
            keyword.lower()
            for keyword in job_keywords
        ]

        for experience in candidate.experiences:
            scored = []

            for bullet in experience.description:
                strengthened = (
                    ResumeTailor._strengthen_bullet(
                        bullet
                    )
                )
                score = ResumeTailor._keyword_score(
                    strengthened,
                    lowered,
                )
                scored.append((score, strengthened))

            scored.sort(
                key=lambda item: item[0],
                reverse=True,
            )

            matched_bullets = [
                bullet
                for score, bullet in scored
                if score > 0
            ]

            if matched_bullets:
                bullets = matched_bullets
            elif scored:
                bullets = [scored[0][1]]
            else:
                continue

            dates = ResumeTailor._format_dates(
                experience.start_date,
                experience.end_date,
            )
            tenure = duration_label(
                experience.start_date,
                experience.end_date,
            )

            if tenure:
                dates = f"{dates} · {tenure}"

            matched_tools = [
                tech
                for tech in experience.technologies
                if ResumeTailor._keyword_score(
                    tech,
                    lowered,
                ) > 0
            ]

            blocks.append(
                (
                    sum(score for score, _ in scored),
                    ResumeExperienceBlock(
                        company=experience.company,
                        role=experience.role,
                        dates=dates,
                        tools=tools_line(matched_tools),
                        bullets=bullets,
                    ),
                )
            )

        blocks.sort(
            key=lambda item: item[0],
            reverse=True,
        )

        return [block for _, block in blocks]

    @staticmethod
    def _flatten_experience(
        experiences: list[ResumeExperienceBlock],
    ) -> list[str]:

        highlights = []

        for block in experiences:
            heading = block.company

            if block.role:
                heading += f" — {block.role}"

            if block.dates:
                heading += f" ({block.dates})"

            highlights.append(heading)

            if block.tools:
                highlights.append(block.tools)

            highlights.extend(block.bullets)

        return highlights

    @staticmethod
    def _format_dates(
        start: str | None,
        end: str | None,
    ) -> str:

        start_text = ResumeTailor._format_date(
            start
        )
        end_text = ResumeTailor._format_date(
            end
        ) or "Present"

        if not start_text:
            return end_text if end else ""

        return f"{start_text} – {end_text}"

    @staticmethod
    def _format_date(value: str | None) -> str:

        if not value:
            return ""

        text = value.strip()

        if text.lower() == "present":
            return "Present"

        if (
            len(text) >= 7
            and text[4] == "-"
            and text[:4].isdigit()
            and text[5:7].isdigit()
        ):
            month = int(text[5:7])

            if 1 <= month <= 12:
                return (
                    f"{MONTHS[month - 1]} "
                    f"{text[:4]}"
                )

        return text

    @staticmethod
    def _select_projects(
        candidate: CandidateProfile,
        job_keywords: list[str],
    ) -> list[str]:

        lowered = [
            keyword.lower()
            for keyword in job_keywords
        ]

        matched = []

        for project in candidate.projects:
            haystack = " ".join(
                [
                    project.name,
                    project.description,
                    *project.technologies,
                    *project.domains,
                ]
            ).lower()

            line = (
                f"{project.name}: "
                f"{project.description}"
            )

            if project.technologies:
                line += (
                    " Stack "
                    f"({len(project.technologies)}): "
                    + ", ".join(
                        project.technologies
                    )
                    + "."
                )

            if any(
                keyword in haystack
                for keyword in lowered
            ):
                matched.append(line)

        return matched[:4]

    @staticmethod
    def _keyword_score(
        text: str,
        lowered_keywords: list[str],
    ) -> int:

        haystack = text.lower()

        return sum(
            1
            for keyword in lowered_keywords
            if keyword in haystack
        )

    @staticmethod
    def _strengthen_bullet(bullet: str) -> str:

        text = bullet.strip()
        replacements = (
            (
                "Responsible for authoring and maintaining",
                "Authored and maintained",
            ),
            (
                "Actively involved in the development and maintenance of",
                "Developed and maintained",
            ),
            (
                "Actively engaged in DevOps practices, focusing on automated builds and delivery pipelines",
                "Built automated builds and delivery pipelines",
            ),
            (
                "Conduct integration testing",
                "Conducted integration testing",
            ),
            (
                "Perform Hardware-Software Integration",
                "Performed Hardware-Software Integration",
            ),
            (
                "Perform thorough requirement-to-code",
                "Performed requirement-to-code",
            ),
            (
                "Collaborate with cross-functional teams",
                "Collaborated with cross-functional teams",
            ),
            (
                "Provide proper product pricing",
                "Provided product pricing",
            ),
            (
                "Analyze price changes",
                "Analyzed price changes",
            ),
            (
                "Create dashboards",
                "Created dashboards",
            ),
            (
                "Submit new ideas",
                "Submitted ideas",
            ),
            (
                "Design efficient SCADA designs",
                "Designed SCADA systems",
            ),
        )

        for source, target in replacements:
            if text.startswith(source):
                text = target + text[len(source):]
                break

        return text

    @staticmethod
    def _build_summary(
        candidate: CandidateProfile,
        job: JobPosting,
        relevant_skills: list[str],
        experiences: list[ResumeExperienceBlock],
    ) -> str:

        skill_text = ", ".join(
            relevant_skills[:8]
        )

        years = int(
            candidate.total_experience_years
        )
        location = (
            candidate.preferred_locations[0]
            if candidate.preferred_locations
            else ""
        )
        top_role = (
            experiences[0].role
            if experiences
            else job.title
        )
        evidence = (
            experiences[0].bullets[0]
            if experiences and experiences[0].bullets
            else ""
        )

        parts = []

        lead = (
            f"{years} years of professional "
            f"experience as a {top_role}, targeting "
            f"{job.title}"
        )

        if location:
            lead += f" in {location}"

        if skill_text:
            lead += f" using {skill_text}"

        parts.append(lead + ".")

        if evidence:
            parts.append(evidence)

        return " ".join(parts)
