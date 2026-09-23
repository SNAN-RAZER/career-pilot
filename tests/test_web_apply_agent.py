from asyncio import run as run_async

from app.application.applicant_packet import (
    build_applicant_packet,
)
from app.application.web_apply_agent import WebApplyAgent
from app.application.web_apply_planner import (
    PageElement,
    PageSnapshot,
    plan_next_action,
)
from app.application.web_browser import BrowserSession
from app.application.web_chrome import (
    chrome_is_locked,
    profile_in_use_message,
)
from app.models.candidate import CandidateProfile, Experience
from app.models.tailored_resume import TailoredResume


class FakeBrowser(BrowserSession):

    def __init__(self, pages: list[PageSnapshot]):
        self.pages = pages
        self.index = 0
        self.fills: dict[str, str] = {}
        self.uploads: list[str] = []
        self.clicks: list[str] = []

    def goto(self, url: str) -> None:
        self.index = 0

    def snapshot(self) -> PageSnapshot:
        page = self.pages[min(self.index, len(self.pages) - 1)]
        elements = []

        for element in page.elements:
            value = self.fills.get(element.id, element.value)
            elements.append(
                element.model_copy(update={"value": value})
            )

        return page.model_copy(update={"elements": elements})

    def fill(self, element_id: str, value: str) -> None:
        self.fills[element_id] = value

    def click(self, element_id: str) -> None:
        self.clicks.append(element_id)
        self.index = min(self.index + 1, len(self.pages) - 1)

    def upload(self, element_id: str, path: str) -> None:
        self.uploads.append(path)
        self.fills[element_id] = path

    def wait(self, milliseconds: int = 1200) -> None:
        return None

    def close(self) -> None:
        return None


def _candidate() -> CandidateProfile:

    return CandidateProfile(
        name="Nayaab Ahmed N",
        email="nayaabahmedn@gmail.com",
        phone="8197718054",
        skills=["Python", "VxWorks"],
        professional_summary="Embedded software developer.",
        experiences=[
            Experience(
                company="Cyient Limited",
                role="Software Developer",
            )
        ],
        preferred_locations=["Bangalore"],
        total_experience_years=4,
    )


def test_chrome_lock_explains_how_to_reuse_logins(tmp_path, monkeypatch):

    lock = tmp_path / "SingletonLock"
    lock.touch()
    monkeypatch.setattr('app.application.web_chrome.chrome_binary', lambda: 'chrome')

    assert chrome_is_locked(tmp_path)
    assert "remote-debugging-port" in profile_in_use_message()


def test_packet_uses_only_profile_facts():

    packet = build_applicant_packet(_candidate())

    assert packet["email"] == "nayaabahmedn@gmail.com"
    assert packet["first_name"] == "Nayaab"
    assert packet["current_company"] == "Cyient Limited"
    assert "C++" not in packet["skills"]

    tailored = TailoredResume(
        summary="Embedded engineer targeting VxWorks roles.",
        skills=["Python", "VxWorks", "RTOS"],
    )
    with_resume = build_applicant_packet(_candidate(), tailored)

    assert with_resume["summary"].startswith("Embedded engineer targeting")
    assert "RTOS" in with_resume["skills"]


def test_planner_fills_email_and_blocks_login():

    form = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Apply",
        elements=[
            PageElement(
                id="e0",
                label="Email",
                type="email",
            ),
            PageElement(
                id="e1",
                label="First name",
            ),
        ],
    )
    packet = build_applicant_packet(_candidate())
    action = plan_next_action(form, packet, set())

    assert action.type == "fill"
    assert action.value == "nayaabahmedn@gmail.com"

    unlabeled = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Apply",
        elements=[
            PageElement(id="e0", type="email"),
            PageElement(id="e1", type="tel"),
        ],
    )
    typed = plan_next_action(unlabeled, packet, set())

    assert typed.type == "fill"
    assert typed.value == "nayaabahmedn@gmail.com"

    login = PageSnapshot(
        url="https://workday.example.com",
        title="Sign in",
        text="Log in to continue",
        elements=[
            PageElement(
                id="e0",
                label="Email",
                type="email",
            ),
            PageElement(
                id="e1",
                label="Password",
                type="password",
            ),
        ],
    )
    blocked = plan_next_action(login, packet, set())

    assert blocked.type == "blocked"
    assert "login" in blocked.reason.lower()


