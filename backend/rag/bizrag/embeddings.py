"""텍스트 임베딩 프로바이더.

OpenAI(text-embedding-3-small, 1536차원) 또는 Gemini(text-embedding-004, 768차원)를 지원하며,
테스트나 키 미설정 시 동작하는 Mock 임베딩도 제공합니다.
"""
from __future__ import annotations

import hashlib
import math
import os
import time
from typing import Any


class EmbeddingProvider:
    def __init__(
        self,
        provider: str = "openai",
        model: str | None = None,
        api_key: str | None = None,
        dimension: int | None = None,
        base_url: str | None = None,
    ):
        self.provider = (provider or os.environ.get("EMBEDDING_PROVIDER", "openai")).lower()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY") or os.environ.get("GEMINI_API_KEY")
        self.base_url = base_url or os.environ.get("OPENAI_BASE_URL")
        self._fastembed_model = None

        if self.provider in ("fastembed", "local"):
            self.model = model or os.environ.get("EMBEDDING_MODEL", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            self.dimension = dimension or 384
        elif self.provider == "openai":
            self.model = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small")
            self.dimension = dimension or (1536 if "small" in self.model or "large" not in self.model else 3072)
        elif self.provider in ("gemini", "google"):
            self.model = model or os.environ.get("EMBEDDING_MODEL", "text-embedding-004")
            self.dimension = dimension or 768
        elif self.provider == "mock":
            self.model = "mock-embedding"
            self.dimension = dimension or 128
        else:
            self.model = model or "text-embedding-3-small"
            self.dimension = dimension or 1536

    def embed_texts(self, texts: list[str], batch_size: int = 64) -> list[list[float]]:
        """여러 텍스트를 배치로 임베딩 벡터 목록으로 변환."""
        if not texts:
            return []

        if self.provider in ("fastembed", "local"):
            return self._embed_fastembed(texts, batch_size)

        if self.provider == "mock" or not self.api_key:
            return [self._mock_embed(t, self.dimension) for t in texts]

        if self.provider == "openai":
            return self._embed_openai(texts, batch_size)
        elif self.provider in ("gemini", "google"):
            return self._embed_gemini(texts)
        else:
            return [self._mock_embed(t, self.dimension) for t in texts]

    def _embed_fastembed(self, texts: list[str], batch_size: int) -> list[list[float]]:
        if self._fastembed_model is None:
            from fastembed import TextEmbedding
            self._fastembed_model = TextEmbedding(model_name=self.model)
        embeddings = list(self._fastembed_model.embed(texts, batch_size=batch_size))
        return [e.tolist() if hasattr(e, "tolist") else list(e) for e in embeddings]

    def embed_query(self, text: str) -> list[float]:
        """단일 쿼리 텍스트 임베딩."""
        vecs = self.embed_texts([text])
        return vecs[0] if vecs else [0.0] * self.dimension

    def _embed_openai(self, texts: list[str], batch_size: int) -> list[list[float]]:
        try:
            from openai import OpenAI
        except ImportError:
            raise ImportError(
                "OpenAI SDK가 설치되어 있지 않습니다. 'pip install openai'를 실행하거나, "
                "EMBEDDING_PROVIDER=fastembed로 설정하세요."
            )

        client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        all_embeddings: list[list[float]] = []

        for i in range(0, len(texts), batch_size):
            batch = [t.replace("\n", " ").strip() or " " for t in texts[i : i + batch_size]]
            resp = client.embeddings.create(input=batch, model=self.model)
            sorted_data = sorted(resp.data, key=lambda x: x.index)
            all_embeddings.extend([d.embedding for d in sorted_data])

        return all_embeddings

    def _embed_gemini(self, texts: list[str]) -> list[list[float]]:
        try:
            from google import genai
            client = genai.Client(api_key=self.api_key)
            embeddings = []
            for t in texts:
                resp = client.models.embed_content(
                    model=self.model,
                    contents=t.strip() or " ",
                )
                embeddings.append(resp.embedding.values)
            return embeddings
        except ImportError:
            # google-genai 미설치 시 google.generativeai 구버전 fallback 시도
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.api_key)
                embeddings = []
                for t in texts:
                    res = genai.embed_content(
                        model=f"models/{self.model}",
                        content=t.strip() or " ",
                    )
                    embeddings.append(res["embedding"])
                return embeddings
            except ImportError:
                raise ImportError(
                    "Google GenAI SDK가 설치되어 있지 않습니다. 'pip install google-genai'를 실행하세요."
                )

    @staticmethod
    def _mock_embed(text: str, dim: int = 128) -> list[float]:
        """결정론적 가상 임베딩 (단어 빈도와 해시 기반 단위 벡터)."""
        vec = [0.0] * dim
        tokens = text.lower().split()
        if not tokens:
            return vec
        for i, token in enumerate(tokens):
            h = int(hashlib.md5(token.encode("utf-8")).hexdigest(), 16)
            idx = h % dim
            vec[idx] += 1.0 + (i * 0.01)

        # L2 normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
