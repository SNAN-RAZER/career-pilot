import html
import re


def strip_job_html(text: str) -> str:

    if not text:
        return ""

    cleaned = re.sub(r"(?i)<br\s*/?>", "\n", text)
    cleaned = re.sub(r"(?i)</li>", "\n", cleaned)
    cleaned = re.sub(r"(?i)<li[^>]*>", "- ", cleaned)
    cleaned = re.sub(r"(?i)</p>", "\n", cleaned)
    cleaned = re.sub(r"(?i)</h[1-6]>", "\n", cleaned)
    cleaned = re.sub(r"<[^>]+>", " ", cleaned)
    cleaned = html.unescape(cleaned)
    cleaned = cleaned.replace("??", "'")
    cleaned = re.sub(r"[ \t]+", " ", cleaned)
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned.strip()
