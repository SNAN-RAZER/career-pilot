import json
import re
from pydantic import BaseModel, Field


class PageElement(BaseModel):

    id: str
    tag: str = "input"
    type: str = "text"
    name: str = ""
    label: str = ""
    placeholder: str = ""
    value: str = ""
    text: str = ""
    autocomplete: str = ""
    dom_id: str = ""
    required: bool = False


class PageSnapshot(BaseModel):

    url: str = ""
    title: str = ""
    text: str = ""
    elements: list[PageElement] = Field(
        default_factory=list
    )


class AgentAction(BaseModel):

    type: str
    element_id: str | None = None
    value: str | None = None
    reason: str = ""
    thought: str = ""


FIELD_MAP = [
    (["first name", "given name", "firstname", "fname", "given-name"], "first_name"),
    (["last name", "surname", "family name", "lastname", "lname", "family-name"], "last_name"),
    (["full name", "legal name", "your name", "candidate name", "applicant name", "autocomplete name"], "full_name"),
    (["e-mail", "email", "mail id"], "email"),
    (["phone", "mobile", "cell", "tel"], "phone"),
    (["linkedin"], "linkedin"),
    (["github"], "github"),
    (["city", "location", "current location"], "location"),
    (["years of experience", "total experience", "experience (years)"], "years_experience"),
    (["current company", "current employer", "organization", "company name"], "current_company"),
    (["current title", "current role", "current designation"], "current_title"),
    (["cover letter", "additional information", "about yourself", "summary"], "summary"),
    (["skills", "technical skills"], "skills"),
    (["degree", "qualification"], "degree"),
    (["university", "college", "institution", "school"], "institution"),
]


SITE_SEARCH_HINTS = (
    "search jobs",
    "search for jobs",
    "enter skills",
    "skills / designations",
    "designations / companies",
    "job title, skill",
    "type keyword",
    "find jobs",
    "keyword / designation",
    "suggestor",
    "qptextbox",
    "naukri search",
)

SKIP_HINTS = (
    "salary",
    "ctc",
    "notice period",
    "visa",
    "sponsor",
    "authorized to work",
    "gender",
    "race",
    "ethnicity",
    "disability",
    "veteran",
    "password",
    "otp",
    "captcha",
    "date of birth",
    "ssn",
    "aadhaar",
    "pan ",
)


COOKIE_HINTS = (
    "accept all",
    "accept cookies",
    "accept all cookies",
    "i agree",
    "got it",
    "allow all",
)

SSO_HINTS = (
    "sign in with google",
    "continue with google",
    "sign in with microsoft",
    "continue with microsoft",
    "use your google account",
    "continue as ",
)


def plan_next_action(
    snapshot: PageSnapshot,
    packet: dict[str, str],
    filled_ids: set[str],
    allow_submit: bool = False,
    think=None,
    goal: dict | None = None,
    history: list[str] | None = None,
    stage: str | None = None,
) -> AgentAction:

    haystack = (
        f"{snapshot.title} {snapshot.text[:4000]}"
    ).lower()
    stage = stage or classify_page_stage(snapshot)

    if _looks_like_captcha(haystack, snapshot):
        return AgentAction(
            type="blocked",
            thought="This looks like a CAPTCHA or bot check.",
            reason="CAPTCHA or bot check is on this page.",
        )

    if think is not None:
        llm_action = plan_with_llm(
            snapshot,
            packet,
            filled_ids,
            allow_submit,
            think,
            goal=goal,
            history=history or [],
            stage=stage,
        )

        if llm_action is not None:
            return llm_action

    return plan_heuristic(
        snapshot,
        packet,
        filled_ids,
        allow_submit,
        haystack,
        stage=stage,
    )


