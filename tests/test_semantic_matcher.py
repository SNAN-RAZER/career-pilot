from app.matching.semantic_matcher import SemanticMatcher


def test_related_concepts():

    matcher = SemanticMatcher()

    score = matcher.similarity(
        "VxWorks real time operating system",
        "real-time operating system software development",
    )

    print(
        f"\nRelated similarity: {score}"
    )

    assert score > 50


def test_unrelated_concepts():

    matcher = SemanticMatcher()

    score = matcher.similarity(
        "VxWorks real time operating system",
        "financial accounting and tax preparation",
    )

    print(
        f"\nUnrelated similarity: {score}"
    )

    assert score < 70