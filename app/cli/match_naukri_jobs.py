import argparse

from app.config.naukri import NaukriSettings
from app.matching.decision_engine import DecisionEngine
from app.matching.job_evaluator import JobEvaluator
from app.matching.job_ranker import JobRanker
from app.matching.target_matcher import TargetMatcher
from app.naukri.client import create_naukri_client
from app.pipeline.job_search_pipeline import JobSearchPipeline
from app.profile.profile_manager import ProfileManager
from app.profile.target_profile_builder import (
    build_target_profile,
)
from app.sources.job_collector import JobCollector
from app.sources.naukri_adapter import NaukriAdapter

PROFILE_PATH = "data/profile/candidate.json"


def main():

    parser = argparse.ArgumentParser(
        description=(
            "Search Naukri using the typed role, "
            "not extra hardcoded titles."
        ),
    )
    parser.add_argument(
        "--role",
        required=True,
        help="Exact search query, e.g. AI Engineer",
    )
    parser.add_argument(
        "--location",
        default="",
    )
    parser.add_argument(
        "--pages",
        type=int,
        default=1,
    )
    parser.add_argument(
        "--experience",
        type=int,
        default=2,
    )
    parser.add_argument(
        "--job-age",
        type=int,
        default=3,
    )
    parser.add_argument(
        "--profile",
        default=PROFILE_PATH,
    )
    args = parser.parse_args()

    print("=" * 70)
    print("CAREERPILOT - REAL NAUKRI JOB MATCHING")
    print("=" * 70)

    candidate = ProfileManager(
        args.profile
    ).load()
    target_profile = build_target_profile(
        candidate
    )

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

    print("\nSearching Naukri...")

    result = pipeline.run(
        candidate=candidate,
        target_profile=target_profile,
        queries=[args.role],
        location=args.location,
        pages=args.pages,
        experience=args.experience,
        job_age=args.job_age,
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

        if ranking.location:
            print(
                f"Location: "
                f"{ranking.location}"
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
