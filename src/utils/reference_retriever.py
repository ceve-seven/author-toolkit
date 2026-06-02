from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

from src.storage.vector_store.chroma_client import get_or_create_collection

COLLECTION_NAME = "reference_novels"


def query_reference_fragments(
    query_text: str,
    scene_type: Optional[str] = None,
    n_results: int = 3,
) -> List[Dict[str, Any]]:
    collection = get_or_create_collection(COLLECTION_NAME)
    if collection.count() == 0:
        return []

    where_filter = None
    if scene_type:
        where_filter = {"scene_type": scene_type}

    results = collection.query(
        query_texts=[query_text],
        n_results=n_results,
        where=where_filter,
    )

    fragments = []
    if results and results.get("metadatas"):
        for i in range(len(results["ids"][0])):
            fragment = {
                "id": results["ids"][0][i],
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i] if results.get("distances") else None,
            }
            if results.get("documents"):
                fragment["content"] = results["documents"][0][i][:500]
            fragments.append(fragment)

    return fragments


def get_reference_for_scene(
    scene_description: str,
    scene_pov: str,
    scene_type: str = "描述",
) -> str:
    fragments = query_reference_fragments(
        query_text=scene_description,
        scene_type=scene_type,
        n_results=2,
    )

    if not fragments:
        return ""

    lines = ["参考片段（风格引导）:"]
    for i, frag in enumerate(fragments, 1):
        meta = frag.get("metadata", {})
        source = meta.get("source_file", "未知来源")
        chapter = meta.get("chapter", "")
        content = frag.get("content", "")[:300]
        lines.append(f"\n[{i}] {source} / {chapter}")
        lines.append(f"    场景类型: {meta.get('scene_type', '')}")
        lines.append(f"    情感标签: {meta.get('emotion_tags', '')}")
        lines.append(f"    参考文本: {content}")

    return "\n".join(lines)


def _extract_keywords(text: str) -> str:
    stop_words = {"的", "了", "是", "在", "有", "和", "就", "不", "都", "而",
                  "及", "与", "着", "或", "一个", "没有", "我们", "他们", "你们",
                  "这", "那", "哪", "什么", "怎么"}
    words = re.findall(r"[\u4e00-\u9fff]{2,4}", text)
    filtered = [w for w in words if w not in stop_words]
    return " ".join(filtered[:5])