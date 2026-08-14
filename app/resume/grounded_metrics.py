from calendar import monthrange
from datetime import date


def parse_year_month(value: str | None) -> date | None:

    if not value:
        return None

    text = value.strip()

    if text.lower() == "present":
        return date.today()

    if (
        len(text) >= 7
        and text[4] == "-"
        and text[:4].isdigit()
        and text[5:7].isdigit()
    ):
        year = int(text[:4])
        month = int(text[5:7])

        if 1 <= month <= 12:
            last_day = monthrange(year, month)[1]
            return date(year, month, last_day)

    return None


def months_between(
    start: str | None,
    end: str | None,
) -> int:

    start_date = parse_year_month(start)

    if start_date is None:
        return 0

    end_date = parse_year_month(end) or date.today()

    months = (
        (end_date.year - start_date.year) * 12
        + (end_date.month - start_date.month)
        + 1
    )

    return max(months, 0)


def duration_label(
    start: str | None,
    end: str | None,
) -> str:

    months = months_between(start, end)

    if months <= 0:
        return ""

    years, leftover = divmod(months, 12)

    parts = []

    if years:
        parts.append(
            f"{years} year" + ("s" if years != 1 else "")
        )

    if leftover and not years:
        parts.append(
            f"{leftover} month"
            + ("s" if leftover != 1 else "")
        )
    elif leftover and years:
        parts.append(
            f"{leftover} month"
            + ("s" if leftover != 1 else "")
        )

    return " ".join(parts)


def tools_line(technologies: list[str]) -> str:

    unique = []
    seen = set()

    for item in technologies:
        key = item.lower()

        if key in seen:
            continue

        seen.add(key)
        unique.append(item)

    if not unique:
        return ""

    return (
        f"Tools ({len(unique)}): "
        + ", ".join(unique)
    )
