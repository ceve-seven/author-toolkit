"""
参考小说向量化脚本 — 将 参考小说/ 目录下的 .md 文件按段落/场景分割，
标注场景类型、节奏曲线、情感起伏、推理模式、对话模式等维度，并存入 ChromaDB。

用法：
    python -m scripts.chroma_vectorize_reference              # 正常执行（跳过已存在）
    python -m scripts.chroma_vectorize_reference --rebuild    # 重建 collection
    python -m scripts.chroma_vectorize_reference --list       # 列出已向量化文件
"""

import argparse
import glob
import hashlib
import os
import re
import sys
from typing import Dict, List, Optional, Tuple

from src.storage.vector_store.chroma_client import get_or_create_collection
from config import Config


# ── 路径常量 ──────────────────────────────────────────────────────────────

REFERENCE_NOVEL_DIR = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "参考小说")
)
"""参考小说所在目录（相对于脚本位置的两级上层）"""

COLLECTION_NAME = "reference_novels"


# ── 场景类型关键词表 ──────────────────────────────────────────────────────

SCENE_KEYWORDS: Dict[str, List[str]] = {
    "对话": [
        "说道", "问道", "回答", "开口", "打断", "喊", "叫", "说", "问", "答",
        "聊", "谈", "告诉", "解释", "提议", "建议", "吼", "骂", "质问", "喃喃",
        "自言自语", "插话", "接过话", "道", "曰", "轻声道", "低声道", "喊道",
        "叫道", "喊道", "骂道", "问道", "说道",
    ],
    "推理": [
        "线索", "推理", "思考", "分析", "推测", "推论", "判断", "依据",
        "证据", "排除", "推导", "结论", "逻辑", "假设", "验证", "猜测",
        "想到", "看来", "显然", "说明", "意味着", "暗示", "推断",
    ],
    "战斗": [
        "攻击", "战斗", "刀", "剑", "枪", "拳", "踢", "杀", "刺", "斩",
        "劈", "砍", "躲", "闪", "防御", "进攻", "搏斗", "厮杀", "冲锋",
        "射击", "爆炸", "威力", "力量", "速度", "命中", "击中", "伤口",
        "鲜血", "飞溅", "倒飞", "轰",
    ],
    "情感": [
        "难过", "开心", "感动", "悲伤", "愤怒", "喜悦", "恐惧", "绝望",
        "希望", "温暖", "心痛", "泪", "笑", "哭", "激动", "温柔",
        "爱", "恨", "怨", "悔", "幸福", "凄凉", "拥抱",
    ],
    "悬疑": [
        "奇怪", "诡异", "谜", "神秘", "疑惑", "异常", "不对劲",
        "不可思议", "难以理解", "古怪", "蹊跷", "暗", "阴影", "秘密",
        "未知", "恐怖", "惊悚", "颤抖", "冷汗", "毛骨悚然",
    ],
}

EMOTION_KEYWORDS: Dict[str, List[str]] = {
    "恐惧": ["恐惧", "害怕", "恐怖", "惊悚", "颤抖", "冷汗", "胆寒", "毛骨悚然", "心惊", "吓"],
    "愤怒": ["愤怒", "怒火", "生气", "暴怒", "恨", "咬牙切齿", "怒不可遏", "愤"],
    "悲伤": ["悲伤", "难过", "伤心", "痛苦", "绝望", "泪", "哭", "哀", "悲", "凄凉", "心碎"],
    "喜悦": ["喜悦", "开心", "高兴", "快乐", "欢喜", "欣慰", "温暖", "幸福", "笑", "满足"],
    "惊奇": ["惊讶", "震惊", "震撼", "吃惊", "目瞪口呆", "难以置信", "意外", "骇然"],
    "悬疑": ["疑惑", "怀疑", "困惑", "迷茫", "不解", "谜", "诡异", "奇怪", "好奇"],
    "紧张": ["紧张", "焦虑", "不安", "忐忑", "窒息", "压迫", "紧绷", "急迫", "煎熬"],
    "希望": ["希望", "期待", "期盼", "信念", "坚定", "勇气", "光明", "信任"],
}

