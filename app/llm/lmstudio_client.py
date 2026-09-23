from typing import Any

import requests

from app.llm.model_catalog import (
    list_chat_models,
    list_embedding_models,
)
from app.llm.provider_store import (
    get_active,
    set_active,
)


class LMStudioClient:

    def __init__(
        self,
        base_url: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
        api_key: str | None = None,
        kind: str | None = None,
    ):

        active = get_active()

        self.kind = (
            kind or active.get("kind") or "lmstudio"
        )
        self.base_url = (
            base_url or active.get("base_url") or ""
        ).rstrip("/")
        self.llm_model = (
            llm_model
            or active.get("chat_model")
            or ""
        )
        self.embedding_model = (
            embedding_model
            or active.get("embedding_model")
            or ""
        )
        self.api_key = (
            api_key
            if api_key is not None
            else active.get("api_key") or ""
        )

    def reachable(self) -> bool:

        try:
            if self.kind in {"openai", "anthropic"}:
                return bool(self.api_key)

            timeout = 3

            if self.kind == "ollama":
                root = self.base_url.rstrip("/")

                if root.endswith("/v1"):
                    root = root[:-3]

                response = requests.get(
                    f"{root}/api/tags",
                    timeout=timeout,
                )
                return response.ok

            response = requests.get(
                f"{self.base_url}/models",
                headers=self._headers(),
                timeout=timeout,
            )
            return response.ok
        except Exception:
            return False

    def list_models(self) -> list[str]:

        return list_chat_models(
            self.kind,
            self.base_url,
            self._headers(),
        )

    def chat(
        self,
        messages: list[dict[str, str]],
        temperature: float = 0.1,
        response_schema: dict | None = None,
        max_tokens: int = 3000,
    ) -> str:

        if not self.llm_model:
            raise RuntimeError(
                "No chat model selected. "
                "Pick a provider and model in LLM settings."
            )

        if self.kind == "anthropic":
            return self._anthropic_chat(
                messages,
                temperature,
                response_schema,
                max_tokens,
            )

        return self._openai_chat(
            messages,
            temperature,
            response_schema,
            max_tokens,
        )

    def embed(self, text: str) -> list[float]:

        model = self._resolved_embedding_model()

        try:
            response = requests.post(
                f"{self.base_url}/embeddings",
                headers=self._headers(),
                json={
                    "model": model,
                    "input": text,
                },
                timeout=300,
            )
            response.raise_for_status()
            data: dict[str, Any] = response.json()
            return data["data"][0]["embedding"]
        except Exception:
            if self.kind != "ollama":
                raise

        root = self.base_url.rstrip("/")

        if root.endswith("/v1"):
            root = root[:-3]

        last_error = None

        for path in ("/api/embeddings", "/api/embed"):
            try:
                response = requests.post(
                    f"{root}{path}",
                    json={
                        "model": model,
                        ("input" if path == "/api/embed" else "prompt"): text,
                    },
                    timeout=300,
                )
                response.raise_for_status()
                payload = response.json()
            except Exception as exc:
                last_error = exc
                continue

            vector = payload.get("embedding")

            if isinstance(vector, list) and vector:
                return vector

            nested = payload.get("embeddings")

            if isinstance(nested, list) and nested:
                first = nested[0]

                if isinstance(first, list):
                    return first

        if last_error:
            raise last_error

        raise RuntimeError(
            "Ollama did not return an embedding vector."
        )

    def _resolved_embedding_model(self) -> str:

        if self.embedding_model:
            return self.embedding_model

        models = list_embedding_models(
            self.kind,
            self.base_url,
            self._headers(),
        )

        if not models:
            raise RuntimeError(
                "No embedding model configured. "
                "Pull an embedding model in Ollama "
                "(for example nomic-embed-text) or "
                "pick one under LLM provider."
            )

        self.embedding_model = models[0]
        provider_id = get_active().get("id") or ""

        if provider_id:
            try:
                set_active(
                    provider_id,
                    embedding_model=self.embedding_model,
                )
            except Exception:
                pass

        return self.embedding_model

    def _headers(self) -> dict[str, str]:

        if self.kind == "anthropic":
            return {
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            }

        headers = {"Content-Type": "application/json"}

        if self.api_key:
            headers["Authorization"] = (
                f"Bearer {self.api_key}"
            )

        return headers

    def _openai_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        response_schema: dict | None,
        max_tokens: int,
    ) -> str:

        payload = {
            "model": self.llm_model,
            "messages": messages,
            "temperature": temperature,
            "top_p": 0.95,
            "max_tokens": max_tokens,
            "tool_choice": "none",
            "tools": [],
        }

        if response_schema is not None:
            payload["response_format"] = {
                "type": "json_schema",
                "json_schema": {
                    "name": response_schema["name"],
                    "strict": True,
                    "schema": response_schema["schema"],
                },
            }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=self._headers(),
            json=payload,
            timeout=300,
        )

        if not response.ok and response_schema is not None:
            payload.pop("response_format", None)
            payload["messages"] = list(messages) + [
                {
                    "role": "user",
                    "content": (
                        "Return JSON only. Schema name: "
                        f"{response_schema['name']}."
                    ),
                }
            ]
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self._headers(),
                json=payload,
                timeout=300,
            )

        response.raise_for_status()

        data = response.json()
        message = data["choices"][0]["message"]
        content = message.get("content")

        if not content:
            raise RuntimeError(
                f"Chat API returned no message content: {data}"
            )

        return content

    def _anthropic_chat(
        self,
        messages: list[dict[str, str]],
        temperature: float,
        response_schema: dict | None,
        max_tokens: int,
    ) -> str:

        system = ""
        chat = []

        for item in messages:
            role = item.get("role") or "user"
            content = item.get("content") or ""

            if role == "system":
                system = (
                    f"{system}\n{content}".strip()
                    if system
                    else content
                )
                continue

            chat.append(
                {
                    "role": (
                        "assistant"
                        if role == "assistant"
                        else "user"
                    ),
                    "content": content,
                }
            )

        if response_schema is not None:
            system = (
                f"{system}\n\nReturn JSON only for schema "
                f"{response_schema['name']}."
            ).strip()

        payload = {
            "model": self.llm_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": chat or [
                {"role": "user", "content": "Hello"}
            ],
        }

        if system:
            payload["system"] = system

        response = requests.post(
            f"{self.base_url}/messages",
            headers=self._headers(),
            json=payload,
            timeout=300,
        )
        response.raise_for_status()
        data = response.json()
        blocks = data.get("content") or []
        texts = [
            block.get("text") or ""
            for block in blocks
            if isinstance(block, dict)
        ]
        content = "\n".join(
            text for text in texts if text
        )

        if not content:
            raise RuntimeError(
                f"Anthropic returned no text: {data}"
            )

        return content
