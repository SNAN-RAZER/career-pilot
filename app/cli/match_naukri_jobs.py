from app.config.naukri import NaukriSettings
from app.matching.decision_engine import DecisionEngine
from app.matching.job_evaluator import JobEvaluator
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.models.candidate import CandidateProfile
from app.models.target_profile import TargetProfile
from app.naukri.client import create_naukri_client
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.sources.job_collector import JobCollector
from app.sources.naukri_adapter import NaukriAdapter


def build_candidate() -> CandidateProfile:

    return CandidateProfile(
        name="CareerPilot Candidate",

        target_roles=[
            "AI Engineer",
            "Agentic AI Engineer",
            "Gen AI Engineer",
            "Generative AI Engineer",
            "RAG Engineer",
            "LLM Engineer",
            "AI Software Engineer",
        ],

        total_experience_years=4.0,

        professional_summary=(
            "Software engineer with professional "
            "embedded systems experience and hands-on "
            "AI, RAG and automation projects."
        ),

        skills=[
            "Python",
            "C",
            "Embedded C",
            "Ada95",
            "VxWorks",
            "RTOS",
            "Git",
            "Docker",
            "LangChain",
            "Qdrant",
            "Ollama",
            "RAG",
            "LLM",
            "REST APIs",
        ],

        domains=[
            "AI",
            "Generative AI",
            "RAG",
            "Software Development",
            "Embedded Systems",
            "Aerospace",
        ],

        preferred_locations=[
            "Bengaluru",
            "Bangalore",
            "Remote",
        ],
    )


def build_target_profile() -> TargetProfile:

    return TargetProfile(

        target_roles=[
            "AI Engineer",
            "Agentic AI Engineer",
            "Gen AI Engineer",
            "Generative AI Engineer",
            "RAG Engineer",
            "LLM Engineer",
            "AI Software Engineer",
        ],

        excluded_roles=[
            "AI Research Scientist",
            "Research Scientist",
            "Machine Learning Researcher",
        ],

        target_domains=[
            "AI",
            "Generative AI",
            "RAG",
            "LLM",
            "Agentic AI",
        ],

        preferred_locations=[
            "Bengaluru",
            "Bangalore",
            "Remote",
        ],

        minimum_match_score=70.0,

        auto_apply_score=85.0,

        allow_project_based_transition=True,

        require_professional_experience=False,

        max_experience_years=5.0,
    )


def main():

    print("=" * 70)
    print("CAREERPILOT - REAL NAUKRI JOB MATCHING")
    print("=" * 70)

    settings = NaukriSettings()

    print("\nConnecting to Naukri...")

    naukri_client = create_naukri_client(
        username=settings.username,
        password=settings.password,
    )

    print("Connected.")

    adapter = NaukriAdapter(
        naukri_client
    )

    collector = JobCollector(
        adapter
    )

    pipeline = JobSearchPipeline(
        collector=collector,

        evaluator=JobEvaluator(),

        target_matcher=TargetMatcher(),

        decision_engine=DecisionEngine(),

        ranker=JobRanker(),
    )

    candidate = build_candidate()

    target_profile = build_target_profile()

    print("\nSearching Naukri...")

    result = pipeline.run(

        candidate=candidate,

        target_profile=target_profile,

        queries=[
            "AI Engineer",
            "Agentic AI Engineer",
            "Gen AI Engineer",
            "RAG Engineer",
            "LLM Engineer",
        ],

        location="Bangalore",

        pages=1,

        experience=2,

        job_age=3,
    )

    print()
    print("=" * 70)
    print("CAREERPILOT RESULTS")
    print("=" * 70)

    print(
        f"\nJobs collected: "
        f"{result.collected_jobs}"
    )

    print(
        f"Target-relevant jobs: "
        f"{result.relevant_jobs}"
    )

    print(
        f"Rejected by target matcher: "
        f"{result.rejected_by_target}"
    )

    print()
    print("=" * 70)
    print("RANKED JOBS")
    print("=" * 70)

    for ranking in result.rankings:

        print()
        print(
            f"#{ranking.rank} "
            f"{ranking.title}"
        )

        print(
            f"Company: "
            f"{ranking.company}"
        )

        print(
            f"Score: "
            f"{ranking.score:.2f}%"
        )

        print(
            f"Decision: "
            f"{ranking.recommendation}"
        )

        if ranking.missing_requirements:

            print("Missing requirements:")

            for requirement in (
                ranking.missing_requirements
            ):

                print(
                    f"  - {requirement}"
                )

        if ranking.reasons:

            print("Reasons:")

            for reason in ranking.reasons:

                print(
                    f"  - {reason}"
                )

        print("-" * 70)


if __name__ == "__main__":
    main()