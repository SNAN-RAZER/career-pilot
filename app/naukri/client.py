from pathlib import Path
import sys


# ---------------------------------------------------------
# Make the standalone NopeRi "src" package importable.
# Keep this dependency isolated to this bridge.
# ---------------------------------------------------------

PROJECT_ROOT = Path(__file__).resolve().parents[2]

NOPE_RI_ROOT = (
    PROJECT_ROOT
    / "third_party"
    / "NopeRi"
)

if str(NOPE_RI_ROOT) not in sys.path:
    sys.path.insert(
        0,
        str(NOPE_RI_ROOT),
    )


from src.client.job_client import NaukriJobClient
from src.client.naukri_client import NaukriLoginClient


def create_naukri_client(
    username: str,
    password: str,
) -> NaukriJobClient:

    login_client = NaukriLoginClient(
        username=username,
        password=password,
    )

    login_client.login()

    return NaukriJobClient(
        login_client,
        use_pool=False,
    )