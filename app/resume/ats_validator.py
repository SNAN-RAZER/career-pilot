from app.models.candidate import CandidateProfile
from app.models.job import JobPosting
from app.models.tailored_resume import (
    ATSResult,
    TailoredResume,
)
from app.resume.allowed_facts import AllowedFacts
from app.resume.keyword_coverage import (
    claimable_keywords,
    contains_keyword,
    resume_text,
)


class ATSValidator:

    PASS_SCORE = 70.0

    def score(
        self,
        resume: TailoredResume,
        job: JobPosting,
        candidate: CandidateProfile,
    ) -> ATSResult:

        facts = AllowedFacts(candidate)
        issues: list[str] = []

        grounded_skills = []
        invented = []

        for skill in resume.skills:
            if facts.allows_skill(skill):
                grounded_skills.append(skill)
            else:
                invented.append(skill)

        if invented:
            issues.append(
                "Removed skills not present in "
                "the candidate profile: "
                + ", ".join(invented)
            )
            resume.skills = grounded_skills
            resume.grounded = False
            resume.warnings.extend(issues)

        text = resume_text(resume)
        supported = claimable_keywords(
            candidate,
            job.title,
            job.description,
        )

        matched = []
        missing = []

        for keyword in supported:
            if contains_keyword(text, keyword):
                matched.append(keyword)
            else:
                missing.append(keyword)

        if supported:
            coverage = len(matched) / len(supported)
        else:
            coverage = 0.0
            issues.append(
                "No job keywords overlap with "
                "the candidate profile."
            )

        score = round(coverage * 100, 2)

        if not resume.summary:
            score -= 10
            issues.append("Missing summary.")

        if not resume.skills and not resume.experiences:
            score -= 10
            issues.append("Missing skills.")

        if (
            not resume.experience_highlights
            and not resume.experiences
        ):
            score -= 10
            issues.append(
                "Missing experience highlights."
            )

        if invented:
            score -= 15

        score = max(0.0, min(100.0, score))

        return ATSResult(
            score=score,
            matched_keywords=matched,
            missing_keywords=missing[:12],
            passed=score >= self.PASS_SCORE,
            issues=issues,
        )
