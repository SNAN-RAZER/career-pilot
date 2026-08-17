from app.matching.candidate_fit_prefilter import CandidateFitResult


def keep_non_java_jobs(
    candidate,
    jobs,
    queries=None,
    target_profile=None,
):

    results = {}

    for job in jobs:
        reject = "java" in (job.title or "").lower()
        results[job.job_id] = CandidateFitResult(
            matched=not reject,
            score=10.0 if reject else 80.0,
            matched_skills=[] if reject else ["Python"],
            reason="test stub",
        )

    return results
