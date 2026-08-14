import os
from typing import Any

import requests
from dotenv import load_dotenv


load_dotenv()


class LMStudioClient:

    def __init__(
        self,
        base_url: str | None = None,
        llm_model: str | None = None,
        embedding_model: str | None = None,
    ):

        self.base_url = (
            base_url
            or os.getenv(
                "LM_STUDIO_BASE_URL",
                "http://localhost:1234/v1",
            )
        ).rstrip("/")

        self.llm_model = (
            llm_model
            or os.getenv(
                "LLM_MODEL",
                "meta-llama-3.1-8b-instruct",
            )
        )

        self.embedding_model = (
            embedding_model
            or os.getenv(
                "EMBEDDING_MODEL",
                "text-embedding-bge-large-en-v1.5",
            )
        )

    def chat(
    self,
    messages: list[dict[str, str]],
    temperature: float = 0.1,
    response_schema: dict | None = None,
    max_tokens: int = 3000,
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
            json=payload,
            timeout=300,
        )

        response.raise_for_status()

        data = response.json()

        message = data["choices"][0]["message"]

        content = message.get("content")

        if not content:
            raise RuntimeError(
                f"LM Studio returned no message content: {data}"
            )

        return content
    def embed(self, text: str) -> list[float]:

        response = requests.post(
            f"{self.base_url}/embeddings",
            json={
                "model": self.embedding_model,
                "input": text,
            },
            timeout=300,
        )

        response.raise_for_status()

        data: dict[str, Any] = response.json()

        return data["data"][0]["embedding"]