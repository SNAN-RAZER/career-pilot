from app.models.job_evaluation import JobEvaluation
from app.models.job_ranking import JobRanking


class JobRanker:

    def rank(
        self,
        evaluations: list[
            tuple[str, str, JobEvaluation]
        ],
    ) -> list[JobRanking]:

        rankings = []

        for item in evaluations:

            location = None

            if len(item) >= 5:
                (
                    job_id,
                    title,
                    company,
                    evaluation,
                    location,
                ) = item[:5]
            elif len(item) == 4:
                job_id, title, company, evaluation = item
            else:
                title, company, evaluation = item
                job_id = ""

            score = self._calculate_score(
                evaluation
            )

            rankings.append(
                JobRanking(
                    rank=0,
                    job_id=job_id,
                    title=title,
                    company=company,
                    location=location,
                    score=round(
                        score,
                        2,
                    ),
                    recommendation=(
                        evaluation.recommendation
                    ),
                    missing_requirements=(
                        evaluation
                        .missing_required_skills
                    ),
                    reasons=evaluation.reasons,
                )
            )

        rankings.sort(
            key=lambda item: item.score,
            reverse=True,
        )

        for index, ranking in enumerate(
            rankings,
            start=1,
        ):
            ranking.rank = index

        return rankings

    @staticmethod
    def _calculate_score(
        evaluation: JobEvaluation,
    ) -> float:

        required_score = (
            JobRanker
            ._required_skill_score(
                evaluation
            )
        )

        professional_score = (
            evaluation.professional_score
        )

        transition_score = (
            evaluation.career_transition_score
        )

        domain_score = (
            evaluation.domain_score
        )

        experience_score = (
            evaluation.experience_score
        )

        preferred_score = (
            JobRanker
            ._preferred_skill_score(
                evaluation
            )
        )

        score = (
            required_score * 0.40
            + professional_score * 0.20
            + transition_score * 0.15
            + domain_score * 0.10
            + experience_score * 0.10
            + preferred_score * 0.05
        )

        return min(
            score,
            100,
        )

    @staticmethod
    def _required_skill_score(
        evaluation: JobEvaluation,
    ) -> float:

        total = len(
            evaluation.required_skills
        )

        if total == 0:
            return 100.0

        supported = sum(
            1
            for skill
            in evaluation.required_skills
            if skill.supported
        )

        return (
            supported
            / total
        ) * 100

    @staticmethod
    def _preferred_skill_score(
        evaluation: JobEvaluation,
    ) -> float:

        total = len(
            evaluation.preferred_skills
        )

        if total == 0:
            return 100.0

        supported = sum(
            1
            for skill
            in evaluation.preferred_skills
            if skill.supported
        )

        return (
            supported
            / total
        ) * 100