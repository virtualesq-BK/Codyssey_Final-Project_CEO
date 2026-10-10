"""한국어 전문검색용 토크나이저.

SQLite FTS5의 기본 토크나이저는 한국어 조사·복합어를 다루지 못하고,
trigram 토크나이저는 2글자 단어("시약", "관리")를 검색하지 못한다.
그래서 색인·검색 양쪽에서 단어를 글자 2-gram으로 바꿔 넣는다.
  "연구실시약관리" -> "연구 구실 실시 시약 약관 관리"
검색어도 같은 방식으로 바꿔 '구(phrase)'로 묻기 때문에 조사가 붙거나
띄어쓰기가 달라도 찾아진다.
"""
from __future__ import annotations

import re

_WORD = re.compile(r"[0-9A-Za-z가-힣ㄱ-ㅎㅏ-ㅣ]+")


def _bigrams(word: str) -> list[str]:
    if len(word) <= 2:
        return [word]
    return [word[i : i + 2] for i in range(len(word) - 1)]


def to_index_text(text: str) -> str:
    out: list[str] = []
    for w in _WORD.findall((text or "").lower()):
        out.extend(_bigrams(w))
    return " ".join(out)


def to_match_query(query: str) -> str | None:
    """검색어 -> FTS5 MATCH 식. 단어별 bigram 구를 OR로 묶고 bm25로 순위를 매긴다."""
    phrases = []
    for w in _WORD.findall((query or "").lower()):
        grams = _bigrams(w)
        phrases.append('"' + " ".join(grams) + '"')
    if not phrases:
        return None
    return " OR ".join(dict.fromkeys(phrases))


def chunk_text(text: str, size: int = 700, overlap: int = 120) -> list[str]:
    """문단 경계를 우선해 청크로 나눈다."""
    text = (text or "").strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]
    paras = [p.strip() for p in re.split(r"\n\s*\n|\n", text) if p.strip()]
    chunks: list[str] = []
    buf = ""
    for p in paras:
        if len(buf) + len(p) + 1 <= size:
            buf = f"{buf}\n{p}" if buf else p
            continue
        if buf:
            chunks.append(buf)
        while len(p) > size:
            chunks.append(p[:size])
            p = p[size - overlap :]
        buf = p
    if buf:
        chunks.append(buf)
    return chunks