def classify_page_stage(snapshot: PageSnapshot) -> str:

    haystack = (
        f"{snapshot.title} {snapshot.text[:3000]}"
    ).lower()
    elements = snapshot.elements
    blobs = [_element_blob(item) for item in elements]

    if _looks_like_captcha(haystack, snapshot):
        return "captcha"

    has_password = any(
        item.type == "password" or "password" in blob
        for item, blob in zip(elements, blobs)
    )
    has_sso = any(
        any(hint in blob for hint in SSO_HINTS)
        for blob in blobs
    )

    if has_password or has_sso:
        if re.search(
            r"\b(sign in|log in|login|create account)\b",
            haystack,
        ) or has_sso:
            return "auth"

    fillable = [
        item
        for item in elements
        if item.tag in {"input", "textarea", "select"}
        and (item.type or "").lower()
        not in {"hidden", "submit", "button", "checkbox", "radio"}
        and not _is_site_search_control(item, snapshot)
    ]
    has_file = any(_is_file(item) for item in elements)
    has_apply = any(_is_nav_button(blob) for blob in blobs)
    has_submit = any(_is_submit(blob) for blob in blobs)
    has_next = any(
        re.search(r"\b(next|continue|save and continue)\b", blob)
        for blob in blobs
    )

    if has_file or len(fillable) >= 2:
        return "form"

    if len(fillable) == 1 and (has_next or has_submit):
        return "form"

    if has_apply and len(fillable) == 0:
        return "gate"

    if has_next and len(fillable) == 0:
        return "gate"

    if "loading" in haystack or "please wait" in haystack:
        return "loading"

    if has_apply:
        return "listing"

    if re.search(
        r"\b(thank you|application received|successfully submitted)\b",
        haystack,
    ):
        return "confirmation"

    return "unknown"


def plan_heuristic(
    snapshot: PageSnapshot,
    packet: dict[str, str],
    filled_ids: set[str],
    allow_submit: bool,
    haystack: str,
    stage: str = "unknown",
) -> AgentAction:

    sso = _find_sso_button(snapshot, filled_ids)

    if sso is not None:
        return AgentAction(
            type="click",
            element_id=sso.id,
            reason="Use the existing Google/SSO login on this Chrome profile.",
        )

    cookie = _find_cookie_button(snapshot, filled_ids)

    if cookie is not None:
        return AgentAction(
            type="click",
            element_id=cookie.id,
            reason="Dismiss cookie banner.",
        )

    if stage == "auth" or _looks_like_login(snapshot, haystack):
        if _find_sso_button(snapshot, filled_ids) is None:
            return AgentAction(
                type="blocked",
                reason=(
                    "This page still needs a login. "
                    "In the open Chrome window, sign in "
                    "(Google account is fine), then click "
                    "Web agent apply again."
                ),
            )

    mapped = _plan_mapped_fill(snapshot, packet, filled_ids)

    if mapped is not None:
        return mapped

    # Prefer opening the form over giving up.
    for element in snapshot.elements:
        if element.id in filled_ids:
            continue

        if _is_site_search_control(element, snapshot):
            continue

        blob = _element_blob(element)

        if _is_nav_button(blob) and not _is_submit(blob):
            return AgentAction(
                type="click",
                element_id=element.id,
                reason=(
                    "Open the next application step "
                    "(Apply / Continue). Fields often appear after this."
                ),
            )

    if stage in {"loading", "gate", "listing"}:
        return AgentAction(
            type="wait",
            value="2500",
            reason=(
                "Waiting for the page to finish loading "
                "or for the application form to appear."
            ),
        )

    if allow_submit:
        for element in snapshot.elements:
            blob = _element_blob(element)

            if _is_submit(blob):
                return AgentAction(
                    type="submit",
                    element_id=element.id,
                    reason="Submit using filled profile data.",
                )

    return AgentAction(
        type="done",
        reason=(
            "No Apply button and no fillable profile fields "
            "are visible on this page yet."
        ),
    )


def _element_blob(element: PageElement) -> str:

    return " ".join(
        [
            element.tag,
            element.type,
            element.name,
            element.label,
            element.placeholder,
            element.text,
            element.autocomplete,
            element.dom_id,
        ]
    ).lower()


def _plan_mapped_fill(
    snapshot: PageSnapshot,
    packet: dict[str, str],
    filled_ids: set[str],
) -> AgentAction | None:

    for element in snapshot.elements:
        if element.id in filled_ids:
            continue

        blob = _element_blob(element)

        if _should_skip(blob):
            continue

        if _is_site_search_control(element, snapshot):
            continue

        if _is_file(element):
            return AgentAction(
                type="upload",
                element_id=element.id,
                reason="Upload the tailored resume.",
            )

        key = _match_packet_key(element, packet)

        if key and not str(element.value or "").strip():
            return AgentAction(
                type="fill",
                element_id=element.id,
                value=packet[key],
                reason=f"Fill {key} from profile JSON.",
            )

    return None