REASONING_PHASE_KEYWORDS: Dict[str, List[str]] = {
    "线索": ["线索", "痕迹", "迹象", "证据", "发现", "找到", "看见", "观察"],
    "推导": ["推测", "推断", "推导", "意味", "说明", "表明", "应该", "可能", "必然"],
    "排除": ["排除", "不可能", "不对", "错了", "否定", "推翻", "矛盾"],
    "结论": ["结论", "答案", "真相", "原来", "终于明白", "清楚了", "断定"],
}

DIALOGUE_INDICATORS: List[str] = [
    '"', "「", "」", "『", "』", "「", "」", "『", "』",
    "说道", "问道", "回答", "说", "问", "答", "道", "喊", "叫",
]

CHUNK_MIN_CHINESE_CHARS = 20
"""段落最小中文字符数，低于此值将跳过"""

CHUNK_MAX_CHARS = 800
"""段落最大字符数，超过此值将进一步拆分"""


# ── 工具函数 ──────────────────────────────────────────────────────────────


def _count_chinese_chars(text: str) -> int:
    return len(re.findall(r'[\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff]', text))


def _detect_scene_type(text: str) -> str:
    scores: Dict[str, int] = {}
    for scene_type, keywords in SCENE_KEYWORDS.items():
        score = sum(text.count(kw) for kw in keywords)
        if score > 0:
            scores[scene_type] = score
    if not scores:
        return "描述"
    return max(scores, key=lambda k: scores.get(k, 0))


def _detect_emotion_tags(text: str) -> List[str]:
    tags = []
    for emotion, keywords in EMOTION_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            tags.append(emotion)
    return tags


def _detect_chunk_type(text: str) -> str:
    dialogue_count = sum(text.count(ind) for ind in DIALOGUE_INDICATORS)
    total_chars = len(text)
    if total_chars == 0:
        return "description"
    dialogue_density = dialogue_count / total_chars
    if dialogue_density > 0.04:
        return "dialogue"
    return "scene"


def _estimate_rhythm_intensity(text: str) -> float:
    intensity = 0.0

    conflict_words = SCENE_KEYWORDS.get("战斗", [])
    conflict_score = sum(text.count(w) for w in conflict_words) / max(len(text), 1)
    intensity += min(conflict_score * 20, 0.5)

    sentences = re.split(r'[。！？\n]', text)
    sentences = [s.strip() for s in sentences if s.strip()]
    if sentences:
        short_sentences = sum(1 for s in sentences if 1 < len(s) < 15)
        short_ratio = short_sentences / len(sentences)
        intensity += short_ratio * 0.25

    for kws in EMOTION_KEYWORDS.values():
        for kw in kws:
            if kw in text:
                intensity += 0.03

    return round(min(intensity, 1.0), 4)


def _detect_reasoning_pattern(text: str) -> Dict[str, bool]:
    pattern: Dict[str, bool] = {}
    for phase, keywords in REASONING_PHASE_KEYWORDS.items():
        pattern[phase] = any(kw in text for kw in keywords)
    return pattern


def _detect_dialogue_pattern(text: str) -> Dict[str, float]:
    quote_count = len(re.findall(r'["「」『』""]', text))
    tag_count = sum(text.count(tag) for tag in DIALOGUE_INDICATORS if len(tag) > 1)
    total = len(text)
    dialogue_ratio = (quote_count + tag_count) / max(total, 1)
    info_exchange = round(min(dialogue_ratio * 10, 1.0), 4)
    return {
        "dialogue_ratio": round(dialogue_ratio, 4),
        "info_exchange": info_exchange,
    }


# ── 文件读取与分段 ────────────────────────────────────────────────────────


