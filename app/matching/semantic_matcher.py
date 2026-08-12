from typing import List

import numpy as np

from app.llm.lmstudio_client import LMStudioClient


class SemanticMatcher:

    def __init__(
        self,
        client: LMStudioClient | None = None,
    ):
        self.client = client or LMStudioClient()

    def similarity(
        self,
        text_a: str,
        text_b: str,
    ) -> float:

        embedding_a = self.client.embed(text_a)
        embedding_b = self.client.embed(text_b)

        vector_a = np.array(
            embedding_a,
            dtype=np.float32,
        )

        vector_b = np.array(
            embedding_b,
            dtype=np.float32,
        )

        denominator = (
            np.linalg.norm(vector_a)
            * np.linalg.norm(vector_b)
        )

        if denominator == 0:
            return 0.0

        score = np.dot(
            vector_a,
            vector_b,
        ) / denominator

        # Convert cosine similarity
        # from [-1, 1] to [0, 100]
        normalized = (
            (score + 1) / 2
        ) * 100

        return round(
            float(normalized),
            2,
        )

    def compare_many(
        self,
        source: str,
        candidates: List[str],
    ) -> List[dict]:

        results = []

        for candidate in candidates:

            score = self.similarity(
                source,
                candidate,
            )

            results.append(
                {
                    "text": candidate,
                    "score": score,
                }
            )

        return sorted(
            results,
            key=lambda item: item["score"],
            reverse=True,
        )