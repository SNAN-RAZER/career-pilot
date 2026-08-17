import re


def skill_matches_keyword(skill: str, keyword: str) -> bool:

    left = (skill or "").lower().strip()
    right = (keyword or "").lower().strip()

    if not left or not right:
        return False

    if left == right:
        return True

    if min(len(left), len(right)) <= 2:
        short = left if len(left) <= 2 else right
        long = right if len(left) <= 2 else left
        return short in skill_atoms(long)

    left_atoms = skill_atoms(left)
    right_atoms = skill_atoms(right)

    if left in right_atoms or right in left_atoms:
        return True

    if left_atoms & right_atoms:
        return True

    return _as_word(left, right) or _as_word(right, left)


def skill_atoms(text: str) -> set[str]:

    body = str(text or "").strip().lower()

    if not body:
        return set()

    if ":" in body:
        body = body.split(":", 1)[1].strip() or body

    parts = re.split(r"[,;/|•·\n]+", body)
    atoms = set()

    for part in parts:
        name = part.strip(" -•·")

        if name:
            atoms.add(name)

    return atoms


def _as_word(needle: str, haystack: str) -> bool:

    pattern = (
        r"(?<![a-z0-9+#./-])"
        + re.escape(needle)
        + r"(?![a-z0-9+#./-])"
    )

    return re.search(pattern, haystack) is not None
