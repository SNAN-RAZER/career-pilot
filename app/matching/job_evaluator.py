from app.matching.evidence_judge import EvidenceJudge
from app.matching.job_analyzer import JobAnalyzer
from app.matching.semantic_matcher import SemanticMatcher
from app.models.candidate import CandidateProfile
from app.models.evidence import SkillEvidence
from app.models.job_evaluation import (
    JobEvaluation,
    SkillEvaluation,
)
from app.profile.evidence_builder import EvidenceBuilder
from app.matching.skill_ontology import SkillOntology
from app.models.job import JobPosting
from app.matching.job_analysis_input import (
    build_job_analysis_input,
)
from app.resume.skill_match import skill_matches_keyword


class JobEvaluator:

    def __init__(
        self,
        analyzer: JobAnalyzer | None = None,
        evidence_builder: EvidenceBuilder | None = None,
        semantic_matcher: SemanticMatcher | None = None,
        evidence_judge: EvidenceJudge | None = None,
    ):

        self.analyzer = (
            analyzer or JobAnalyzer()
        )

        self.evidence_builder = (
            evidence_builder
            or EvidenceBuilder()
        )

        self.semantic_matcher = (
            semantic_matcher
            or SemanticMatcher()
        )

        self.evidence_judge = (
            evidence_judge
            or EvidenceJudge()
        )

    def evaluate(
    self,
    candidate: CandidateProfile,
    job: JobPosting | str,
) -> JobEvaluation:
        if isinstance(job, str):
            job = JobPosting(
                job_id="legacy-evaluator-job",
                title="Unknown",
                company="Unknown",
                location="",
                description=job,
                source="legacy",
            )
        job_analysis_input = (
            build_job_analysis_input(job)
        )

        requirements = self.analyzer.analyze(
            job_analysis_input
        )

        evidence = self.evidence_builder.build(
            candidate
        )

        required_evaluations = []

        for requirement in requirements.required_skills:

            if JobAnalyzer._is_bad_skill(
                requirement.requirement
            ):
                continue

            evaluation = self._evaluate_requirement(
                requirement.requirement,
                True,
                evidence,
            )

            required_evaluations.append(
                evaluation
            )

        preferred_evaluations = []

        for requirement in requirements.preferred_skills:

            evaluation = self._evaluate_requirement(
                requirement.requirement,
                False,
                evidence,
            )

            preferred_evaluations.append(
                evaluation
            )

        matched_required = [
            item.requirement
            for item in required_evaluations
            if item.supported
        ]

        missing_required = [
            item.requirement
            for item in required_evaluations
            if not item.supported
        ]

        professional_score = self._calculate_evidence_score(
            required_evaluations,
            "professional",
        )

        project_score = self._calculate_evidence_score(
            required_evaluations,
            "project",
        )

        domain_score = self._calculate_domain_score(
            candidate,
            requirements.domains,
        )

        experience_score = self._calculate_experience_score(
            candidate.total_experience_years,
            requirements.required_experience_years,
        )

        required_skill_score = self._calculate_required_score(
            required_evaluations
        )

        preferred_skill_score = self._calculate_required_score(
            preferred_evaluations
        )

        overall_score = (
            required_skill_score * 0.40
            + professional_score * 0.20
            + project_score * 0.10
            + domain_score * 0.10
            + experience_score * 0.10
            + preferred_skill_score * 0.10
        )

        overall_score = round(
            min(overall_score, 100),
            2,
        )

        career_transition_score = round(
            (
                project_score * 0.50
                + professional_score * 0.30
                + domain_score * 0.20
            ),
            2,
        )

        recommendation = self._recommend(
            overall_score,
            missing_required,
        )

        reasons = self._build_reasons(
            missing_required,
            matched_required,
            professional_score,
            project_score,
            experience_score,
        )

        return JobEvaluation(
            overall_score=overall_score,

            professional_score=round(
                professional_score,
                2,
            ),

            project_score=round(
                project_score,
                2,
            ),

            domain_score=round(
                domain_score,
                2,
            ),

            experience_score=round(
                experience_score,
                2,
            ),

            required_skills=required_evaluations,

            preferred_skills=preferred_evaluations,

            missing_required_skills=missing_required,

            matched_required_skills=matched_required,

            career_transition_score=career_transition_score,

            recommendation=recommendation,

            reasons=reasons,
        )

    def _evaluate_requirement(
        self,
        requirement: str,
        required: bool,
        evidence: list[SkillEvidence],
    ) -> SkillEvaluation:

        requirement_lower = (
            requirement.strip().lower()
        )

        # First perform exact matching.
        exact_matches = [
            item
            for item in evidence
            if item.skill.strip().lower()
            == requirement_lower
            or skill_matches_keyword(
                item.skill,
                requirement,
            )
        ]

        if exact_matches:

            best = self._select_best_evidence(
                exact_matches
            )

            return SkillEvaluation(
                requirement=requirement,
                required=required,
                supported=True,
                evidence_type=(
                    best.evidence_type.value
                ),
                evidence_source=best.source,
                similarity_score=100.0,
                confidence=1.0,
                reason=(
                    "The candidate profile explicitly "
                    "contains this skill."
                ),
            )
        # No exact match.

        # Second: deterministic skill ontology.
        #
        # Example:
        # Qdrant -> Vector Database
        # VxWorks -> RTOS

        ontology_matches = []

        for item in evidence:

            mapping = SkillOntology.match(
                item.skill,
                requirement,
            )

            if mapping is not None:
                ontology_matches.append(
                    (item, mapping)
                )

        if ontology_matches:

            # Prefer professional evidence.
            ontology_matches.sort(
                key=lambda pair: (
                    pair[0].evidence_type.value
                    != "professional"
                )
            )

            best, mapping = ontology_matches[0]

            return SkillEvaluation(
                requirement=requirement,
                required=required,
                supported=True,
                evidence_type=(
                    best.evidence_type.value
                ),
                evidence_source=best.source,
                similarity_score=(
                    mapping.confidence * 100
                ),
                confidence=mapping.confidence,
                reason=mapping.explanation,
            )
        # Use semantic similarity to find candidate evidence.
        best = None
        best_score = 0.0

        for item in evidence:

            score = self.semantic_matcher.similarity(
                requirement,
                item.skill,
            )

            if score > best_score:
                best_score = score
                best = item

        # Important:
        # Semantic similarity is NOT proof.
        #
        # Only send reasonably related evidence to
        # the Llama evidence judge.

        if best is not None and best_score >= 80:

            judgment = self.evidence_judge.judge(
                requirement,
                best,
            )

            return SkillEvaluation(
                requirement=requirement,
                required=required,
                supported=judgment.supported,
                evidence_type=(
                    best.evidence_type.value
                ),
                evidence_source=best.source,
                similarity_score=best_score,
                confidence=judgment.confidence,
                reason=judgment.reason,
            )

        return SkillEvaluation(
            requirement=requirement,
            required=required,
            supported=False,
            similarity_score=best_score,
            confidence=0.0,
            reason="No sufficient candidate evidence found.",
        )

    @staticmethod
    def _select_best_evidence(
        evidence: list[SkillEvidence],
    ) -> SkillEvidence:

        # Professional evidence is stronger than project evidence.
        professional = [
            item
            for item in evidence
            if item.evidence_type.value
            == "professional"
        ]

        if professional:
            return professional[0]

        return evidence[0]

    @staticmethod
    def _calculate_required_score(
        evaluations: list[SkillEvaluation],
    ) -> float:

        if not evaluations:
            return 100.0

        supported = sum(
            1
            for item in evaluations
            if item.supported
        )

        return (
            supported
            / len(evaluations)
        ) * 100

    @staticmethod
    def _calculate_evidence_score(
        evaluations: list[SkillEvaluation],
        evidence_type: str,
    ) -> float:

        relevant = [
            item
            for item in evaluations
            if item.supported
            and item.evidence_type
            == evidence_type
        ]

        if not relevant:
            return 0.0

        return (
            len(relevant)
            / len(evaluations)
        ) * 100

    @staticmethod
    def _calculate_domain_score(
        candidate: CandidateProfile,
        job_domains: list[str],
    ) -> float:

        if not job_domains:
            return 100.0

        candidate_domains = {
            domain.lower()
            for domain in candidate.domains
        }

        matched = 0

        for domain in job_domains:

            domain_lower = domain.lower()

            if any(
                domain_lower in candidate_domain
                or candidate_domain in domain_lower
                for candidate_domain
                in candidate_domains
            ):
                matched += 1

        return (
            matched
            / len(job_domains)
        ) * 100

    @staticmethod
    def _calculate_experience_score(
        candidate_years: float,
        required_years: float | None,
    ) -> float:

        if required_years is None:
            return 100.0

        if candidate_years >= required_years:
            return 100.0

        if required_years <= 0:
            return 100.0

        return min(
            candidate_years
            / required_years
            * 100,
            100,
        )

    @staticmethod
    def _recommend(
        score: float,
        missing_required: list[str],
    ) -> str:

        # Hard gate:
        # missing required skills means we never
        # automatically apply.

        if missing_required:

            if score >= 70:
                return "REVIEW"

            return "REJECT"

        if score >= 80:
            return "APPLY"

        if score >= 60:
            return "REVIEW"

        return "REJECT"

    @staticmethod
    def _build_reasons(
        missing_required,
        matched_required,
        professional_score,
        project_score,
        experience_score,
    ):

        reasons = []

        if matched_required:
            reasons.append(
                "Matched required skills: "
                + ", ".join(matched_required)
            )

        if missing_required:
            reasons.append(
                "Missing required skills: "
                + ", ".join(missing_required)
            )

        if professional_score >= 70:
            reasons.append(
                "Strong professional evidence."
            )

        elif professional_score > 0:
            reasons.append(
                "Some professional evidence exists."
            )

        if project_score >= 70:
            reasons.append(
                "Strong project-based evidence."
            )

        if experience_score >= 100:
            reasons.append(
                "Experience requirement satisfied."
            )

        return reasons