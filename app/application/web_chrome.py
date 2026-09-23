import os
import shutil
import subprocess
import time
from pathlib import Path


CDP_URL = os.getenv(
    "CHROME_CDP_URL",
    "http://127.0.0.1:9222",
)

CDP_PORT = int(os.getenv("CHROME_CDP_PORT", "9222"))

CHROME_USER_DATA_DIR = os.getenv(
    "CHROME_USER_DATA_DIR",
    str(Path.home() / ".config/google-chrome"),
)

CHROME_PROFILE = os.getenv(
    "CHROME_PROFILE_DIRECTORY",
    "Default",
)

APPLY_PROFILE = Path(
    os.getenv(
        "CAREER_PILOT_CHROME_PROFILE",
        str(Path("data/browser/chrome-apply").resolve()),
    )
)




def chrome_user_data_dir() -> Path:

    return Path(CHROME_USER_DATA_DIR).expanduser()


def apply_profile_dir() -> Path:

    return Path(APPLY_PROFILE).expanduser()


def chrome_binary() -> str:

    for name in (
        "google-chrome-stable",
        "google-chrome",
        "chromium-browser",
        "chromium",
    ):
        found = shutil.which(name)

        if found:
            return found

    for root in (os.getenv("PROGRAMFILES"), os.getenv("PROGRAMFILES(X86)"), os.getenv("LOCALAPPDATA")):
        if root:
            for relative in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe"):
                candidate = Path(root) / relative
                if candidate.is_file():
                    return str(candidate)
    raise RuntimeError("Install Google Chrome or Microsoft Edge to use browser-assisted applications.")


def chrome_is_locked(user_data_dir: Path | None = None) -> bool:

    root = user_data_dir or chrome_user_data_dir()

    for name in (
        "SingletonLock",
        "SingletonSocket",
        "SingletonCookie",
    ):
        if (root / name).exists():
            return True

    return False


def cdp_ready(url: str | None = None) -> bool:

    try:
        import requests

        response = requests.get(
            f"{(url or CDP_URL).rstrip('/')}/json/version",
            timeout=0.6,
        )
        return response.ok
    except Exception:
        return False


def wait_for_cdp(seconds: float = 20) -> bool:

    deadline = time.time() + seconds

    while time.time() < deadline:
        if cdp_ready():
            return True

        time.sleep(0.4)

    return False


def seed_apply_profile() -> Path:

    dest = apply_profile_dir()
    dest.mkdir(parents=True, exist_ok=True)
    return dest



def start_debug_chrome() -> None:

    if cdp_ready():
        return

    profile = seed_apply_profile()
    binary = chrome_binary()

    log_path = profile / "launch.log"
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log = log_path.open("ab")

    subprocess.Popen(
        [
            binary,
            f"--remote-debugging-port={CDP_PORT}",
            f"--user-data-dir={profile}",
            "--no-first-run",
            "--no-default-browser-check",
            "--disable-blink-features=AutomationControlled",
            "--new-window",
        ],
        stdout=log,
        stderr=log,
        start_new_session=True,
    )

    if not wait_for_cdp(25):
        details = ""

        try:
            details = log_path.read_text(errors="ignore")[-800:]
        except OSError:
            details = ""

        raise RuntimeError(
            "Started Chrome for Career-Pilot but could not "
            f"reach {CDP_URL}. Keep the new Chrome window "
            "open and try again.\n"
            + (details or profile_in_use_message())
        )


def chrome_debug_command(user_data_dir: Path | None = None) -> str:

    profile = user_data_dir or apply_profile_dir()

    return (
        f"{chrome_binary()} "
        f"--remote-debugging-port={CDP_PORT} "
        f"--user-data-dir={profile}"
    )


def profile_in_use_message() -> str:

    return (
        "Career-Pilot opens its own Chrome window with "
        "debugging. Sign in there when requested. "
        "Your everyday Chrome can stay open. If attach "
        "fails, run:\n\n"
        f"{chrome_debug_command()}\n\n"
        "Then click Web agent apply again."
    )
