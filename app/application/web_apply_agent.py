from inspect import isawaitable

from pydantic import BaseModel, Field

from app.application.applicant_packet import (
    build_applicant_packet,
)
from app.application.web_apply_planner import (
    classify_page_stage,
    plan_next_action,
)
from app.application.web_browser import (
    BrowserSession,
    PlaywrightBrowser,
)
from app.llm.lmstudio_client import LMStudioClient
from app.models.candidate import CandidateProfile
from app.models.tailored_resume import TailoredResume


class WebApplyReport(BaseModel):

    status: str
    apply_url: str
    current_url: str = ""
    filled: list[str] = Field(default_factory=list)
    steps: list[str] = Field(default_factory=list)
    thoughts: list[str] = Field(default_factory=list)
    stages: list[str] = Field(default_factory=list)
    message: str
    submitted: bool = False


class WebApplyAgent:

    def __init__(
        self,
        browser: BrowserSession | None = None,
        headed: bool = True,
        max_steps: int = 50,
    ):
        self.browser = browser
        self.headed = headed
        self.max_steps = max_steps
        self.llm = LMStudioClient()
        self.use_llm = browser is None

    def _think(self, prompt: str) -> str:

        try:
            import requests

            response = requests.get(
                f"{self.llm.base_url}/models",
                timeout=1.5,
            )

            if not response.ok:
                return ""
        except Exception:
            return ""

        if not str(self.llm.llm_model or "").strip():
            return ""

        return self.llm.chat(
            [
                {
                    "role": "system",
                    "content": (
                        "You are Career-Pilot, a browser agent that "
                        "applies to jobs on live career sites. "
                        "Application pages are multi-step: listing, "
                        "Apply button, login, then form fields. "
                        "Decide the next UI action from what you see. "
                        "Never invent candidate facts. Return JSON only."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            max_tokens=900,
        )

    async def _use(self, method, *args):

        result = method(*args)

        if isawaitable(result):
            return await result

        return result

    async def run(
        self,
        apply_url: str,
        candidate: CandidateProfile,
        resume_path: str | None = None,
        allow_submit: bool = False,
        job_title: str = "",
        company: str = "",
        tailored: TailoredResume | None = None,
    ) -> WebApplyReport:

        packet = build_applicant_packet(
            candidate,
            tailored,
        )
        owns_browser = self.browser is None
        browser = self.browser or await PlaywrightBrowser.create(
            headed=self.headed
        )
        filled_ids: set[str] = set()
        filled_fields: list[str] = []
        steps: list[str] = []
        thoughts: list[str] = []
        stages: list[str] = []
        last_url = ""
        last_signature = ""
        idle_rounds = 0
        goal = {
            "title": job_title,
            "company": company,
            "start_url": apply_url,
        }

        try:
            await self._use(browser.goto, apply_url)
            await self._use(browser.wait, 2000)
            current_url = apply_url

            for _ in range(self.max_steps):
                snapshot = await self._use(browser.snapshot)
                current_url = snapshot.url
                stage = classify_page_stage(snapshot)
                stages.append(stage)
                signature = (
                    f"{snapshot.url}|{stage}|"
                    f"{len(snapshot.elements)}|"
                    f"{(snapshot.title or '')[:80]}"
                )

                if snapshot.url != last_url:
                    filled_ids = set()
                    last_url = snapshot.url
                    idle_rounds = 0

                action = plan_next_action(
                    snapshot,
                    packet,
                    filled_ids,
                    allow_submit=allow_submit,
                    think=self._think if self.use_llm else None,
                    goal=goal,
                    history=steps,
                    stage=stage,
                )

                if action.thought:
                    thoughts.append(action.thought)

                steps.append(
                    f"[{stage}] {action.type}: {action.reason}"
                )

                if action.type == "blocked":
                    return WebApplyReport(
                        status="blocked",
                        apply_url=apply_url,
                        current_url=current_url,
                        filled=filled_fields,
                        steps=steps,
                        thoughts=thoughts,
                        stages=stages,
                        message=action.reason,
                    )

                if action.type == "done":
                    if signature == last_signature:
                        idle_rounds += 1
                    else:
                        idle_rounds = 0
                        last_signature = signature

                    if idle_rounds < 2 and stage in {
                        "listing",
                        "gate",
                        "loading",
                    }:
                        await self._use(browser.wait, 2500)
                        continue

                    return WebApplyReport(
                        status=(
                            "filled"
                            if filled_fields
                            else "needs_review"
                        ),
                        apply_url=apply_url,
                        current_url=current_url,
                        filled=filled_fields,
                        steps=steps,
                        thoughts=thoughts,
                        stages=stages,
                        message=(
                            action.reason
                            if filled_fields
                            else (
                                "I opened the job page and looked for "
                                "Apply / form fields. Nothing more was "
                                "clickable or fillable from this page "
                                f"state ({stage}). Check the Chrome "
                                "window and run Web agent apply again "
                                "if a form appeared."
                            )
                        ),
                    )

                if action.type == "wait":
                    milliseconds = 2000

                    if action.value and str(action.value).isdigit():
                        milliseconds = int(action.value)

                    await self._use(browser.wait, milliseconds)
                    last_signature = signature
                    continue

                if action.type == "fill" and action.element_id:
                    try:
                        await self._use(
                            browser.fill,
                            action.element_id,
                            action.value or "",
                        )
                    except Exception as exc:
                        steps.append(
                            f"fill skipped ({action.element_id}): {exc}"
                        )
                        filled_ids.add(action.element_id)
                        continue

                    filled_ids.add(action.element_id)
                    filled_fields.append(action.reason)
                    last_signature = signature
                    continue

                if action.type == "upload" and action.element_id:
                    if not resume_path:
                        steps.append("skip upload: no resume file")
                        filled_ids.add(action.element_id)
                        continue

                    try:
                        await self._use(
                            browser.upload,
                            action.element_id,
                            resume_path,
                        )
                    except Exception as exc:
                        steps.append(f"upload skipped: {exc}")
                        filled_ids.add(action.element_id)
                        continue

                    filled_ids.add(action.element_id)
                    filled_fields.append("resume")
                    last_signature = signature
                    continue

                if action.type in {"click", "submit"} and action.element_id:
                    try:
                        await self._use(
                            browser.click,
                            action.element_id,
                        )
                    except Exception as exc:
                        steps.append(
                            f"click skipped ({action.element_id}): {exc}"
                        )
                        filled_ids.add(action.element_id)
                        continue

                    filled_ids.add(action.element_id)
                    # New page / modal / form may appear after click.
                    filled_ids = set()
                    last_signature = ""
                    idle_rounds = 0

                    if action.type == "submit":
                        return WebApplyReport(
                            status="submitted",
                            apply_url=apply_url,
                            current_url=current_url,
                            filled=filled_fields,
                            steps=steps,
                            thoughts=thoughts,
                            stages=stages,
                            message="Clicked submit on the company form.",
                            submitted=True,
                        )

                    await self._use(browser.wait, 1200)
                    continue

            return WebApplyReport(
                status="filled" if filled_fields else "needs_review",
                apply_url=apply_url,
                current_url=current_url,
                filled=filled_fields,
                steps=steps,
                thoughts=thoughts,
                stages=stages,
                message=(
                    "Stopped after the step limit. "
                    "Review the open browser window."
                ),
            )
        finally:
            if owns_browser and not self.headed:
                try:
                    await self._use(browser.close)
                except Exception:
                    pass