def test_planner_clicks_google_sso():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://workday.example.com",
        title="Sign in",
        text="Log in to continue",
        elements=[
            PageElement(
                id="e0",
                label="Password",
                type="password",
            ),
            PageElement(
                id="e1",
                tag="button",
                text="Sign in with Google",
            ),
        ],
    )
    action = plan_next_action(page, packet, set())

    assert action.type == "click"
    assert action.element_id == "e1"


def test_llm_fill_must_use_profile_facts():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Apply",
        elements=[
            PageElement(id="e0", label="Email", type="email"),
        ],
    )

    def think(_prompt):
        return (
            '{"thought":"Empty email box on the form",'
            '"type":"fill","element_id":"e0",'
            '"value":"wrong@x.com","reason":"Fill email"}'
        )

    action = plan_next_action(
        page,
        packet,
        set(),
        think=think,
        goal={"title": "Embedded Engineer", "company": "Acme"},
    )

    assert action.thought
    assert action.type == "fill"
    assert action.value == "nayaabahmedn@gmail.com"


def test_agent_thinks_and_clicks_apply():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://careers.example.com/job/1",
        title="Embedded Engineer",
        text="We are hiring. Apply now.",
        elements=[
            PageElement(
                id="e0",
                tag="button",
                text="Apply now",
            )
        ],
    )

    def think(_prompt):
        assert "Embedded Engineer" in _prompt
        assert "CURRENT PAGE STAGE" in _prompt
        assert "multi-step" in _prompt.lower() or "AFTER you click" in _prompt
        return (
            '{"thought":"This is a job listing, not a form yet",'
            '"type":"click","element_id":"e0",'
            '"reason":"Open the application form"}'
        )

    action = plan_next_action(
        page,
        packet,
        set(),
        think=think,
        goal={"title": "Embedded Engineer", "company": "Acme"},
    )

    assert action.type == "click"
    assert action.element_id == "e0"
    assert "listing" in action.thought.lower()


def test_llm_done_on_listing_still_clicks_apply():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://careers.example.com/job/1",
        title="Embedded Engineer",
        text="We are hiring. Apply now.",
        elements=[
            PageElement(
                id="e0",
                tag="button",
                text="Apply now",
            )
        ],
    )

    def think(_prompt):
        return (
            '{"thought":"No form fields visible",'
            '"type":"done","element_id":"",'
            '"reason":"Nothing to fill"}'
        )

    action = plan_next_action(
        page,
        packet,
        set(),
        think=think,
        goal={"title": "Embedded Engineer", "company": "Acme"},
    )

    assert action.type == "click"
    assert action.element_id == "e0"


def test_page_stage_listing_then_form():

    from app.application.web_apply_planner import (
        classify_page_stage,
    )

    listing = PageSnapshot(
        url="https://careers.example.com/job/1",
        title="Role",
        text="Apply now to join us",
        elements=[
            PageElement(id="e0", tag="button", text="Apply now"),
        ],
    )
    form = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Application",
        text="Please complete the form",
        elements=[
            PageElement(id="e0", label="Email", type="email"),
            PageElement(id="e1", label="Phone", type="tel"),
            PageElement(id="e2", type="file", label="Resume"),
        ],
    )

    assert classify_page_stage(listing) in {"listing", "gate"}
    assert classify_page_stage(form) == "form"


def test_planner_does_not_search_naukri_again():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://www.naukri.com/job-listings-123",
        title="Embedded Engineer",
        text="Apply on company website",
        elements=[
            PageElement(
                id="e0",
                label="Enter skills / designations",
                placeholder="Enter skills / designations",
            ),
            PageElement(
                id="e1",
                tag="button",
                text="Search",
            ),
            PageElement(
                id="e2",
                tag="button",
                text="Apply on company website",
            ),
        ],
    )

    def think(_prompt):
        assert "Do NOT search Naukri" in _prompt
        return (
            '{"thought":"This is a search box",'
            '"type":"fill","element_id":"e0",'
            '"value":"current_title","reason":"Find the job"}'
        )

    action = plan_next_action(
        page,
        packet,
        set(),
        think=think,
        goal={
            "title": "Embedded Engineer",
            "company": "Acme",
            "start_url": page.url,
        },
    )

    assert action.type == "click"
    assert action.element_id == "e2"


