import os
import uuid
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

SETTINGS_PATH = Path("data/llm/settings.json")


DEFAULT_PROVIDERS = [
    {
        "id": "lmstudio-local",
        "kind": "lmstudio",
        "label": "LM Studio",
        "base_url": os.getenv(
            "LM_STUDIO_BASE_URL",
            "http://localhost:1234/v1",
        ),
        "api_key": "",
        "chat_model": os.getenv(
            "LLM_MODEL",
            "",
        ),
        "embedding_model": os.getenv(
            "EMBEDDING_MODEL",
            "",
        ),
    },
    {
        "id": "ollama-local",
        "kind": "ollama",
        "label": "Ollama",
        "base_url": os.getenv(
            "OLLAMA_BASE_URL",
            "http://localhost:11434/v1",
        ),
        "api_key": "",
        "chat_model": os.getenv("OLLAMA_MODEL", ""),
        "embedding_model": "",
    },
    {
        "id": "openai",
        "kind": "openai",
        "label": "OpenAI",
        "base_url": "https://api.openai.com/v1",
        "api_key": os.getenv("OPENAI_API_KEY", ""),
        "chat_model": os.getenv(
            "OPENAI_MODEL",
            "gpt-4o-mini",
        ),
        "embedding_model": "text-embedding-3-small",
    },
    {
        "id": "anthropic",
        "kind": "anthropic",
        "label": "Anthropic",
        "base_url": "https://api.anthropic.com/v1",
        "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
        "chat_model": os.getenv(
            "ANTHROPIC_MODEL",
            "claude-sonnet-4-5",
        ),
        "embedding_model": "",
    },
]


def _empty() -> dict:

    return {
        "active_id": "lmstudio-local",
        "providers": [
            dict(item) for item in DEFAULT_PROVIDERS
        ],
    }


def load_settings() -> dict:

    import json

    if not SETTINGS_PATH.exists():
        data = _empty()
        save_settings(data)
        return data

    loaded = json.loads(
        SETTINGS_PATH.read_text(encoding="utf-8")
    )

    if not isinstance(loaded, dict):
        return _empty()

    providers = loaded.get("providers") or []

    if not providers:
        loaded = _empty()
        save_settings(loaded)
        return loaded

    collapsed = _collapse_duplicate_providers(loaded)

    if collapsed != loaded:
        save_settings(collapsed)

    return collapsed


def _normalize_url(url: str) -> str:

    return str(url or "").strip().rstrip("/").lower()


_BUILTIN_IDS = {
    "lmstudio-local",
    "ollama-local",
    "openai",
    "anthropic",
}


def _collapse_duplicate_providers(data: dict) -> dict:

    providers = list(data.get("providers") or [])
    chosen: dict[tuple[str, str], dict] = {}
    order: list[tuple[str, str]] = []
    dropped_ids: dict[str, str] = {}

    for item in providers:
        key = (
            str(item.get("kind") or ""),
            _normalize_url(item.get("base_url") or ""),
        )

        if key not in chosen:
            chosen[key] = dict(item)
            order.append(key)
            continue

        keep = chosen[key]
        incoming = dict(item)
        keep_builtin = keep.get("id") in _BUILTIN_IDS
        incoming_builtin = incoming.get("id") in _BUILTIN_IDS

        if incoming_builtin and not keep_builtin:
            if not incoming.get("chat_model"):
                incoming["chat_model"] = keep.get(
                    "chat_model"
                ) or ""
            if not incoming.get("api_key"):
                incoming["api_key"] = keep.get("api_key") or ""
            dropped_ids[str(keep.get("id"))] = str(
                incoming.get("id")
            )
            chosen[key] = incoming
            continue

        if incoming.get("chat_model") and not keep.get(
            "chat_model"
        ):
            keep["chat_model"] = incoming["chat_model"]

        if incoming.get("api_key") and not keep.get("api_key"):
            keep["api_key"] = incoming["api_key"]

        dropped_ids[str(incoming.get("id"))] = str(
            keep.get("id")
        )

    merged = [chosen[key] for key in order]
    active_id = str(data.get("active_id") or "")

    if active_id in dropped_ids:
        active_id = dropped_ids[active_id]

    if active_id not in {item.get("id") for item in merged}:
        active_id = merged[0]["id"] if merged else ""

    return {
        **data,
        "active_id": active_id,
        "providers": merged,
    }


