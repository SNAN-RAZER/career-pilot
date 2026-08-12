from app.config.naukri import NaukriSettings
from app.naukri.client import create_naukri_client
from app.sources.naukri_adapter import NaukriAdapter


def main():

    settings = NaukriSettings()

    print("=" * 60)
    print("CAREERPILOT - NAUKRI SEARCH")
    print("=" * 60)

    print("\nConnecting to Naukri...")

    client = create_naukri_client(
        username=settings.username,
        password=settings.password,
    )

    adapter = NaukriAdapter(client)

    print("Connected.")
    print()

    jobs = adapter.search(
        keyword="AI Engineer",
        location="Bangalore",
        page=1,
        job_age=3,
        experience=2,
        results_per_page=20,
    )

    print(
        f"Jobs collected: {len(jobs)}"
    )

    print("-" * 60)

    for index, job in enumerate(
        jobs,
        start=1,
    ):

        print(
            f"\n#{index} {job.title}"
        )

        print(
            f"Company: {job.company}"
        )

        print(
            f"Location: {job.location}"
        )

        print(
            f"Experience: "
            f"{job.raw_data.get('experience')}"
        )

        print(
            f"Salary: {job.salary}"
        )

        print(
            f"Posted: {job.posted_date}"
        )

        print(
            f"URL: {job.url}"
        )

        print()


if __name__ == "__main__":
    main()