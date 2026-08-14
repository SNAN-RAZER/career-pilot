from pathlib import Path

from app.resume.source_document import (
    extract_contact,
    extract_resume_text,
    find_source_resume,
)


def test_extract_contact_from_resume_text():

    text = (
        "Nayaab Ahmed N\n"
        "nayaabahmedn@gmail.com\n"
        "8197718054\n"
        "https://github.com/nayaab\n"
    )

    contact = extract_contact(text)

    assert contact["email"] == (
        "nayaabahmedn@gmail.com"
    )
    assert "8197718054" in contact["phone"]
    assert "github.com/nayaab" in contact["github"]


def test_extract_txt_resume(tmp_path):

    path = tmp_path / "source_resume.txt"
    path.write_text(
        "Software developer using Python and VxWorks.",
        encoding="utf-8",
    )

    assert "Python" in extract_resume_text(path)


def test_find_source_resume(tmp_path):

    assert find_source_resume(tmp_path) is None

    resume = tmp_path / "source_resume.txt"
    resume.write_text("hello", encoding="utf-8")

    found = find_source_resume(tmp_path)

    assert found == resume
