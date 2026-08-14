import re


STOPWORDS = {
    "a",
    "an",
    "and",
    "the",
    "to",
    "of",
    "in",
    "for",
    "with",
    "on",
    "at",
    "by",
    "or",
    "as",
    "is",
    "are",
    "be",
    "from",
    "this",
    "that",
    "we",
    "you",
    "your",
    "our",
    "will",
    "using",
    "use",
    "experience",
    "required",
    "requirements",
    "job",
    "role",
    "work",
    "team",
    "strong",
    "good",
    "knowledge",
    "ability",
    "years",
}


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(
        r"[A-Za-z][A-Za-z0-9+#/.]{1,}",
        text,
    )

    seen: set[str] = set()
    keywords: list[str] = []

    for token in tokens:
        normalized = token.lower()

        if normalized in STOPWORDS:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        keywords.append(token)

    return keywords