def save_settings(data: dict) -> None:

    import json

    SETTINGS_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )
    SETTINGS_PATH.write_text(
        json.dumps(data, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def get_active() -> dict:

    data = load_settings()
    active_id = data.get("active_id")

    for item in data.get("providers") or []:
        if item.get("id") == active_id:
            return dict(item)

    providers = data.get("providers") or []

    if providers:
        return dict(providers[0])

    return dict(DEFAULT_PROVIDERS[0])


def set_active(
    provider_id: str,
    chat_model: str | None = None,
    embedding_model: str | None = None,
) -> dict:

    data = load_settings()
    found = None

    for item in data.get("providers") or []:
        if item.get("id") == provider_id:
            found = item
            if chat_model:
                item["chat_model"] = chat_model
            if embedding_model:
                item["embedding_model"] = embedding_model
            break

    if found is None:
        raise ValueError("Unknown LLM provider.")

    if not str(found.get("chat_model") or "").strip():
        raise ValueError(
            "Select a chat model before activating "
            "this provider."
        )

    data["active_id"] = provider_id
    save_settings(data)
    return dict(found)


def upsert_provider(payload: dict) -> dict:

    data = load_settings()
    kind = str(payload.get("kind") or "custom").strip()
    base_url = str(
        payload.get("base_url") or ""
    ).strip().rstrip("/")
    provider_id = str(payload.get("id") or "").strip()

    if not provider_id:
        for item in data.get("providers") or []:
            same_host = (
                item.get("kind") == kind
                and _normalize_url(item.get("base_url") or "")
                == _normalize_url(base_url)
            )

            if same_host:
                provider_id = str(item.get("id") or "")
                break

    provider_id = provider_id or uuid.uuid4().hex[:10]

    record = {
        "id": provider_id,
        "kind": kind,
        "label": str(
            payload.get("label") or "Custom API"
        ).strip(),
        "base_url": base_url,
        "api_key": str(payload.get("api_key") or ""),
        "chat_model": str(
            payload.get("chat_model") or ""
        ).strip(),
        "embedding_model": str(
            payload.get("embedding_model") or ""
        ).strip(),
    }

    if not record["base_url"]:
        raise ValueError("base_url is required.")

    providers = data.setdefault("providers", [])
    replaced = False

    for index, item in enumerate(providers):
        if item.get("id") == provider_id:
            if not record["api_key"]:
                record["api_key"] = item.get("api_key") or ""
            if not record["chat_model"]:
                record["chat_model"] = (
                    item.get("chat_model") or ""
                )
            if not record["embedding_model"]:
                record["embedding_model"] = (
                    item.get("embedding_model") or ""
                )
            providers[index] = record
            replaced = True
            break

    if not replaced:
        providers.append(record)

    if not data.get("active_id"):
        data["active_id"] = provider_id

    save_settings(data)
    return dict(record)


def delete_provider(provider_id: str) -> None:

    data = load_settings()
    providers = [
        item
        for item in data.get("providers") or []
        if item.get("id") != provider_id
    ]

    if len(providers) == len(data.get("providers") or []):
        raise ValueError("Unknown LLM provider.")

    data["providers"] = providers

    if data.get("active_id") == provider_id:
        data["active_id"] = (
            providers[0]["id"] if providers else ""
        )

    save_settings(data)


def public_provider(item: dict) -> dict:

    key = str(item.get("api_key") or "")
    masked = ""

    if key:
        masked = ("*" * max(len(key) - 4, 0)) + key[-4:]

    return {
        "id": item.get("id"),
        "kind": item.get("kind"),
        "label": item.get("label"),
        "base_url": item.get("base_url"),
        "has_api_key": bool(key),
        "api_key_masked": masked,
        "chat_model": item.get("chat_model") or "",
        "embedding_model": item.get("embedding_model") or "",
    }
