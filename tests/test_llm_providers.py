import json

from app.llm.lmstudio_client import LMStudioClient
from app.llm import provider_store


def test_public_provider_masks_api_key():

    shown = provider_store.public_provider(
        {
            "id": "openai",
            "kind": "openai",
            "label": "OpenAI",
            "base_url": "https://api.openai.com/v1",
            "api_key": "sk-test-secret-key",
            "chat_model": "gpt-4o-mini",
        }
    )

    assert shown["has_api_key"] is True
    assert "secret" not in shown["api_key_masked"]
    assert shown["api_key_masked"].endswith("key")
    assert "api_key" not in shown


def test_set_active_updates_chat_model(tmp_path, monkeypatch):

    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        provider_store,
        "SETTINGS_PATH",
        path,
    )
    provider_store.save_settings(
        {
            "active_id": "lmstudio-local",
            "providers": [
                {
                    "id": "lmstudio-local",
                    "kind": "lmstudio",
                    "label": "LM Studio",
                    "base_url": "http://localhost:1234/v1",
                    "api_key": "",
                    "chat_model": "old-model",
                },
                {
                    "id": "ollama-local",
                    "kind": "ollama",
                    "label": "Ollama",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "",
                    "chat_model": "llama3.2",
                },
            ],
        }
    )

    record = provider_store.set_active(
        "ollama-local",
        "llama3.2:latest",
    )

    assert record["id"] == "ollama-local"
    assert record["chat_model"] == "llama3.2:latest"
    saved = json.loads(path.read_text())
    assert saved["active_id"] == "ollama-local"


def test_openai_client_uses_bearer_and_model(monkeypatch):

    captured = {}

    class FakeResponse:
        ok = True

        def raise_for_status(self):
            return None

        def json(self):
            return {
                "choices": [
                    {
                        "message": {
                            "content": "ok",
                        }
                    }
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(
        "app.llm.lmstudio_client.requests.post",
        fake_post,
    )

    client = LMStudioClient(
        base_url="https://api.openai.com/v1",
        llm_model="gpt-4o-mini",
        api_key="sk-test",
        kind="openai",
    )
    text = client.chat(
        [{"role": "user", "content": "hi"}],
    )

    assert text == "ok"
    assert captured["url"].endswith("/chat/completions")
    assert captured["headers"]["Authorization"] == (
        "Bearer sk-test"
    )
    assert captured["json"]["model"] == "gpt-4o-mini"


def test_anthropic_client_posts_messages(monkeypatch):

    captured = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "content": [
                    {"type": "text", "text": "claude-ok"}
                ]
            }

    def fake_post(url, headers=None, json=None, timeout=None):
        captured["url"] = url
        captured["headers"] = headers
        captured["json"] = json
        return FakeResponse()

    monkeypatch.setattr(
        "app.llm.lmstudio_client.requests.post",
        fake_post,
    )

    client = LMStudioClient(
        base_url="https://api.anthropic.com/v1",
        llm_model="claude-sonnet-4-5",
        api_key="ant-key",
        kind="anthropic",
    )
    text = client.chat(
        [
            {"role": "system", "content": "Be brief."},
            {"role": "user", "content": "hi"},
        ]
    )

    assert text == "claude-ok"
    assert captured["url"].endswith("/messages")
    assert captured["headers"]["x-api-key"] == "ant-key"
    assert captured["json"]["system"] == "Be brief."


def test_set_active_requires_chat_model(tmp_path, monkeypatch):

    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        provider_store,
        "SETTINGS_PATH",
        path,
    )
    provider_store.save_settings(
        {
            "active_id": "lmstudio-local",
            "providers": [
                {
                    "id": "ollama-dup",
                    "kind": "ollama",
                    "label": "Ollama",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "",
                    "chat_model": "",
                }
            ],
        }
    )

    try:
        provider_store.set_active("ollama-dup")
        raise AssertionError("expected ValueError")
    except ValueError as exc:
        assert "chat model" in str(exc).lower()


def test_ollama_reachable_pings_tags(monkeypatch):

    captured = {}

    class FakeResponse:
        ok = True

    def fake_get(url, timeout=None, headers=None):
        captured["url"] = url
        return FakeResponse()

    monkeypatch.setattr(
        "app.llm.lmstudio_client.requests.get",
        fake_get,
    )

    client = LMStudioClient(
        base_url="http://localhost:11434/v1",
        llm_model="hermes3:latest",
        kind="ollama",
    )

    assert client.reachable() is True
    assert captured["url"] == "http://localhost:11434/api/tags"


def test_collapse_duplicate_ollama_keeps_builtin(tmp_path, monkeypatch):

    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        provider_store,
        "SETTINGS_PATH",
        path,
    )
    path.write_text(
        json.dumps(
            {
                "active_id": "990acbe7d1",
                "providers": [
                    {
                        "id": "ollama-local",
                        "kind": "ollama",
                        "label": "Ollama",
                        "base_url": "http://localhost:11434/v1",
                        "api_key": "",
                        "chat_model": "hermes3:latest",
                    },
                    {
                        "id": "990acbe7d1",
                        "kind": "ollama",
                        "label": "Ollama",
                        "base_url": "http://localhost:11434/v1",
                        "api_key": "",
                        "chat_model": "",
                    },
                ],
            }
        ),
        encoding="utf-8",
    )

    loaded = provider_store.load_settings()
    ids = [item["id"] for item in loaded["providers"]]

    assert ids == ["ollama-local"]
    assert loaded["active_id"] == "ollama-local"
    assert loaded["providers"][0]["chat_model"] == (
        "hermes3:latest"
    )


def test_upsert_reuses_existing_ollama_host(tmp_path, monkeypatch):

    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        provider_store,
        "SETTINGS_PATH",
        path,
    )
    provider_store.save_settings(
        {
            "active_id": "ollama-local",
            "providers": [
                {
                    "id": "ollama-local",
                    "kind": "ollama",
                    "label": "Ollama",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "",
                    "chat_model": "hermes3:latest",
                }
            ],
        }
    )

    record = provider_store.upsert_provider(
        {
            "kind": "ollama",
            "label": "Ollama",
            "base_url": "http://localhost:11434/v1",
            "chat_model": "",
        }
    )

    assert record["id"] == "ollama-local"
    assert record["chat_model"] == "hermes3:latest"
    saved = json.loads(path.read_text())
    assert len(saved["providers"]) == 1


def test_set_active_saves_embedding_model(tmp_path, monkeypatch):

    path = tmp_path / "settings.json"
    monkeypatch.setattr(
        provider_store,
        "SETTINGS_PATH",
        path,
    )
    provider_store.save_settings(
        {
            "active_id": "ollama-local",
            "providers": [
                {
                    "id": "ollama-local",
                    "kind": "ollama",
                    "label": "Ollama",
                    "base_url": "http://localhost:11434/v1",
                    "api_key": "",
                    "chat_model": "hermes3:latest",
                    "embedding_model": "",
                }
            ],
        }
    )

    record = provider_store.set_active(
        "ollama-local",
        embedding_model="nomic-embed-text:latest",
    )

    assert record["embedding_model"] == "nomic-embed-text:latest"
    saved = json.loads(path.read_text())
    assert saved["providers"][0]["embedding_model"] == (
        "nomic-embed-text:latest"
    )