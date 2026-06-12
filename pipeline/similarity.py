"""Similarity guard (STRATEGY.md §2, "Half 2 — enforce at a gate").

"Embed every finished script; store the vectors. Before a new video proceeds,
compute cosine similarity vs. the back catalog. Above a threshold -> reject and
regenerate. Mechanically prevents the 30-near-identical-videos pattern."

Embeddings use Gemini when a key is present; otherwise we fall back to a
lexical (token Jaccard) signal so the guard still functions offline. Vectors for
accepted scripts are appended to catalog/embeddings.json.
"""
from __future__ import annotations

import json
import math
import os
import re

from . import ROOT, llm

CATALOG_PATH = ROOT / "catalog" / "embeddings.json"
THRESHOLD = float(os.getenv("SIMILARITY_THRESHOLD", "0.86"))


def _load() -> list[dict]:
    if not CATALOG_PATH.exists():
        return []
    try:
        with open(CATALOG_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def _save(entries: list[dict]) -> None:
    CATALOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    tmp = CATALOG_PATH.with_suffix(".json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)
    tmp.replace(CATALOG_PATH)


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


def _tokens(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9']+", (text or "").lower()))


def _jaccard(a: str, b: str) -> float:
    ta, tb = _tokens(a), _tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def fingerprint(text: str) -> dict:
    """Return a stored representation: an embedding vector if available, else the
    raw text for lexical comparison."""
    vec = llm.embed(text)
    if vec is not None:
        return {"kind": "embedding", "vector": vec, "text": text[:240]}
    return {"kind": "lexical", "text": text}


def max_similarity(text: str) -> tuple[float, str | None]:
    """Highest similarity of `text` against the accepted catalog.

    Returns (score, most_similar_job_id). Uses embeddings when both sides have
    them, otherwise falls back to lexical Jaccard.
    """
    catalog = _load()
    if not catalog:
        return 0.0, None
    fp = fingerprint(text)
    best, best_id = 0.0, None
    for entry in catalog:
        if fp["kind"] == "embedding" and entry.get("kind") == "embedding":
            score = _cosine(fp["vector"], entry["vector"])
        else:
            score = _jaccard(text, entry.get("text", ""))
        if score > best:
            best, best_id = score, entry.get("job_id")
    return best, best_id


def remember(job_id: str, text: str) -> None:
    """Add an accepted script's fingerprint to the back catalog."""
    catalog = _load()
    catalog = [e for e in catalog if e.get("job_id") != job_id]  # idempotent
    entry = fingerprint(text)
    entry["job_id"] = job_id
    catalog.append(entry)
    _save(catalog)
