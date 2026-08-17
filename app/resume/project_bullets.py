import re


SENTENCE_SPLIT = re.compile(
    r"(?<=[.!?])\s+(?=[A-Z])"
)


def project_bullets(
    description: str,
    technologies: list[str] | None = None,
) -> list[str]:

    text = str(description or "").strip()
    bullets = []

    if not text:
        pass
    elif "\n" in text:
        for line in text.splitlines():
            line = _strip_bullet(line)

            if line:
                bullets.append(line)
    else:
        bullets = [
            part.strip()
            for part in SENTENCE_SPLIT.split(text)
            if part.strip()
        ]

    bullets = [_strip_bullet(item) for item in bullets]
    return [item for item in bullets if item]


def _strip_bullet(text: str) -> str:

    return re.sub(
        r"^[\s•\-\u2022*]+",
        "",
        str(text or "").strip(),
    ).strip()