def _read_md_files(ref_dir: str) -> List[Tuple[str, str]]:
    pattern = os.path.join(ref_dir, "**", "*.md")
    files = sorted(glob.glob(pattern, recursive=True))
    results: List[Tuple[str, str]] = []
    for fp in files:
        rel_path = os.path.relpath(fp, ref_dir)
        try:
            with open(fp, "r", encoding="utf-8") as f:
                content = f.read()
            results.append((rel_path, content))
        except Exception as e:
            print(f"  [跳过] 无法读取 {fp}: {e}")
    return results


def _merge_short_paragraphs(paragraphs: List[str], min_chars: int = 50) -> List[str]:
    merged: List[str] = []
    buffer = ""
    for para in paragraphs:
        if not para.strip():
            continue
        if len(buffer) < min_chars:
            buffer = (buffer + "\n\n" + para).strip()
        else:
            merged.append(buffer)
            buffer = para
    if buffer:
        merged.append(buffer)
    return merged


def _split_long_paragraph(text: str, max_chars: int) -> List[str]:
    if len(text) <= max_chars:
        return [text]
    splits: List[str] = []

    sentences = re.split(r'(?<=[。！？\n])', text)
    current = ""
    for sent in sentences:
        if not sent.strip():
            continue
        if len(current) + len(sent) > max_chars and current:
            splits.append(current.strip())
            current = sent
        else:
            current += sent
    if current.strip():
        splits.append(current.strip())
    return splits if splits else [text]


def _split_into_chunks(rel_path: str, text: str) -> List[Dict]:
    chunks: List[Dict] = []

    chapter_pattern = re.compile(r'^第[一二三四五六七八九十百千\d]+[章节]', re.MULTILINE)

    chapter_splits = list(chapter_pattern.finditer(text))

    if chapter_splits:
        for i, match in enumerate(chapter_splits):
            chapter_title = match.group().strip()
            chapter_start = match.end()
            chapter_end = chapter_splits[i + 1].start() if i + 1 < len(chapter_splits) else len(text)
            chapter_text = text[chapter_start:chapter_end].strip()

            raw_paragraphs = re.split(r'\n\s*\n', chapter_text)
            paragraphs = _merge_short_paragraphs(raw_paragraphs)

            for p_idx, para in enumerate(paragraphs):
                para = para.strip()
                if not para or _count_chinese_chars(para) < CHUNK_MIN_CHINESE_CHARS:
                    continue

                sub_paras = _split_long_paragraph(para, CHUNK_MAX_CHARS)
                for sp_idx, sp in enumerate(sub_paras):
                    chunk = _annotate_chunk(rel_path, chapter_title, sp)
                    chunks.append(chunk)
    else:
        raw_paragraphs = re.split(r'\n\s*\n', text)
        paragraphs = _merge_short_paragraphs(raw_paragraphs)

        for p_idx, para in enumerate(paragraphs):
            para = para.strip()
            if not para or _count_chinese_chars(para) < CHUNK_MIN_CHINESE_CHARS:
                continue

            sub_paras = _split_long_paragraph(para, CHUNK_MAX_CHARS)
            for sp_idx, sp in enumerate(sub_paras):
                chunk = _annotate_chunk(rel_path, "", sp)
                chunks.append(chunk)

    for idx, chunk in enumerate(chunks):
        raw_id = f"{chunk['metadata']['source_file']}#{idx}"
        chunk["id"] = hashlib.md5(raw_id.encode("utf-8")).hexdigest()

    return chunks


def _annotate_chunk(filepath: str, chapter: str, text: str) -> Dict:
    word_count = _count_chinese_chars(text)
    scene_type = _detect_scene_type(text)
    emotion_tags = _detect_emotion_tags(text)
    chunk_type = _detect_chunk_type(text)
    rhythm = _estimate_rhythm_intensity(text)
    reasoning = _detect_reasoning_pattern(text)
    dialogue = _detect_dialogue_pattern(text)

    return {
        "id": "",
        "text": text,
        "metadata": {
            "source_file": filepath,
            "chapter": chapter,
            "chunk_type": chunk_type,
            "scene_type": scene_type,
            "emotion_tags": ",".join(emotion_tags) if emotion_tags else "neutral",
            "word_count": word_count,
            "rhythm_intensity": rhythm,
            "reasoning_clue": str(reasoning.get("线索", False)),
            "reasoning_deduce": str(reasoning.get("推导", False)),
            "reasoning_exclude": str(reasoning.get("排除", False)),
            "reasoning_conclusion": str(reasoning.get("结论", False)),
            "dialogue_ratio": dialogue["dialogue_ratio"],
            "info_exchange": dialogue["info_exchange"],
        },
    }


