from __future__ import annotations

import re
from typing import Any, Dict, Optional


class SimileFixer:
    """比喻堆叠修复器

    检测并减少过度使用的比喻句式（像/仿佛/如同/宛如/好似）。
    L1 自动修复级别。
    """

    SIMILE_PATTERNS = [
        r"像[\w\s]{0,10}一样",
        r"仿佛[\w\s]{0,15}",
        r"如同[\w\s]{0,15}",
        r"宛如[\w\s]{0,15}",
        r"好似[\w\s]{0,10}",
    ]

    def fix(self, text: str, params: Optional[Dict[str, Any]] = None) -> str:
        """修复比喻堆叠

        策略：
        - 在 500 字窗口内发现多个比喻时，保留第一个，删除后续的
        """
        matches = []
        for pattern in self.SIMILE_PATTERNS:
            for m in re.finditer(pattern, text):
                matches.append((m.start(), m.end(), pattern))

        if len(matches) < 2:
            return text

        matches.sort(key=lambda x: x[0])

        windows = []
        window_start = 0
        for i in range(len(matches)):
            if matches[i][0] - matches[window_start][0] > 500:
                windows.append(matches[window_start:i])
                window_start = i
        windows.append(matches[window_start:])

        remove_positions = set()
        for w in windows:
            for m in w[1:]:
                if m[0] not in remove_positions:
                    remove_positions.add(m[0])

        parts = []
        last_end = 0
        for _, end, _ in sorted(matches, key=lambda x: x[0]):
            if _ in remove_positions:
                parts.append(text[last_end:_])
                last_end = end

        if last_end < len(text):
            parts.append(text[last_end:])
        return "".join(parts)

    def validate(self, text: str) -> bool:
        """检查是否需要修复"""
        count = 0
        for pattern in self.SIMILE_PATTERNS:
            count += len(re.findall(pattern, text))
        return count >= 2
