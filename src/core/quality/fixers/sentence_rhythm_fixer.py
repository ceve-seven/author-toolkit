from __future__ import annotations

import statistics
from typing import Any, Dict, Optional

from src.core.quality.fixers.base_fixer import BaseFixer


class SentenceRhythmFixer(BaseFixer):
    """句子节奏修正器——破坏 AI 匀质句式，注入长短交替的节奏"""

    def fix(self, content: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修正句子节奏

        策略：
        - 长句（>30 字）按逗号拆分，部分改为句号
        - 短句（<10 字）与相邻句子合并
        """
        sentences = content.split("。")
        fixed: list[str] = []

        i = 0
        while i < len(sentences):
            sent = sentences[i].strip()
            if not sent:
                fixed.append(sentences[i])
                i += 1
                continue

            strategy = i % 3
            if strategy == 0 and len(sent) > 30:
                parts = sent.split("，")
                if len(parts) >= 3:
                    mid = len(parts) // 2
                    left = "".join(parts[:mid])
                    right = "，".join(parts[mid:])
                    fixed.append(left + "。")
                    fixed.append(right)
                else:
                    fixed.append(sentences[i])
            elif strategy == 1 and len(sent) < 10 and i + 1 < len(sentences):
                next_sent = sentences[i + 1].strip()
                if next_sent:
                    merged = sent + "，" + next_sent
                    fixed.append(merged)
                    i += 1
                else:
                    fixed.append(sentences[i])
            else:
                fixed.append(sentences[i])

            i += 1

        return "。".join(fixed)

    def validate(self, content: str) -> bool:
        """检查是否需要节奏修正"""
        sentences = [s for s in content.split("。") if len(s.strip()) > 0]
        if len(sentences) < 3:
            return False
        lengths = [len(s) for s in sentences]
        mean_len = statistics.mean(lengths)
        std_len = statistics.stdev(lengths) if len(lengths) > 1 else 0
        fluctuation = std_len / mean_len if mean_len > 0 else 1
        return fluctuation < 0.3