def _match_packet_key(
    element: PageElement,
    packet: dict[str, str],
) -> str | None:

    blob = _element_blob(element)
    input_type = (element.type or "").lower()
    auto = (element.autocomplete or "").lower()

    if input_type in {"email"} and "email" in packet:
        return "email"

    if input_type in {"tel", "phone"} and "phone" in packet:
        return "phone"

    if auto in packet:
        return auto

    auto_map = {
        "email": "email",
        "tel": "phone",
        "phone": "phone",
        "given-name": "first_name",
        "family-name": "last_name",
        "name": "full_name",
        "organization": "current_company",
        "url": "linkedin" if "linkedin" in packet else None,
    }

    mapped = auto_map.get(auto)

    if mapped and mapped in packet:
        return mapped

    for hints, key in FIELD_MAP:
        if key not in packet:
            continue

        if any(hint in blob for hint in hints):
            return key

    if element.tag == "textarea" and packet.get("cover_letter"):
        return "cover_letter"

    for key in packet:
        label = key.replace("_", " ")

        if label in blob or key in blob:
            return key

    if (
        "name" in blob
        and "company" not in blob
        and "user" not in blob
        and "full_name" in packet
    ):
        return "full_name"

    return None


def _should_skip(blob: str) -> bool:

    return any(hint in blob for hint in SKIP_HINTS)


def _is_site_search_control(
    element: PageElement,
    snapshot: PageSnapshot,
) -> bool:

    blob = _element_blob(element)
    url = (snapshot.url or "").lower()

    if any(hint in blob for hint in SITE_SEARCH_HINTS):
        return True

    if (element.type or "").lower() == "search":
        return True

    if "naukri.com" not in url:
        return False

    if element.tag in {"input", "textarea"}:
        if (element.type or "").lower() in {
            "email",
            "tel",
            "phone",
            "file",
            "password",
            "hidden",
        }:
            return False

        return any(
            hint in blob
            for hint in (
                "keyword",
                "designation",
                "job title",
                "location",
                "experience",
                "search",
            )
        )

    if element.tag in {"button", "a"}:
        return blob.strip() in {
            "search",
            "search jobs",
        }

    return False


def _is_file(element: PageElement) -> bool:

    return element.type == "file"


def _is_nav_button(blob: str) -> bool:

    return bool(
        re.search(
            r"\b(apply|next|continue|start application|"
            r"i'm interested|i am interested)\b",
            blob,
        )
    )


def _is_submit(blob: str) -> bool:

    return bool(
        re.search(
            r"\b(submit|submit application|send application)\b",
            blob,
        )
    )


def _looks_like_captcha(
    haystack: str,
    snapshot: PageSnapshot,
) -> bool:

    if "captcha" in haystack or "i'm not a robot" in haystack:
        return True

    return any(
        "captcha" in _element_blob(element)
        for element in snapshot.elements
    )


def _looks_like_login(
    snapshot: PageSnapshot,
    haystack: str,
) -> bool:

    has_password = any(
        element.type == "password"
        or "password" in _element_blob(element)
        for element in snapshot.elements
    )

    loginish = bool(
        re.search(
            r"\b(sign in|log in|login|create account|"
            r"forgot password)\b",
            haystack,
        )
    )

    return has_password and loginish


def _find_sso_button(
    snapshot: PageSnapshot,
    filled_ids: set[str],
) -> PageElement | None:

    for element in snapshot.elements:
        if element.id in filled_ids:
            continue

        blob = _element_blob(element)

        if any(hint in blob for hint in SSO_HINTS):
            return element

    return None


def _find_cookie_button(
    snapshot: PageSnapshot,
    filled_ids: set[str],
) -> PageElement | None:

    for element in snapshot.elements:
        if element.id in filled_ids:
            continue

        blob = _element_blob(element)

        if any(hint in blob for hint in COOKIE_HINTS):
            return element

    return None


