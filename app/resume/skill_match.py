import re


def skill_matches_keyword(skill: str, keyword: str) -> bool:

    left = (skill or "").lower().strip()
    right = (keyword or "").lower().strip()

    if not left or not right:
        return False

    if left == right:
        return True

    if min(len(left), len(right)) <= 2:
        return False

    return _as_word(left, right) or _as_word(right, left)


def _as_word(needle: str, haystack: str) -> bool:

    pattern = (
        r"(?<![a-z0-9+#])"
        + re.escape(needle)
        + r"(?![a-z0-9+#])"
    )

    return re.search(pattern, haystack) is not None
