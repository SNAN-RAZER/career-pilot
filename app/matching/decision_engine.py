from app.models.decision import (
    BlockerType,
    CareerDecision,
    Decision,
    DecisionBlocker,
)
from app.models.job_evaluation import JobEvaluation


class DecisionEngine:

    AUTO_APPLY_SCORE = 80
    REVIEW_SCORE = 60

    def decide(
        self,
        evaluation: JobEvaluation,
    ) -> CareerDecision:

        blockers = []

        # -------------------------------------------------
        # 1. Missing mandatory requirements
        # -------------------------------------------------

        for requirement in (
            evaluation.missing_required_skills
        ):

            blockers.append(
                DecisionBlocker(
                    blocker_type=(
                        BlockerType.MISSING_REQUIRED_SKILL
                    ),
                    requirement=requirement,
                    severity="high",
                    explanation=(
                        "The job explicitly requires "
                        "this skill, but sufficient "
                        "candidate evidence was not found."
                    ),
                )
            )

        # -------------------------------------------------
        # 2. Calculate eligibility
        # -------------------------------------------------

        if blockers:

            eligibility_score = max(
                0,
                evaluation.overall_score
                - (len(blockers) * 10)
            )

        else:

            eligibility_score = (
                evaluation.overall_score
            )

        # -------------------------------------------------
        # 3. Determine decision
        # -------------------------------------------------

        if (
            evaluation.overall_score
            >= self.AUTO_APPLY_SCORE
            and not blockers
        ):

            decision = Decision.APPLY

        elif (
            evaluation.overall_score
            >= self.REVIEW_SCORE
        ):

            decision = Decision.REVIEW

        else:

            decision = Decision.REJECT

        reasons = []

        if blockers:

            reasons.append(
                f"{len(blockers)} mandatory "
                "requirement(s) require attention."
            )

        if (
            evaluation.professional_score
            >= 70
        ):

            reasons.append(
                "Strong professional experience alignment."
            )

        elif (
            evaluation.professional_score
            > 0
        ):

            reasons.append(
                "Some professional experience aligns "
                "with the role."
            )

        if (
            evaluation.project_score
            >= 70
        ):

            reasons.append(
                "Strong project-based evidence aligns "
                "with the role."
            )

        if (
            evaluation.career_transition_score
            >= 80
        ):

            reasons.append(
                "The role appears to be a strong "
                "career-transition opportunity."
            )

        return CareerDecision(
            decision=decision,

            match_score=round(
                evaluation.overall_score,
                2,
            ),

            eligibility_score=round(
                eligibility_score,
                2,
            ),

            career_transition_score=round(
                evaluation.career_transition_score,
                2,
            ),

            blockers=blockers,

            reasons=reasons,
        )