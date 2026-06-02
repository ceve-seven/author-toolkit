from __future__ import annotations

from typing import Any, Dict, Optional

from src.core.quality.fixers.base_fixer import BaseFixer


class TransitionWordFixer(BaseFixer):
    """过渡词修正器——减少过度使用的过渡词"""

    TRANSITION_WORDS = ["然而", "因此", "与此同时", "另外", "但是", "所以", "此外", "不过", "于是"]

    def fix(self, content: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修正过渡词过度使用

        策略：
        - 随机删除 1/3 的过渡词
        - 部分过渡词替换为更自然的表达
        """
        import random
        fixed = content
        for word in self.TRANSITION_WORDS:
            count = fixed.count(word)
            if count <= 1:
                continue
            remove_count = count // 3
            if remove_count == 0:
                continue

            positions = []
            start = 0
            for _ in range(count):
                pos = fixed.find(word, start)
                if pos == -1:
                    break
                positions.append(pos)
                start = pos + len(word)

            remove_positions = set(random.sample(positions, min(remove_count, len(positions))))
            parts = []
            last_end = 0
            for pos in sorted(positions):
                if pos in remove_positions:
                    parts.append(fixed[last_end:pos])
                    if pos > 0 and fixed[pos - 1] in ("，", "。", "；"):
                        pass
                    elif pos + len(word) < len(fixed) and fixed[pos + len(word)] in ("，", "。"):
                        pass
                    else:
                        parts.append("，")
                    last_end = pos + len(word)
                else:
                    continue
            if last_end < len(fixed):
                parts.append(fixed[last_end:])
            fixed = "".join(parts)

        return fixed

    def validate(self, content: str) -> bool:
        """检查是否需要修正"""
        count = sum(content.count(w) for w in self.TRANSITION_WORDS)
        density = count / (max(len(content), 1) / 1000)
        return density > 15