from __future__ import annotations

import random
from typing import Any, Dict, Optional


class TransitionWordFixer:
    """过渡词修复器

    减少过度使用的过渡词。
    L1 自动修复级别。
    """

    TRANSITION_WORDS = ["然而", "因此", "与此同时", "另外", "但是", "所以", "此外", "不过", "于是"]

    REPLACEMENTS: Dict[str, list] = {
        "然而": ["但", "可", "不过"],
        "因此": ["于是", "就这样", "这使"],
        "与此同时": ["这时", "就在此时", ""],
        "另外": ["还有", "此外", ""],
        "但是": ["可", "却", "不过"],
        "所以": ["于是", "就这样", "便"],
        "此外": ["另外", "还有", ""],
        "不过": ["但", "可", ""],
        "于是": ["便", "就", "就这样"],
    }

    def fix(self, text: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修复过渡词过度使用"""
        fixed = text
        for word in self.TRANSITION_WORDS:
            count = fixed.count(word)
            if count <= 1:
                continue

            remove_count = max(1, count // 3)
            positions: list[int] = []
            start = 0
            for _ in range(count):
                pos = fixed.find(word, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + len(word)

            remove_positions = set(random.sample(positions, min(remove_count, len(positions))))
            parts: list[str] = []
            last_end = 0
            for pos in sorted(positions):
                if pos in remove_positions:
                    parts.append(fixed[last_end:pos])
                    last_end = pos + len(word)
                else:
                    replacements = self.REPLACEMENTS.get(word, [])
                    if replacements:
                        repl = random.choice(replacements)
                        parts.append(fixed[last_end:pos])
                        if repl:
                            parts.append(repl)
                        last_end = pos + len(word)

            if last_end < len(fixed):
                parts.append(fixed[last_end:])
            fixed = "".join(parts)

        return fixed

    def validate(self, text: str) -> bool:
        """检查是否需要修复"""
        count = sum(text.count(w) for w in self.TRANSITION_WORDS)
        density = count / (max(len(text), 1) / 1000)
        return density > 15