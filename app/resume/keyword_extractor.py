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
    "such",
    "proficiency",
    "principles",
    "bachelor",
    "bachelors",
    "science",
    "electrical",
    "engineer",
    "engineering",
    "developer",
    "software",
    "including",
    "must",
    "have",
    "should",
    "preferred",
    "plus",
    "etc",
    "other",
    "related",
    "minimum",
    "excellent",
    "understanding",
    "familiarity",
    "candidate",
    "position",
    "description",
    "location",
    "production",
    "background",
    "profile",
    "keywords",
    "aligned",
    "targeting",
    "responsibilities",
    "about",
    "india",
    "chennai",
    "bangalore",
    "hyderabad",
    "pune",
    "remote",
    "chatbot",
    "chatbots",
}


def extract_keywords(text: str) -> list[str]:
    tokens = re.findall(
        r"[A-Za-z][A-Za-z0-9+#/.]{1,}",
        text,
    )

    seen: set[str] = set()
    keywords: list[str] = []

    for token in tokens:
        token = token.strip(".,;:()[]")
        normalized = token.lower()

        if normalized in STOPWORDS:
            continue

        if len(normalized) < 3 and normalized not in {
            "c",
            "r",
            "go",
            "c++",
            "c#",
        }:
            continue

        if normalized in seen:
            continue

        seen.add(normalized)
        keywords.append(token)

    return keywords
