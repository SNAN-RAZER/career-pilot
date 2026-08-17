from app.llm.model_catalog import list_chat_models


class FakeResponse:
    def __init__(self, payload, ok=True):
        self._payload = payload
        self.ok = ok

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError("http error")

    def json(self):
        return self._payload


def test_ollama_uses_tags_endpoint(monkeypatch):

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/api/tags"):
            return FakeResponse(
                {
                    "models": [
                        {"name": "llama3.2:latest"},
                        {"name": "nomic-embed-text"},
                    ]
                }
            )
        return FakeResponse({}, ok=False)

    monkeypatch.setattr(
        "app.llm.model_catalog.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "app.llm.model_catalog._ollama_cli",
        lambda: [],
    )

    models = list_chat_models(
        "ollama",
        "http://localhost:11434/v1",
    )

    assert models == ["llama3.2:latest"]


def test_lmstudio_uses_v0_and_v1(monkeypatch):

    def fake_get(url, headers=None, timeout=None):
        if "/api/v0/models" in url:
            return FakeResponse(
                {
                    "data": [
                        {
                            "id": "meta-llama-3.1-8b-instruct",
                            "type": "llm",
                        },
                        {
                            "id": "text-embedding-nomic-embed-text-v1.5",
                            "type": "embeddings",
                        },
                    ]
                }
            )
        if url.endswith("/models"):
            return FakeResponse(
                {
                    "data": [
                        {"id": "another-chat-model"}
                    ]
                }
            )
        return FakeResponse({}, ok=False)

    monkeypatch.setattr(
        "app.llm.model_catalog.requests.get",
        fake_get,
    )

    models = list_chat_models(
        "lmstudio",
        "http://localhost:1234/v1",
    )

    assert "meta-llama-3.1-8b-instruct" in models
    assert "another-chat-model" in models
    assert not any("embed" in name for name in models)


def test_ollama_lists_embedding_models(monkeypatch):

    def fake_get(url, headers=None, timeout=None):
        if url.endswith("/api/tags"):
            return FakeResponse(
                {
                    "models": [
                        {"name": "llama3.2:latest"},
                        {"name": "nomic-embed-text:latest"},
                    ]
                }
            )
        return FakeResponse({}, ok=False)

    monkeypatch.setattr(
        "app.llm.model_catalog.requests.get",
        fake_get,
    )
    monkeypatch.setattr(
        "app.llm.model_catalog._ollama_cli",
        lambda: [],
    )

    from app.llm.model_catalog import list_embedding_models

    embeds = list_embedding_models(
        "ollama",
        "http://localhost:11434/v1",
    )

    assert embeds == ["nomic-embed-text:latest"]


def test_ollama_cli_parses_list_table(monkeypatch):

    monkeypatch.setattr(
        "app.llm.model_catalog._ollama_tags",
        lambda base_url: [],
    )
    monkeypatch.setattr(
        "app.llm.model_catalog._openai_style_models",
        lambda base_url, headers: [],
    )

    class Completed:
        returncode = 0
        stdout = (
            "NAME                ID    SIZE\n"
            "llama3.2:latest     abc   2.0 GB\n"
            "qwen2.5:7b          def   4.7 GB\n"
        )

    monkeypatch.setattr(
        "app.llm.model_catalog.subprocess.run",
        lambda *args, **kwargs: Completed(),
    )

    models = list_chat_models(
        "ollama",
        "http://localhost:11434/v1",
    )

    assert models == ["llama3.2:latest", "qwen2.5:7b"]