# ── 命令行操作 ────────────────────────────────────────────────────────────


def _rebuild_collection():
    from src.storage.vector_store.chroma_client import get_chroma_client

    client = get_chroma_client()
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"  [删除] collection '{COLLECTION_NAME}' 已删除")
    except Exception:
        print(f"  [信息] collection '{COLLECTION_NAME}' 不存在，将新建")


def _list_vectorized():
    collection = get_or_create_collection(COLLECTION_NAME)
    all_data = collection.get(include=["metadatas"])
    if not all_data or not all_data["metadatas"]:
        print("  (空) 尚无已向量化的文件。")
        return

    files: Dict[str, int] = {}
    for meta in all_data["metadatas"]:
        if meta and "source_file" in meta:
            sf = meta["source_file"]
            files[sf] = files.get(sf, 0) + 1

    print(f"  共 {len(files)} 个已向量化文件:")
    for f in sorted(files):
        print(f"    - {f} ({files[f]} 个段落块)")
    print(f"\n  总计 {len(all_data['ids'])} 个段落块")


def _run_vectorize(rebuild: bool):
    if rebuild:
        _rebuild_collection()

    ref_dir = REFERENCE_NOVEL_DIR
    if not os.path.isdir(ref_dir):
        print(f"[错误] 参考小说目录不存在: {ref_dir}")
        sys.exit(1)

    print(f"  参考小说目录: {ref_dir}")
    md_files = _read_md_files(ref_dir)
    if not md_files:
        print("  (空) 未找到 .md 文件。")
        return

    print(f"  找到 {len(md_files)} 个 .md 文件")

    collection = get_or_create_collection(
        COLLECTION_NAME,
        metadata={"description": "参考小说向量库，用于风格参考与场景分析"},
    )

    existing_ids = set((collection.get() or {}).get("ids", [])) if not rebuild else set()

    total_added = 0
    total_skipped = 0

    for rel_path, content in md_files:
        chunks = _split_into_chunks(rel_path, content)
        file_added = 0
        file_skipped = 0

        batch_ids: List[str] = []
        batch_texts: List[str] = []
        batch_metadatas: List[Dict] = []

        for chunk in chunks:
            if chunk["id"] in existing_ids:
                file_skipped += 1
                continue
            batch_ids.append(chunk["id"])
            batch_texts.append(chunk["text"])
            batch_metadatas.append(chunk["metadata"])
            file_added += 1

        if batch_ids:
            collection.add(
                ids=batch_ids,
                documents=batch_texts,
                metadatas=batch_metadatas,
            )
            existing_ids.update(batch_ids)

        total_added += file_added
        total_skipped += file_skipped
        print(f"    [{rel_path}] 新增 {file_added} 个段落, 跳过 {file_skipped} 个")

    print(f"\n  完成! 共新增 {total_added} 个段落, 跳过 {total_skipped} 个段落")


# ── 入口 ──────────────────────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="将参考小说文本按段落/场景分割、标注多维信息后向量化存储到 ChromaDB"
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="重建 collection（删除已有数据后再导入）"
    )
    parser.add_argument(
        "--list", action="store_true",
        help="列出已向量化的文件列表"
    )
    args = parser.parse_args()

    if args.list:
        _list_vectorized()
        return

    if args.rebuild:
        confirm = input("  确认重建 collection？将删除所有已有数据 (y/N): ")
        if confirm.lower() != "y":
            print("  已取消。")
            return

    _run_vectorize(rebuild=args.rebuild)


if __name__ == "__main__":
    main()