def test_llm_field_not_found_still_fills_email():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Apply",
        elements=[
            PageElement(id="e0", label="Email", type="email"),
            PageElement(id="e1", label="LinkedIn profile"),
        ],
    )

    def think(_prompt):
        return (
            '{"thought":"LinkedIn field not found in JSON",'
            '"type":"blocked","element_id":"e1",'
            '"reason":"Field not found in profile"}'
        )

    action = plan_next_action(
        page,
        packet,
        set(),
        think=think,
    )

    assert action.type == "fill"
    assert action.value == "nayaabahmedn@gmail.com"


def test_llm_can_target_a_field_by_label():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Apply",
        elements=[
            PageElement(id="e0", label="Email", type="email"),
        ],
    )

    def think(_prompt):
        return (
            '{"thought":"Fill the email box",'
            '"type":"fill","element_id":"Email",'
            '"value":"email","reason":"Use profile email"}'
        )

    action = plan_next_action(
        page,
        packet,
        set(),
        think=think,
    )

    assert action.type == "fill"
    assert action.element_id == "e0"
    assert action.value == "nayaabahmedn@gmail.com"


def test_planner_skips_salary_and_does_not_submit_by_default():

    packet = build_applicant_packet(_candidate())
    page = PageSnapshot(
        url="https://careers.example.com/apply",
        title="Apply",
        elements=[
            PageElement(id="e0", label="Expected CTC"),
            PageElement(
                id="e1",
                tag="button",
                text="Submit application",
            ),
        ],
    )

    action = plan_next_action(page, packet, set(), allow_submit=False)

    assert action.type == "done"


def test_agent_clicks_apply_then_fills_form():

    browser = FakeBrowser(
        [
            PageSnapshot(
                url="https://careers.example.com/job/1",
                title="Software Developer",
                text="Apply now",
                elements=[
                    PageElement(
                        id="e0",
                        tag="button",
                        text="Apply now",
                    ),
                ],
            ),
            PageSnapshot(
                url="https://careers.example.com/apply",
                title="Application",
                text="Complete your application",
                elements=[
                    PageElement(id="e0", label="Email", type="email"),
                    PageElement(id="e1", label="Phone"),
                    PageElement(id="e2", type="file", label="Resume"),
                ],
            ),
        ]
    )
    report = run_async(
        WebApplyAgent(browser=browser).run(
            "https://careers.example.com/job/1",
            _candidate(),
            resume_path="/tmp/resume.docx",
            allow_submit=False,
            job_title="Software Developer",
            company="Acme",
        )
    )

    assert browser.clicks == ["e0"]
    assert browser.fills["e0"] == "nayaabahmedn@gmail.com"
    assert browser.fills["e1"] == "8197718054"
    assert browser.uploads == ["/tmp/resume.docx"]
    assert report.status == "filled"
    assert "gate" in report.stages or "listing" in report.stages
    assert "form" in report.stages


def test_agent_fills_form_and_uploads_resume():

    browser = FakeBrowser(
        [
            PageSnapshot(
                url="https://careers.example.com/apply",
                title="Software Developer",
                elements=[
                    PageElement(id="e0", label="Email", type="email"),
                    PageElement(id="e1", label="Phone"),
                    PageElement(id="e2", type="file", label="Resume"),
                    PageElement(
                        id="e3",
                        tag="button",
                        text="Submit application",
                    ),
                ],
            )
        ]
    )
    report = run_async(
        WebApplyAgent(browser=browser).run(
            "https://careers.example.com/apply",
            _candidate(),
            resume_path="/tmp/resume.docx",
            allow_submit=False,
        )
    )

    assert report.status == "filled"
    assert browser.fills["e0"] == "nayaabahmedn@gmail.com"
    assert browser.fills["e1"] == "8197718054"
    assert browser.uploads == ["/tmp/resume.docx"]
    assert report.submitted is False
    assert not browser.clicks
