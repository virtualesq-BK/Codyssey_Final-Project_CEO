"""Pinecone Vector RAG 및 임베딩 연동 단위 테스트 (네트워크/API 키 불필요).

실행: python -m unittest discover -s tests -v
"""
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from bizrag.app import App
from bizrag.embeddings import EmbeddingProvider
from bizrag.knowledge import Knowledge
from bizrag.pinecone_store import PineconeStore
from bizrag.store import Store


class TestEmbeddings(unittest.TestCase):
    def test_mock_embedding(self):
        emb = EmbeddingProvider(provider="mock", dimension=64)
        self.assertEqual(emb.dimension, 64)

        vecs = emb.embed_texts(["안녕하세요", "반갑습니다"])
        self.assertEqual(len(vecs), 2)
        self.assertEqual(len(vecs[0]), 64)
        self.assertEqual(len(vecs[1]), 64)

        # 결정론적 확인: 같은 텍스트는 같은 벡터
        vecs2 = emb.embed_texts(["안녕하세요"])
        self.assertEqual(vecs[0], vecs2[0])

        # 쿼리 임베딩
        q_vec = emb.embed_query("테스트 질의")
        self.assertEqual(len(q_vec), 64)


class TestPineconeStore(unittest.TestCase):
    def setUp(self):
        self.emb = EmbeddingProvider(provider="mock", dimension=32)
        self.store = PineconeStore(
            api_key="fake-key",
            index_name="test-index",
            namespace="test-ns",
            embedding_provider=self.emb,
        )

    def test_ensure_index(self):
        mock_client = MagicMock()
        mock_idx_item = MagicMock()
        mock_idx_item.name = "other-index"
        mock_client.list_indexes.return_value = [mock_idx_item]

        with patch.object(self.store, "_pc", mock_client):
            created = self.store.ensure_index()
            self.assertTrue(created)
            mock_client.create_index.assert_called_once()

    def test_upsert_chunks(self):
        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_client.Index.return_value = mock_index

        chunks = [
            {
                "chunk_id": "law:article:1#0",
                "doc_id": "law:article:1",
                "title": "소비자기본법 제1조",
                "text": "이 법은 소비자의 권익을 증진하기 위하여 제정되었다.",
                "source": "law",
                "doc_type": "law_article",
                "url": "http://example.com/law",
                "published_at": "2024-01-01",
                "retrieved_at": "2024-01-02",
                "license": "공공누리",
            }
        ]

        with patch.object(self.store, "_pc", mock_client), patch.object(self.store, "_index", mock_index):
            count = self.store.upsert_chunks(chunks, batch_size=10)
            self.assertEqual(count, 1)
            mock_index.upsert.assert_called_once()
            args, kwargs = mock_index.upsert.call_args
            vectors = kwargs["vectors"]
            self.assertEqual(len(vectors), 1)
            self.assertEqual(vectors[0]["metadata"]["chunk_id"], "law:article:1#0")
            self.assertEqual(vectors[0]["metadata"]["source"], "law")
            self.assertEqual(len(vectors[0]["values"]), 32)

    def test_search(self):
        mock_client = MagicMock()
        mock_index = MagicMock()
        mock_index.query.return_value = {
            "matches": [
                {
                    "id": "law:article:1#0",
                    "score": 0.895,
                    "metadata": {
                        "doc_id": "law:article:1",
                        "title": "소비자기본법 제1조",
                        "text": "이 법은...",
                        "source": "law",
                        "doc_type": "law_article",
                        "url": "http://example.com/law",
                        "published_at": "2024-01-01",
                        "retrieved_at": "2024-01-02",
                        "license": "공공누리",
                    },
                }
            ]
        }

        with patch.object(self.store, "_pc", mock_client), patch.object(self.store, "_index", mock_index):
            hits = self.store.search("소비자 권익", limit=5)
            self.assertEqual(len(hits), 1)
            self.assertEqual(hits[0]["chunk_id"], "law:article:1#0")
            self.assertEqual(hits[0]["score"], 0.895)
            self.assertEqual(hits[0]["source"], "law")


class TestHybridSearch(unittest.TestCase):
    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.db_path = Path(self.td.name) / "test.db"
        self.sql_store = Store(self.db_path)

        # 샘플 문서 적재
        self.sql_store.upsert_document(
            source="law",
            doc_type="law_article",
            original_id="1",
            title="소비자기본법 제1조",
            body="이 법은 소비자의 권익을 증진하고 소비생활의 향상을 도모함을 목적으로 한다.",
            url="http://law.go.kr",
        )
        self.sql_store.upsert_document(
            source="law",
            doc_type="law_article",
            original_id="17",
            title="전자상거래법 제17조",
            body="소비자는 계약 내용에 관한 서면을 받은 날부터 7일 이내에 청약철회를 할 수 있다.",
            url="http://law.go.kr",
        )

        self.mock_pinecone = MagicMock()
        self.emb = EmbeddingProvider(provider="mock", dimension=32)
        self.knowledge = Knowledge(app=None, pinecone_store=self.mock_pinecone)
        self.knowledge.store = self.sql_store

    def tearDown(self):
        self.sql_store.close()
        self.td.cleanup()

    def test_get_all_chunks(self):
        chunks = self.sql_store.get_all_chunks()
        self.assertGreaterEqual(len(chunks), 2)
        self.assertEqual(chunks[0]["source"], "law")
        self.assertIn("chunk_id", chunks[0])

    def test_hybrid_search_rrf(self):
        # Pinecone 모의 검색 결과
        self.mock_pinecone.search.return_value = [
            {
                "chunk_id": "law:law_article:17#0",
                "doc_id": "law:law_article:17",
                "source": "law",
                "doc_type": "law_article",
                "title": "전자상거래법 제17조",
                "text": "청약철회 7일",
                "score": 0.95,
            }
        ]

        # hybrid 모드로 검색
        results = self.knowledge.search_knowledge("청약철회", mode="hybrid", limit=5)
        self.assertGreaterEqual(len(results), 1)
        top = results[0]
        self.assertEqual(top["doc_id"], "law:law_article:17")
        self.assertIn("hybrid_score", top)
