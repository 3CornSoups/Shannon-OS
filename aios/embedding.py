"""Embedding client for AIOS memory system.

Primary: OpenAI-compatible embedding API (DashScope / Qwen, configured via
DASHSCOPE_API_KEY / DASHSCOPE_EMBED_MODEL). Returns real semantic vectors.
Fallback: local sentence-transformers model (free, fast, works offline).
Hash fallback: deterministic pseudo-vector if nothing else works.
"""

from __future__ import annotations

import json
import logging
import math

import httpx

logger = logging.getLogger(__name__)

# Lazy-loaded singleton model
_MODEL = None
_MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"


def _get_local_model():
    """Lazy-load the sentence-transformers model (singleton)."""
    global _MODEL
    if _MODEL is None:
        try:
            from sentence_transformers import SentenceTransformer
            _MODEL = SentenceTransformer(_MODEL_NAME)
            logger.info("Embedding: loaded local model '%s'", _MODEL_NAME)
        except Exception as exc:
            logger.warning("Embedding: failed to load local model: %s", exc)
            _MODEL = False  # Mark as failed, don't retry
    return _MODEL if _MODEL is not False else None


class EmbeddingClient:
    """Client for text embedding.

    Priority:
      1. OpenAI-compatible API (DashScope / Qwen) when configured — primary
      2. Local sentence-transformers model (no network, free)
      3. Hash-based fallback
    """

    def __init__(
        self,
        api_base: str = "",
        api_key: str = "",
        model: str = "",
        timeout_sec: int = 15,
    ):
        self.api_base = api_base.rstrip("/") if api_base else ""
        self.api_key = api_key
        self.api_model = model or ""
        self.timeout_sec = timeout_sec

    async def embed(self, text: str) -> list[float]:
        """Get embedding vector. Returns list of floats."""
        text = text[:8000]  # Truncate

        # 1. API (DashScope/OpenAI-compatible) when configured — primary
        if self.api_base and self.api_key:
            vec = await self._api_embed(text)
            if vec:
                return vec

        # 2. Try local model
        local_model = _get_local_model()
        if local_model is not None:
            try:
                vec = local_model.encode(text, normalize_embeddings=True)
                return vec.tolist()
            except Exception as exc:
                logger.warning("Local embed failed: %s, trying API", exc)

        # 3. Hash fallback
        return self._fallback_embed(text)

    async def _api_embed(self, text: str) -> list[float] | None:
        """Call OpenAI-compatible embedding API (DashScope compatible-mode)."""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        payload = {"model": self.api_model or "qwen3.7-text-embedding", "input": text}
        try:
            async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
                response = await client.post(
                    f"{self.api_base}/v1/embeddings",
                    headers=headers, json=payload,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data["data"][0]["embedding"]
        except Exception as exc:
            logger.debug("Embedding API failed: %s", exc)
        return None

    def _fallback_embed(self, text: str) -> list[float]:
        """Deterministic hash-based 128-dim vector."""
        import hashlib
        h = hashlib.sha256(text.encode()).digest()
        vec = []
        for i in range(0, 32, 2):
            val = (h[i] << 8 | h[i + 1]) / 65535.0
            vec.append(val * 2 - 1)
        while len(vec) < 128:
            vec.append(0.0)
        return vec

    @staticmethod
    def cosine_similarity(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = math.sqrt(sum(x * x for x in a))
        norm_b = math.sqrt(sum(x * x for x in b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)

    @staticmethod
    def encode_vector(vec: list[float]) -> str:
        return json.dumps(vec)

    @staticmethod
    def decode_vector(s: str) -> list[float]:
        return json.loads(s)
