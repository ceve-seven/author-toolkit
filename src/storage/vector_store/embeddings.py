from __future__ import annotations

import math
from typing import List, Optional

from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from src.config.settings import Config


_embedding_func = DefaultEmbeddingFunction()


def compute_embedding(text: str) -> List[float]:
    embedding = _embedding_func([text])
    if embedding is None:
        return []
    # pyrefly: ignore [bad-return]
    return embedding[0]


def compute_foreshadow_similarity(text_a: str, text_b: str) -> float:
    vec_a = compute_embedding(text_a)
    vec_b = compute_embedding(text_b)
    if not vec_a or not vec_b:
        return 0.0
    return _cosine_similarity(vec_a, vec_b)


def is_duplicate_foreshadow(text_a: str, text_b: str, threshold: Optional[float] = None) -> bool:
    if threshold is None:
        threshold = Config.FORESHADOW_DUPLICATE_THRESHOLD
    similarity = compute_foreshadow_similarity(text_a, text_b)
    return similarity >= threshold


def _cosine_similarity(vec_a: List[float], vec_b: List[float]) -> float:
    dot_product = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot_product / (norm_a * norm_b)