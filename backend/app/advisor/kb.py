"""Curated agronomy knowledge base + TF-IDF retrieval.

No external embedding service required: a small hand-rolled TF-IDF +
cosine-similarity ranker over ~30 short statements is more than enough
precision for this corpus size, and keeps the advisor fully offline-capable
for KB retrieval (only the `write`/`verify` LLM call needs network).
"""

from __future__ import annotations

import json
import math
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path

KB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "agronomy_kb.json"

_WORD_RE = re.compile(r"[a-z0-9]+")

# Minimal English stopword list -- small corpus, so even a short list
# meaningfully sharpens TF-IDF discrimination between statements.
_STOPWORDS = {
    "the", "a", "an", "is", "are", "and", "or", "of", "to", "in", "on", "at",
    "for", "with", "its", "this", "that", "than", "as", "be", "can", "which",
    "into", "such", "between", "when", "than", "than", "it", "their", "by",
    "from", "both", "not", "so", "if", "even", "while", "most", "more", "than",
}


def _tokenize(text: str) -> list[str]:
    return [w for w in _WORD_RE.findall(text.lower()) if w not in _STOPWORDS]


@lru_cache
def load_kb() -> list[dict]:
    with open(KB_PATH, encoding="utf-8") as f:
        return json.load(f)


@lru_cache
def _tfidf_index() -> tuple[list[dict], list[Counter], dict[str, float]]:
    kb = load_kb()
    doc_tokens = [_tokenize(entry["statement"]) for entry in kb]
    doc_term_freqs = [Counter(tokens) for tokens in doc_tokens]

    n_docs = len(kb)
    df: Counter = Counter()
    for tf in doc_term_freqs:
        for term in tf:
            df[term] += 1

    idf = {term: math.log((1 + n_docs) / (1 + count)) + 1.0 for term, count in df.items()}
    return kb, doc_term_freqs, idf


def _vectorize(term_freq: Counter, idf: dict[str, float]) -> dict[str, float]:
    vec = {term: freq * idf.get(term, 0.0) for term, freq in term_freq.items()}
    norm = math.sqrt(sum(v * v for v in vec.values())) or 1.0
    return {term: v / norm for term, v in vec.items()}


def _cosine(a: dict[str, float], b: dict[str, float]) -> float:
    return sum(v * b.get(term, 0.0) for term, v in a.items())


def retrieve(query: str, top_k: int = 6) -> list[dict]:
    """Returns the top_k KB entries (dicts with id/source/statement) ranked
    by TF-IDF cosine similarity to `query`. Falls back to the first top_k KB
    entries if the query has no overlapping vocabulary with the corpus at
    all (keeps retrieval non-empty rather than erroring)."""
    kb, doc_term_freqs, idf = _tfidf_index()

    query_tf = Counter(_tokenize(query))
    if not query_tf:
        return kb[:top_k]

    query_vec = _vectorize(query_tf, idf)
    doc_vecs = [_vectorize(tf, idf) for tf in doc_term_freqs]

    scored = [(i, _cosine(query_vec, dv)) for i, dv in enumerate(doc_vecs)]
    scored.sort(key=lambda t: t[1], reverse=True)

    if scored[0][1] <= 0:
        return kb[:top_k]

    return [kb[i] for i, score in scored[:top_k] if score > 0] or kb[:top_k]


def build_retrieval_query(facts: dict, question: str | None = None) -> str:
    """Builds the text query used for KB retrieval out of a facts object:
    the crop names in the rotation (and current crops), plus whichever
    agronomic themes the facts/sub-scores suggest are most relevant, plus an
    optional free-text chat question."""
    parts: list[str] = []

    crop_names = list(facts.get("rotation_crops", {}).values()) + facts.get("current_crops", [])
    parts.extend(crop_names)

    sub_scores = facts.get("rotation_score", {}).get("sub_scores", {})
    if sub_scores.get("water_fit", 100) < 70:
        parts.append("water saving irrigation deficit drought tolerant")
    if sub_scores.get("heat_risk", 100) < 70:
        parts.append("heat stress flowering critical temperature")
    if sub_scores.get("soil_health", 100) >= 70:
        parts.append("legume nitrogen fixation crop residue soil organic matter diversity rotation pest")
    else:
        parts.append("crop residue soil organic matter diversity pest break legume nitrogen")

    legumes = [c for c, meta in facts.get("per_crop", {}).items() if meta.get("n_fixing")]
    if legumes:
        parts.append("legume nitrogen fixation")

    if question:
        parts.append(question)

    return " ".join(parts)
