from pathlib import Path

from app.application.web_apply_planner import (
    PageElement,
    PageSnapshot,
)
from app.application.web_chrome import (
    CDP_URL,
    cdp_ready,
    chrome_binary,
    profile_in_use_message,
    start_debug_chrome,
)


class BrowserSession:

    def goto(self, url: str) -> None:
        raise NotImplementedError

    def snapshot(self) -> PageSnapshot:
        raise NotImplementedError

    def fill(self, element_id: str, value: str) -> None:
        raise NotImplementedError

    def click(self, element_id: str) -> None:
        raise NotImplementedError

    def upload(self, element_id: str, path: str) -> None:
        raise NotImplementedError

    def wait(self, milliseconds: int = 1200) -> None:
        raise NotImplementedError

    def close(self) -> None:
        raise NotImplementedError


class PlaywrightBrowser(BrowserSession):

    def __init__(self):
        self._ids: list = []
        self._owns_browser = False
        self._playwright = None
        self._context = None
        self._browser = None
        self._page = None

    @classmethod
    async def create(cls, headed: bool = True):
        try:
            from playwright.async_api import async_playwright
        except ImportError as exc:
            raise RuntimeError(
                "Playwright is not installed. "
                "Run: uv pip install playwright && "
                "playwright install chromium"
            ) from exc

        browser = cls()
        browser._playwright = await async_playwright().start()

        try:
            await browser._connect_chrome(headed)
        except Exception:
            await browser._playwright.stop()
            raise

        if browser._context is None:
            await browser._playwright.stop()
            raise RuntimeError(profile_in_use_message())

        if browser._context.pages:
            browser._page = browser._context.pages[0]
        else:
            browser._page = await browser._context.new_page()

        try:
            await browser._page.set_viewport_size(
                {"width": 1280, "height": 900}
            )
        except Exception:
            pass

        return browser

    async def _connect_chrome(self, headed: bool) -> None:

        if not cdp_ready():
            start_debug_chrome()

        try:
            await self._attach_cdp()
            return
        except Exception as first:
            try:
                start_debug_chrome()
                await self._attach_cdp()
                return
            except Exception as second:
                raise RuntimeError(
                    "Could not attach to Chrome. "
                    + profile_in_use_message()
                    + f"\n\nDetails: {second or first}"
                ) from second

    async def _attach_cdp(self) -> None:

        self._browser = (
            await self._playwright.chromium.connect_over_cdp(
                CDP_URL
            )
        )

        if self._browser.contexts:
            self._context = self._browser.contexts[0]
        else:
            self._context = await self._browser.new_context()

        self._owns_browser = False

    async def _launch_chrome(self, headed: bool) -> None:

        executable = chrome_binary()
        self._browser = await self._playwright.chromium.launch(
            headless=not headed,
            executable_path=executable,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self._context = await self._browser.new_context(
            viewport={"width": 1280, "height": 900}
        )
        self._owns_browser = True

    async def goto(self, url: str) -> None:

        if self._context is None:
            raise RuntimeError("Chrome is not connected.")

        try:
            self._page = await self._context.new_page()
        except Exception:
            if self._page is None:
                raise

        await self._page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=45000,
        )
        await self._page.wait_for_timeout(900)

    async def wait(self, milliseconds: int = 1200) -> None:

        await self._page.wait_for_timeout(int(milliseconds))

    async def snapshot(self) -> PageSnapshot:

        selector = (
            "input, textarea, select, button, a[href], "
            "[role='button'], [role='textbox'], "
            "[role='combobox'], [contenteditable='true']"
        )
        elements = []
        self._ids = []
        bodies = []
        index = 0

        frames = [self._page]
        frames.extend(self._page.frames)
        seen = set()

        for frame in frames:
            key = id(frame)

            if key in seen:
                continue

            seen.add(key)

            try:
                bodies.append(
                    (await frame.inner_text("body"))[:3000]
                )
            except Exception:
                pass

            try:
                locator = frame.locator(selector)
                count = min(await locator.count(), 70)
            except Exception:
                continue

            for offset in range(count):
                if index >= 100:
                    break

                handle = locator.nth(offset)

                try:
                    if not await handle.is_visible(timeout=250):
                        continue
                except Exception:
                    continue

                self._ids.append(handle)
                tag = "div"
                input_type = ""
                name = ""
                placeholder = ""
                autocomplete = ""
                dom_id = ""
                value = ""
                label = ""
                text = ""
                required = False

                try:
                    tag = (
                        (await handle.evaluate("el => el.tagName"))
                        or "DIV"
                    ).lower()
                    input_type = (
                        (await handle.get_attribute("type")) or tag
                    ).lower()
                    name = (await handle.get_attribute("name")) or ""
                    automation = (
                        await handle.get_attribute(
                            "data-automation-id"
                        )
                    ) or ""

                    if automation and not name:
                        name = automation
                    placeholder = (
                        await handle.get_attribute("placeholder")
                    ) or ""
                    autocomplete = (
                        await handle.get_attribute("autocomplete")
                    ) or ""
                    dom_id = (await handle.get_attribute("id")) or ""
                    label = (
                        await handle.get_attribute("aria-label")
                    ) or ""
                    text = ((await handle.inner_text()) or "")[:160]
                    required = (
                        await handle.get_attribute("required")
                    ) is not None
                except Exception:
                    pass

                if tag in {"input", "textarea"} and input_type not in {
                    "file",
                    "checkbox",
                    "radio",
                    "button",
                    "submit",
                    "hidden",
                }:
                    try:
                        value = await handle.input_value()
                    except Exception:
                        value = ""

                if not label:
                    try:
                        label = await handle.evaluate(
                            """el => {
                              const id = el.id;
                              if (id) {
                                const node = document.querySelector(
                                  `label[for="${CSS.escape(id)}"]`
                                );
                                if (node && node.innerText) {
                                  return node.innerText;
                                }
                              }
                              const parent = el.closest("label");
                              if (parent && parent.innerText) {
                                return parent.innerText;
                              }
                              const prev = el.previousElementSibling;
                              if (prev && prev.innerText) {
                                return prev.innerText;
                              }
                              const wrap = el.closest(
                                "[data-automation-id]"
                              );
                              return [
                                el.getAttribute("data-automation-id") || "",
                                wrap
                                  ? wrap.getAttribute("data-automation-id")
                                  : "",
                              ].filter(Boolean).join(" ");
                            }"""
                        ) or ""
                    except Exception:
                        label = ""

                elements.append(
                    PageElement(
                        id=f"e{index}",
                        tag=tag,
                        type=input_type or tag,
                        name=name,
                        label=label[:200],
                        placeholder=placeholder,
                        value=value or "",
                        text=text,
                        autocomplete=autocomplete,
                        dom_id=dom_id,
                        required=required,
                    )
                )
                index += 1

        return PageSnapshot(
            url=self._page.url,
            title=await self._page.title(),
            text="\n".join(bodies)[:8000],
            elements=elements,
        )

    async def fill(self, element_id: str, value: str) -> None:

        handle = self._by_id(element_id)
        await handle.click()

        try:
            await handle.fill(value, timeout=4000)
        except Exception:
            await handle.press("Control+A")
            await handle.type(value, delay=20)

    async def click(self, element_id: str) -> None:

        await self._by_id(element_id).click(timeout=5000)
        await self._page.wait_for_timeout(1500)

    async def upload(self, element_id: str, path: str) -> None:

        handle = self._by_id(element_id)
        await handle.set_input_files(str(Path(path)))

    async def close(self) -> None:

        if self._playwright is None:
            return

        if not self._owns_browser:
            await self._playwright.stop()
            return

        if self._context is not None:
            await self._context.close()

        if self._browser is not None:
            try:
                await self._browser.close()
            except Exception:
                pass

        await self._playwright.stop()

    def _by_id(self, element_id: str):

        raw = str(element_id or "")

        if not raw.startswith("e") or not raw[1:].isdigit():
            raise RuntimeError(
                f"Bad element id {element_id!r}. "
                "The agent must click a listed e0/e1 control."
            )

        index = int(raw[1:])

        if index < 0 or index >= len(self._ids):
            raise RuntimeError(
                f"Element {raw} is not on this page "
                f"({len(self._ids)} controls visible)."
            )

        return self._ids[index]