def plan_with_llm(
    snapshot: PageSnapshot,
    packet: dict[str, str],
    filled_ids: set[str],
    allow_submit: bool,
    think,
    goal: dict | None = None,
    history: list[str] | None = None,
    stage: str = "unknown",
) -> AgentAction | None:

    allowed = {element.id: element for element in snapshot.elements}
    packet_values = {
        value.lower() for value in packet.values() if value
    }
    listing = []

    for element in snapshot.elements[:80]:
        listing.append(
            f"{element.id} tag={element.tag} type={element.type} "
            f"label={element.label!r} name={element.name!r} "
            f"placeholder={element.placeholder!r} "
            f"autocomplete={element.autocomplete!r} "
            f"text={element.text!r} value={element.value!r}"
        )

    goal = goal or {}
    history_text = "\n".join((history or [])[-10:]) or "(none)"
    facts = json.dumps(packet, ensure_ascii=False)

    prompt = f"""
You are Career-Pilot, an agent applying to a real job in a live browser.

GOAL: Apply for "{goal.get('title') or 'this role'}" at "{goal.get('company') or 'this company'}".
Start URL (already opened):
{goal.get('start_url') or snapshot.url}

CURRENT PAGE STAGE: {stage}
Stages mean:
- listing: job detail page — look for Apply / Apply on company website / I'm interested
- gate: Apply/Continue exists but the form is not open yet — click it
- auth: login / SSO — click Google/Microsoft if available; else blocked
- form: name/email/phone/resume/questions visible — fill from PROFILE FACTS
- loading: page still changing — wait
- confirmation: already submitted — done
- unknown: inspect elements and choose the best next move

IMPORTANT REALITY OF CAREER SITES:
Application UIs are multi-step. You often see ONLY an Apply button first.
Fields appear AFTER you click Apply / Next / Continue.
Never conclude "no fields" while an Apply/Continue button is visible.
Never search Naukri or type the job title into a search box.

Use only PROFILE FACTS. Never invent salary, visa, gender, password, OTP, or skills.

Decide ONE next action:
1. Cookie banner → click accept.
2. Login wall with Google/Microsoft → click SSO.
3. Job listing / gate with Apply → click Apply (or company-site apply).
4. Form open → fill the next empty profile field, or upload resume.
5. After fills, click Next / Continue if present.
6. Skip salary, visa, gender, race, password, OTP, and job-search boxes.
7. If one question is not in PROFILE FACTS, fill another field instead.
   type=blocked only for CAPTCHA or a login wall you cannot pass.
8. element_id MUST be an id from the list (e0, e1, ...).
9. Do not submit unless submit is allowed. Prefer done when the form is ready.

PROFILE FACTS:
{facts}

RECENT STEPS:
{history_text}

URL: {snapshot.url}
TITLE: {snapshot.title}
PAGE TEXT:
{snapshot.text[:2200]}

CLICKABLE / FILLABLE ELEMENTS:
{chr(10).join(listing) or '(none visible)'}

Submit is {'allowed' if allow_submit else 'NOT allowed — leave submit to the human'}.

Return ONLY JSON:
{{"thought":"what stage am I in and why this action","type":"fill|click|upload|wait|done|blocked|submit","element_id":"e0","value":"","reason":"what this achieves"}}

For fill, value must be a PROFILE FACT value or key (email, first_name, phone, ...).
If the form is still opening, use type=wait with value="2500".
""".strip()

    try:
        raw = think(prompt)
    except Exception:
        return None

    parsed = _parse_action_json(raw)

    if not parsed:
        return None

    action_type = str(parsed.get("type") or "").lower()
    element_id = parsed.get("element_id")
    value = parsed.get("value")
    thought = str(parsed.get("thought") or "").strip()
    reason = str(parsed.get("reason") or thought or "Agent page action")

    if action_type not in {
        "fill",
        "click",
        "upload",
        "wait",
        "done",
        "blocked",
        "submit",
    }:
        return None

    if action_type == "done" and stage in {"listing", "gate", "loading"}:
        for element in snapshot.elements:
            if element.id in filled_ids:
                continue

            blob = _element_blob(element)

            if _is_nav_button(blob) and not _is_submit(blob):
                return AgentAction(
                    type="click",
                    element_id=element.id,
                    thought=thought,
                    reason=(
                        "Form fields are not open yet; "
                        "clicking Apply/Continue first."
                    ),
                )

        if stage == "loading":
            return AgentAction(
                type="wait",
                thought=thought,
                value="2500",
                reason="Waiting for the application form to appear.",
            )

    if action_type == "submit" and not allow_submit:
        return AgentAction(
            type="done",
            thought=thought,
            reason=(
                "The form looks ready. Submit it yourself "
                "in the Chrome window."
            ),
        )

    if action_type == "blocked" and _is_false_missing_field(reason, thought):
        mapped = _plan_mapped_fill(snapshot, packet, filled_ids)

        if mapped is not None:
            mapped.thought = thought
            return mapped

        return None

    if action_type in {"fill", "click", "upload", "submit"}:
        element_id = _resolve_element_id(
            element_id,
            snapshot,
            filled_ids,
        )

        if element_id not in allowed:
            mapped = _plan_mapped_fill(snapshot, packet, filled_ids)

            if mapped is not None:
                mapped.thought = thought
                return mapped

            # If the model pointed at a label but Apply exists, open the form.
            for element in snapshot.elements:
                blob = _element_blob(element)

                if _is_nav_button(blob) and not _is_submit(blob):
                    return AgentAction(
                        type="click",
                        element_id=element.id,
                        thought=thought,
                        reason=(
                            "Could not resolve that control; "
                            "opening the next Apply step instead."
                        ),
                    )

            return None

        if element_id in filled_ids and action_type in {"fill", "click"}:
            return None

        element = allowed.get(element_id)

        if element is not None and _is_site_search_control(
            element,
            snapshot,
        ):
            return None

    if action_type == "fill":
        element = allowed.get(element_id)
        grounded = _ground_fill_value(
            str(value or ""),
            packet,
            packet_values,
        )

        if not grounded and element is not None:
            key = _match_packet_key(element, packet)

            if key:
                grounded = packet[key]

        if not grounded:
            mapped = _plan_mapped_fill(
                snapshot,
                packet,
                filled_ids | {str(element_id)},
            )

            if mapped is not None:
                mapped.thought = thought
                return mapped

            return None

        value = grounded

        if element is not None and _should_skip(_element_blob(element)):
            mapped = _plan_mapped_fill(
                snapshot,
                packet,
                filled_ids | {element.id},
            )

            if mapped is not None:
                mapped.thought = (
                    thought
                    + " Skipped an HR-only question; filling a profile field instead."
                )
                return mapped

            return AgentAction(
                type="wait",
                thought=thought,
                value="1500",
                reason=(
                    "Skipped a question that is not in your "
                    "profile JSON: "
                    f"{element.label or element.name or element.id}."
                ),
            )

    return AgentAction(
        type=action_type,
        element_id=element_id,
        value=value,
        reason=reason,
        thought=thought,
    )


