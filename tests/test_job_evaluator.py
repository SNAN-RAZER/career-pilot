from app.matching.job_evaluator import JobEvaluator
from app.profile.profile_manager import ProfileManager
from app.matching.decision_engine import DecisionEngine
from app.models.decision import Decision

PROFILE_PATH = "data/profile/candidate.json"


AI_JOB = """
We are looking for an AI Engineer with 3 to 5 years
of software development experience.

Required:
- Strong Python programming experience
- Experience with Large Language Models
- Experience building RAG applications
- Experience with vector databases
- Experience with LangChain
- Good understanding of REST APIs

Preferred:
- Experience with PyTorch
- Experience with AWS
- Experience deploying AI applications using Docker

The candidate should have a Bachelor's degree in Computer
Science, Information Technology, Electronics or a related
engineering field.

Experience in Generative AI is preferred.
"""


def test_complete_job_evaluation():

    profile_manager = ProfileManager(
        PROFILE_PATH
    )

    candidate = profile_manager.load()

    evaluator = JobEvaluator()

    result = evaluator.evaluate(
        candidate,
        AI_JOB,
    )

    print("\n")
    print("=" * 60)
    print("JOB EVALUATION")
    print("=" * 60)

    print(
        f"\nOverall Score: "
        f"{result.overall_score}%"
    )

    print(
        f"Professional Score: "
        f"{result.professional_score}%"
    )

    print(
        f"Project Score: "
        f"{result.project_score}%"
    )

    print(
        f"Domain Score: "
        f"{result.domain_score}%"
    )

    print(
        f"Experience Score: "
        f"{result.experience_score}%"
    )

    print(
        f"Career Transition Score: "
        f"{result.career_transition_score}%"
    )

    print(
        f"\nRecommendation: "
        f"{result.recommendation}"
    )

    print("\nRequired Skills:")

    for item in result.required_skills:

        status = (
            "✓"
            if item.supported
            else "✗"
        )

        print(
            f"{status} "
            f"{item.requirement} "
            f"[{item.evidence_type}] "
            f"{item.confidence:.2f}"
        )

    print("\nPreferred Skills:")

    for item in result.preferred_skills:

        status = (
            "✓"
            if item.supported
            else "✗"
        )

        print(
            f"{status} "
            f"{item.requirement}"
        )

    print("\nReasons:")

    for reason in result.reasons:
        print(f"- {reason}")

    print("=" * 60)

    assert result.overall_score >= 0
    assert result.overall_score <= 100

    assert result.recommendation in {
        "APPLY",
        "REVIEW",
        "REJECT",
    }

def test_explicit_candidate_skills_are_supported():

    profile_manager = ProfileManager(
        PROFILE_PATH
    )

    candidate = profile_manager.load()

    evaluator = JobEvaluator()

    result = evaluator.evaluate(
        candidate,
        """
        We are looking for a software engineer.

        Required:
        - Python
        - Docker
        - RAG
        """
    )

    results = {
        item.requirement.lower(): item
        for item in result.required_skills
    }

    assert results["python"].supported is True
    assert results["docker"].supported is True
    assert results["rag"].supported is True

def test_decision_engine_with_missing_requirement():

    profile_manager = ProfileManager(
        PROFILE_PATH
    )

    candidate = profile_manager.load()

    evaluator = JobEvaluator()

    evaluation = evaluator.evaluate(
        candidate,
        AI_JOB,
    )

    engine = DecisionEngine()

    decision = engine.decide(
        evaluation
    )

    print("\n")
    print("=" * 60)
    print("CAREER DECISION")
    print("=" * 60)

    print(
        f"\nDecision: {decision.decision.value}"
    )

    print(
        f"Match Score: "
        f"{decision.match_score}%"
    )

    print(
        f"Eligibility Score: "
        f"{decision.eligibility_score}%"
    )

    print(
        f"Transition Score: "
        f"{decision.career_transition_score}%"
    )

    print("\nBlockers:")

    for blocker in decision.blockers:

        print(
            f"- {blocker.requirement}: "
            f"{blocker.explanation}"
        )

    print("\nReasons:")

    for reason in decision.reasons:
        print(f"- {reason}")

    assert decision.decision in {
        Decision.APPLY,
        Decision.REVIEW,
        Decision.REJECT,
    }

    assert len(
        decision.blockers
    ) == 1

    assert (
        decision.blockers[0].requirement
        == "REST APIs"
    )