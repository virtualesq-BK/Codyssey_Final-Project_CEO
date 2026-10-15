"""Pinecone Vector DB 저장소.

bizrag 수집기가 모은 문서 청크를 임베딩 벡터로 변환하여 Pinecone 인덱스에 업서트하고,
시맨틱(의미 기반) 검색을 수행합니다.
"""
from __future__ import annotations

import hashlib
import os
from typing import Any, Iterable

from .embeddings import EmbeddingProvider


class PineconeStore:
    def __init__(
        self,
        api_key: str | None = None,
        index_name: str | None = None,
        namespace: str = "bizrag",
        embedding_provider: EmbeddingProvider | None = None,
        cloud: str = "aws",
        region: str = "us-east-1",
    ):
        self.api_key = api_key or os.environ.get("PINECONE_API_KEY")
        self.index_name = index_name or os.environ.get("PINECONE_INDEX_NAME", "bizrag-market")
        self.namespace = namespace or os.environ.get("PINECONE_NAMESPACE", "bizrag")
        self.cloud = cloud or os.environ.get("PINECONE_CLOUD", "aws")
        self.region = region or os.environ.get("PINECONE_REGION", "us-east-1")
        self.embeddings = embedding_provider or EmbeddingProvider()
        self._pc = None
        self._index = None

    @property
    def client(self):
        if self._pc is None:
            if not self.api_key:
                raise ValueError("PINECONE_API_KEY가 설정되지 않았습니다. .env에 키를 입력하세요.")
            try:
                from pinecone import Pinecone
            except ImportError:
                raise ImportError(
                    "pinecone SDK가 설치되어 있지 않습니다. 'pip install pinecone'을 실행하세요."
                )
            self._pc = Pinecone(api_key=self.api_key)
        return self._pc

    @property
    def index(self):
        if self._index is None:
            self._index = self.client.Index(self.index_name)
        return self._index

    def ensure_index(self, metric: str = "cosine") -> bool:
        """인덱스가 없으면 Serverless 규격으로 자동 생성."""
        client = self.client
        try:
            from pinecone import ServerlessSpec
            spec = ServerlessSpec(cloud=self.cloud, region=self.region)
        except (ImportError, Exception):
            spec = {"serverless": {"cloud": self.cloud, "region": self.region}}

        existing_names = [getattr(idx, "name", str(idx)) for idx in client.list_indexes()]
        if self.index_name not in existing_names:
            client.create_index(
                name=self.index_name,
                dimension=self.embeddings.dimension,
                metric=metric,
                spec=spec,
            )
            return True
        return False

    def upsert_chunks(self, chunks: list[dict], batch_size: int = 100) -> int:
        """청크 목록을 Pinecone에 일괄 업서트.

        청크 딕셔너리 기대 구조:
        {
            "chunk_id": str,
            "doc_id": str,
            "text": str,
            "title": str,
            "source": str,
            "doc_type": str,
            "url": str | None,
            "published_at": str | None,
            "retrieved_at": str | None,
            "license": str | None,
        }
        """
        if not chunks:
            return 0

        total_upserted = 0
        texts_to_embed = [f"{c.get('title', '')}\n{c.get('text', '')}".strip() for c in chunks]
        embeddings = self.embeddings.embed_texts(texts_to_embed)

        records_to_upsert = []
        for c, emb in zip(chunks, embeddings):
            # Pinecone Vector ID는 ASCII 문자만 허용되므로 sha1 해시 기반 고유 ASCII ID 사용
            ascii_id = hashlib.sha1(c["chunk_id"].encode("utf-8")).hexdigest()
            metadata = {
                "chunk_id": c["chunk_id"],
                "doc_id": c["doc_id"],
                "source": c.get("source", ""),
                "doc_type": c.get("doc_type", ""),
                "title": c.get("title", ""),
                "url": c.get("url") or "",
                "published_at": c.get("published_at") or "",
                "retrieved_at": c.get("retrieved_at") or "",
                "license": c.get("license") or "",
                "text": c.get("text", "")[:3500],  # Pinecone metadata 크기 제한 대응
            }
            records_to_upsert.append({
                "id": ascii_id,
                "values": emb,
                "metadata": metadata,
            })

        total = len(records_to_upsert)
        for i in range(0, total, batch_size):
            batch = records_to_upsert[i : i + batch_size]
            self.index.upsert(vectors=batch, namespace=self.namespace)
            total_upserted += len(batch)
            print(f"    진행 중: {total_upserted}/{total} 청크 업서트 완료 ({int(total_upserted / total * 100)}%)")

        return total_upserted

    def search(
        self,
        query: str,
        sources: Iterable[str] | None = None,
        doc_types: Iterable[str] | None = None,
        limit: int = 8,
    ) -> list[dict]:
        """쿼리 텍스트를 임베딩하여 Pinecone 시맨틱 검색."""
        query_vec = self.embeddings.embed_query(query)

        # 메타데이터 필터 구성
        filter_dict: dict[str, Any] = {}
        if sources:
            src_list = list(sources)
            filter_dict["source"] = {"$in": src_list} if len(src_list) > 1 else src_list[0]
        if doc_types:
            dt_list = list(doc_types)
            filter_dict["doc_type"] = {"$in": dt_list} if len(dt_list) > 1 else dt_list[0]

        resp = self.index.query(
            vector=query_vec,
            namespace=self.namespace,
            top_k=limit,
            include_metadata=True,
            filter=filter_dict if filter_dict else None,
        )

        hits: list[dict] = []
        for match in resp.get("matches", []):
            meta = match.get("metadata", {})
            hits.append({
                "chunk_id": meta.get("chunk_id") or match.get("id"),
                "doc_id": meta.get("doc_id"),
                "source": meta.get("source"),
                "doc_type": meta.get("doc_type"),
                "title": meta.get("title"),
                "text": meta.get("text"),
                "url": meta.get("url"),
                "published_at": meta.get("published_at"),
                "retrieved_at": meta.get("retrieved_at"),
                "license": meta.get("license"),
                "score": round(match.get("score", 0.0), 3),
            })
        return hits

    def stats(self) -> dict:
        """인덱스 통계 정보 조회."""
        res = self.index.describe_index_stats()
        return {
            "total_vector_count": res.get("total_vector_count", 0),
            "namespaces": res.get("namespaces", {}),
            "dimension": res.get("dimension"),
        }
