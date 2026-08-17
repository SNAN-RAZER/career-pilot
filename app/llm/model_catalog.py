import subprocess

import requests


def list_chat_models(
    kind: str,
    base_url: str,
    headers: dict | None = None,
) -> list[str]:

    return [
        name
        for name in _list_all_models(kind, base_url, headers)
        if not _is_embedding(name)
    ]


def list_embedding_models(
    kind: str,
    base_url: str,
    headers: dict | None = None,
) -> list[str]:

    return [
        name
        for name in _list_all_models(kind, base_url, headers)
        if _is_embedding(name)
    ]


def _list_all_models(
    kind: str,
    base_url: str,
    headers: dict | None = None,
) -> list[str]:

    kind = (kind or "").lower()
    base_url = (base_url or "").rstrip("/")
    headers = headers or {}

    if kind == "anthropic":
        return _openai_style_models(base_url, headers)

    if kind == "ollama":
        return _unique(
            _ollama_tags(base_url)
            + _ollama_cli()
            + _openai_style_models(base_url, headers)
        )

    if kind == "lmstudio":
        return _unique(
            _lmstudio_v0_models(base_url, headers)
            + _openai_style_models(base_url, headers)
        )

    return _openai_style_models(base_url, headers)


def _host_root(base_url: str) -> str:

    if base_url.endswith("/v1"):
        return base_url[:-3]

    return base_url


def _openai_style_models(
    base_url: str,
    headers: dict,
) -> list[str]:

    try:
        response = requests.get(
            f"{base_url}/models",
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    names = []

    for item in data.get("data") or data.get("models") or []:
        name = _item_name(item)

        if name:
            names.append(name)

    return names


def _lmstudio_v0_models(
    base_url: str,
    headers: dict,
) -> list[str]:

    root = _host_root(base_url)

    try:
        response = requests.get(
            f"{root}/api/v0/models",
            headers=headers,
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    names = []

    for item in data.get("data") or data.get("models") or []:
        name = _item_name(item)

        if name:
            names.append(name)

    return names


def _ollama_tags(base_url: str) -> list[str]:

    root = _host_root(base_url)

    try:
        response = requests.get(
            f"{root}/api/tags",
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
    except Exception:
        return []

    names = []

    for item in data.get("models") or []:
        name = ""

        if isinstance(item, dict):
            name = str(
                item.get("name") or item.get("model") or ""
            )
        elif isinstance(item, str):
            name = item

        if name:
            names.append(name)

    return names


def _ollama_cli() -> list[str]:

    try:
        completed = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=8,
            check=False,
        )
    except Exception:
        return []

    if completed.returncode != 0:
        return []

    names = []

    for line in completed.stdout.splitlines()[1:]:
        name = line.strip().split()[0] if line.strip() else ""

        if name and name.lower() != "name":
            names.append(name)

    return names


def _item_name(item) -> str:

    if isinstance(item, str):
        return item.strip()

    if not isinstance(item, dict):
        return ""

    return str(
        item.get("id")
        or item.get("name")
        or item.get("model")
        or ""
    ).strip()


def _is_embedding(name: str) -> bool:

    lowered = name.lower()

    return any(
        token in lowered
        for token in (
            "embed",
            "nomic-embed",
            "text-embedding",
            "bge-",
        )
    )


def _unique(names: list[str]) -> list[str]:

    return list(dict.fromkeys(names))