def _is_false_missing_field(reason: str, thought: str) -> bool:

    blob = f"{reason} {thought}".lower()

    return any(
        hint in blob
        for hint in (
            "not found",
            "field not found",
            "not in your profile",
            "not in profile",
            "missing from",
            "no field",
            "couldn't find",
            "could not find",
        )
    )


def _resolve_element_id(
    raw,
    snapshot: PageSnapshot,
    filled_ids: set[str],
) -> str | None:

    if raw is None:
        return None

    token = str(raw).strip()

    if token in {element.id for element in snapshot.elements}:
        return token

    needle = token.lower()

    for element in snapshot.elements:
        if element.id in filled_ids:
            continue

        blob = _element_blob(element)

        if needle and needle in blob:
            return element.id

    return token or None


def _ground_fill_value(
    value: str,
    packet: dict[str, str],
    packet_values: set[str],
) -> str | None:

    raw = value.strip()

    if not raw:
        return None

    if raw in packet:
        return packet[raw]

    if raw.lower() in packet_values:
        for item in packet.values():
            if item.lower() == raw.lower():
                return item

    return None


def _parse_action_json(raw: str) -> dict | None:

    if not raw:
        return None

    text = re.sub(
        r"^\s*```(?:json)?\s*",
        "",
        raw.strip(),
        flags=re.I,
    )
    text = re.sub(r"\s*```\s*$", "", text).strip()

    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict) and "parameters" not in parsed:
            return parsed
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{[^{}]+\}", text)

    if not match:
        return None

    try:
        parsed = json.loads(match.group(0))
    except json.JSONDecodeError:
        return None

    if isinstance(parsed, dict) and "parameters" not in parsed:
        return parsed

    return None

