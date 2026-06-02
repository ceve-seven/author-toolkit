from __future__ import annotations

import os
import re
import statistics
from dataclasses import dataclass
from typing import Any, Dict, List

import yaml


@dataclass
class TraceIssue:
    """AI 痕迹问题"""

    trait_type: str
    """特征类型标识"""
    severity: str
    """严重程度: critical / warning / info"""
    fix_level: int
    """修复级别: 1=自动, 2=半自动, 3=仅报告"""
    detail: str
    """问题详情"""
    position: int = 0
    """问题位置（字符偏移）"""
    suggestion: str = ""
    """修复建议"""


class AITraceDetector:
    """AI 痕迹检测器

    检测 19 大 AI 痕迹特征：
    1.  句式匀质化（sentence_rhythm_uniform）
    2.  过渡词依赖（transition_word_overuse）
    3.  情感说明（emotion_telling）
    4.  对话功能化（dialogue_functional）
    5.  描写模板化（description_templated）
    6.  安全化倾向（safety_bias）
    7.  章末钩子强度（weak_chapter_end）
    8.  节奏塌陷（rhythm_collapse）
    9.  直接情感告知（direct_emotion_telling）
    10. POV越界（pov_violation）
    11. 否定对比句（negation_pattern）——"不是A，是B"
    12. 比喻堆叠（simile_overuse）——"像/仿佛……一样"
    13. 同句式开头（sentence_start_repetition）
    14. 排比否定（negative_parallelism）——连续"不是"开句
    15. 结构性过渡词（discourse_marker_overuse）——"首先/其次/最后/总之"
    16. 模糊化表达（hedge_language）——"似乎/不禁/某种/仿佛"
    17. 动作模板（action_beat_repetition）——"微微一笑/陷入沉思"
    18. 情感反应模板（reaction_template）——"心头一紧/一股暖流"
    19. 标点 AI 模式（punctuation_ai_pattern）——破折号/省略号/叠用标点
    """

    TRANSITION_WORDS = ["然而", "因此", "与此同时", "另外", "但是", "所以", "此外", "不过", "于是"]

    EMOTION_LABELS = ["感到", "觉得", "心中充满", "内心", "感受到", "体会到"]

    DESCRIPTION_TEMPLATES = [
        "阳光透过", "微风拂过", "空气中弥漫", "映入眼帘",
        "深吸一口气", "时间仿佛", "无声的", "轻轻地",
        "缓缓地", "默默地", "静静地", "渐渐地",
    ]

    SAFETY_MARKERS = ["我们应该", "最好还是", "不太合适", "考虑到", "从某种角度来说"]

    NEGATION_PATTERN = re.compile(r'不是[^，。]*?，[^。]*?是[^。]*?。')

    SIMILE_PATTERNS = [
        re.compile(r'像[^，。]{1,30}一样'),
        re.compile(r'像[^，。]{1,30}一般'),
        re.compile(r'仿佛[^，。]{1,30}一样'),
        re.compile(r'仿佛[^，。]{1,30}一般'),
        re.compile(r'如同[^，。]{1,30}一样'),
        re.compile(r'如同[^，。]{1,30}一般'),
    ]

    DISCOURSE_MARKERS = [
        "首先", "其次", "再次", "最后", "总之", "总而言之", "总的来说",
        "值得注意的是", "需要指出的是", "不可否认", "众所周知",
        "换言之", "换句话说", "也就是说", "毋庸置疑",
        "综上所述", "由此可见", "不难看出",
        "一方面", "另一方面",
        "第一", "第二", "第三",
    ]

    HEDGE_WORDS = [
        "似乎", "或许", "也许", "大概", "可能",
        "不禁", "不由得", "忍不住",
        "某种", "某种程度", "某种意义上",
        "仿佛",
        "一种说不出的", "一种莫名的",
        "莫名地", "莫名地感到",
        "从未有过的",
    ]

    ACTION_BEATS = [
        "微微一笑", "点了点头", "摇了摇头", "点点头", "摇摇头",
        "陷入沉思", "陷入沉默",
        "深吸一口气", "长长地舒了一口气", "缓缓吐出一口气",
        "沉吟片刻", "沉吟了", "沉默了片刻", "沉默了半晌",
        "缓缓开口", "缓缓说道",
        "嘴角上扬", "嘴角勾起",
        "皱了皱眉", "皱起眉头", "眉头紧锁",
        "轻轻叹了口气", "叹了一口气", "叹了口气",
        "闭上了眼睛", "睁开眼睛",
    ]

    REACTION_TEMPLATES = [
        "心头一紧", "心头一暖", "心头一颤", "心头一震", "心头一酸",
        "心中一紧", "心中一暖", "心中一颤", "心中一酸",
        "一股暖流", "一股寒意", "一股暖意",
        "眼中闪过", "眼底闪过", "眸中闪过",
        "涌上心头", "涌了上来",
        "眼眶一红", "眼圈一红",
        "鼻头一酸", "鼻子一酸",
        "心里咯噔一下", "心头咯噔一下",
    ]

    EMDASH_PATTERN = re.compile(r'——')

    ELLIPSIS_PATTERN = re.compile(r'……')

    PUNCTUATION_COMBOS = re.compile(r'[！?？]{2,}|[？!！]{2,}|[。．]{3,}')

    def __init__(self):
        self.thresholds: Dict[str, Any] = {
            "sentence_fluctuation": 0.55,
            "transition_density": 6.0,
            "emotion_label_count": 2,
            "info_dialogue_ratio": 0.6,
            "template_hits": 1,
            "safety_count": 0,
            "hook_strength": 0.60,
            "rhythm_collapse": 800,
            "direct_emotion_telling": 0.10,
            "pov_violation": 1,
            "negation_max_per_200chars": 1,
            "negation_max_per_chapter": 10,
            "simile_max_per_500chars": 2,
            "simile_max_per_chapter": 5,
            "sentence_start_repetition_max": 0.15,
            "negative_parallelism_consecutive": 2,
            "discourse_marker_density": 3.0,
            "hedge_density": 3.0,
            "action_beat_hits": 3,
            "reaction_template_hits": 2,
            "punctuation_ai_pattern_density": 2.0,
        }

    def detect(self, text: str) -> List[TraceIssue]:
        """检测文本中的 AI 痕迹"""
        issues: List[TraceIssue] = []

        issues.extend(self._check_sentence_rhythm(text))
        issues.extend(self._check_transition_words(text))
        issues.extend(self._check_emotion_telling(text))
        issues.extend(self._check_dialogue_functional(text))
        issues.extend(self._check_description_templates(text))
        issues.extend(self._check_safety_bias(text))
        issues.extend(self._check_hook_strength(text))
        issues.extend(self._check_rhythm_collapse(text))
        issues.extend(self._check_direct_emotion_telling(text))
        issues.extend(self._check_pov_violation(text))
        issues.extend(self._check_negation_pattern(text))
        issues.extend(self._check_simile_overuse(text))
        issues.extend(self._check_sentence_start_repetition(text))
        issues.extend(self._check_negative_parallelism(text))
        issues.extend(self._check_discourse_marker_overuse(text))
        issues.extend(self._check_hedge_language(text))
        issues.extend(self._check_action_beat_repetition(text))
        issues.extend(self._check_reaction_template(text))
        issues.extend(self._check_punctuation_ai_pattern(text))

        return issues

    def _check_sentence_rhythm(self, text: str) -> List[TraceIssue]:
        """特征1: 句式匀质化检测"""
        issues: List[TraceIssue] = []
        sentence_lengths = [
            len(s) for s in text.replace("！", "。").replace("？", "。").split("。")
            if len(s) > 0
        ]
        if not sentence_lengths:
            return issues

        mean_len = statistics.mean(sentence_lengths)
        std_len = statistics.stdev(sentence_lengths) if len(sentence_lengths) > 1 else 0
        fluctuation = std_len / mean_len if mean_len > 0 else 1

        threshold = self.thresholds["sentence_fluctuation"]
        if fluctuation < threshold:
            issues.append(TraceIssue(
                trait_type="sentence_rhythm_uniform",
                severity="critical",
                fix_level=1,
                detail=f"句式波动系数 {fluctuation:.2f}（阈值 {threshold}），句子长度过于均匀",
                suggestion="通过长短句交替增加节奏变化，混合使用复合句和简单句",
            ))

        return issues

    def _check_transition_words(self, text: str) -> List[TraceIssue]:
        """特征2: 过渡词依赖检测"""
        issues: List[TraceIssue] = []
        word_count = max(len(text), 1)
        transition_count = sum(text.count(w) for w in self.TRANSITION_WORDS)
        density = transition_count / (word_count / 1000)

        threshold = self.thresholds["transition_density"]
        if density > threshold:
            issues.append(TraceIssue(
                trait_type="transition_word_overuse",
                severity="warning",
                fix_level=1,
                detail=f"过渡词密度 {density:.1f} 次/千字（阈值 {threshold}）",
                suggestion="减少过渡词使用频率，改用直接逻辑连接或通过上下文暗示关系",
            ))

        return issues

    def _check_emotion_telling(self, text: str) -> List[TraceIssue]:
        """特征3: 情感说明检测"""
        issues: List[TraceIssue] = []
        emotion_count = sum(text.count(w) for w in self.EMOTION_LABELS)

        threshold = self.thresholds["emotion_label_count"]
        if emotion_count > threshold:
            issues.append(TraceIssue(
                trait_type="emotion_telling",
                severity="warning",
                fix_level=2,
                detail=f"情感标签出现 {emotion_count} 次（阈值 {threshold}）",
                suggestion="用具体行为、动作和环境描写来展示情感，而非直接说明",
            ))

        return issues

    def _check_dialogue_functional(self, text: str) -> List[TraceIssue]:
        """特征4: 对话功能化检测"""
        issues: List[TraceIssue] = []
        dialogue_lines = re.findall(r'[""]([^""]{10,})[""]', text)
        if not dialogue_lines:
            return issues

        info_dense = sum(1 for line in dialogue_lines if self._is_info_dense(line))
        ratio = info_dense / len(dialogue_lines)

        threshold = self.thresholds["info_dialogue_ratio"]
        if ratio > threshold:
            issues.append(TraceIssue(
                trait_type="dialogue_functional",
                severity="warning",
                fix_level=2,
                detail=f"信息密集型对话占比 {info_dense}/{len(dialogue_lines)}（阈值 {threshold:.0%}）",
                suggestion="在对话中加入潜台词、停顿、动作描写和非语言信息",
            ))

        return issues

    def _check_description_templates(self, text: str) -> List[TraceIssue]:
        """特征5: 描写模板化检测"""
        issues: List[TraceIssue] = []
        template_hits = sum(1 for t in self.DESCRIPTION_TEMPLATES if t in text)

        threshold = self.thresholds["template_hits"]
        if template_hits >= threshold:
            issues.append(TraceIssue(
                trait_type="description_templated",
                severity="warning",
                fix_level=1,
                detail=f"匹配 {template_hits} 个常见描写模板（阈值 {threshold}）",
                suggestion="用更独特、具体的观察替换模板化描写，突出叙事视角的独特性",
            ))

        return issues

    def _check_safety_bias(self, text: str) -> List[TraceIssue]:
        """特征6: 安全化倾向检测"""
        issues: List[TraceIssue] = []
        safety_count = sum(text.count(m) for m in self.SAFETY_MARKERS)

        threshold = self.thresholds["safety_count"]
        if safety_count > threshold:
            issues.append(TraceIssue(
                trait_type="safety_bias",
                severity="info",
                fix_level=3,
                detail=f"检测到 {safety_count} 处安全化表达",
                suggestion="安全化表达可能削弱叙事张力，建议根据角色性格使用更直接的语言",
            ))

        return issues

    def _check_hook_strength(self, text: str) -> List[TraceIssue]:
        """特征7: 章末钩子强度检测"""
        issues: List[TraceIssue] = []
        chapters = re.split(r'(?:第[\u4e00-\u9fff\d]+[章回部节])', text)

        hook_patterns = {
            "question": r'[？?]|为什么|怎么|难道|能否|是否|有没有',
            "suspense": r'…{2,}|未知|神秘|诡异|突然|就在这时|意想不到|谁也没有想到',
            "twist": r'但[是]?|却|竟然|居然|没想到|出乎意料|反转',
            "emotion": r'震惊|恐惧|喜悦|悲伤|愤怒|感动|泪流|心如刀绞|心头一[紧震颤]',
        }

        weak_ends = 0
        total_chapters = 0

        for ch in chapters:
            ch = ch.strip()
            if len(ch) < 300:
                continue
            total_chapters += 1
            ending = ch[-300:]

            has_hook = any(re.search(pattern, ending) for pattern in hook_patterns.values())

            if not has_hook:
                weak_ends += 1

        if total_chapters == 0:
            return issues

        strength = 1 - (weak_ends / total_chapters)
        threshold = self.thresholds["hook_strength"]
        if strength < threshold:
            issues.append(TraceIssue(
                trait_type="weak_chapter_end",
                severity="warning",
                fix_level=2,
                detail=f"章末钩子强度 {strength:.2f}（阈值 {threshold}），{weak_ends}/{total_chapters} 章结尾缺乏悬念",
                suggestion="在章节结尾增加问题钩子、悬念钩子、反转钩子或情感钩子",
            ))

        return issues

    def _check_rhythm_collapse(self, text: str) -> List[TraceIssue]:
        """特征8: 节奏塌陷检测"""
        issues: List[TraceIssue] = []
        sentences = re.split(r'[。！？\n]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]

        rhythm_markers = [
            "原来", "真相", "发现", "知道", "意识到", "明白",
            "愤怒", "悲伤", "喜悦", "恐惧", "惊讶", "震惊", "感动", "绝望",
            "突然", "诡异", "不对劲", "危险", "小心", "难道", "究竟",
            "来到", "走进", "离开", "回到", "推开", "穿过", "进入",
        ]

        threshold = self.thresholds["rhythm_collapse"]

        segment_length = 0

        for i, sentence in enumerate(sentences):
            has_rhythm = any(marker in sentence for marker in rhythm_markers)

            if has_rhythm:
                if segment_length > threshold:
                    issues.append(TraceIssue(
                        trait_type="rhythm_collapse",
                        severity="warning",
                        fix_level=2,
                        detail=f"连续 {segment_length} 字无节奏变化（阈值 {threshold}字）",
                        suggestion="插入信息揭露、情绪变化、悬念强化或场景切换以打破节奏",
                    ))
                segment_length = 0
            else:
                segment_length += len(sentence)

        if segment_length > threshold:
            issues.append(TraceIssue(
                trait_type="rhythm_collapse",
                severity="warning",
                fix_level=2,
                detail=f"连续 {segment_length} 字无节奏变化（阈值 {threshold}字）",
                suggestion="插入信息揭露、情绪变化、悬念强化或场景切换以打破节奏",
            ))

        return issues

    def _check_direct_emotion_telling(self, text: str) -> List[TraceIssue]:
        """特征9: 直接情感告知检测"""
        issues: List[TraceIssue] = []

        emotion_patterns = [
            r'他感到\w+', r'她感到\w+', r'我感到\w+',
            r'他[愤怒悲伤喜悦恐惧绝望痛苦]',
            r'她[愤怒悲伤喜悦恐惧绝望痛苦]',
            r'心中充满\w+', r'内心充满\w+',
            r'心里一[紧酸楚难受温暖感动]',
            r'一股[怒火悲伤喜悦恐惧]\w*涌',
        ]

        total_count = 0
        for pattern in emotion_patterns:
            total_count += len(re.findall(pattern, text))

        word_count = max(len(text), 1)
        density = total_count / (word_count / 1000)

        threshold = self.thresholds["direct_emotion_telling"]
        if density > threshold:
            issues.append(TraceIssue(
                trait_type="direct_emotion_telling",
                severity="warning",
                fix_level=1,
                detail=f"直接情感标签密度 {density:.2f} 次/千字（阈值 {threshold}）",
                suggestion="用具体动作、环境和细节描写来间接传递情感，避免直接情感标签",
            ))

        return issues

    def _check_pov_violation(self, text: str) -> List[TraceIssue]:
        """特征10: POV越界检测"""
        issues: List[TraceIssue] = []
        scenes = re.split(r'(?:第[\u4e00-\u9fff\d]+[章回部节]|\n{3,})', text)

        thought_markers = ["想", "觉得", "心里", "暗自", "暗暗", "心道", "寻思", "琢磨", "盘算"]

        violation_count = 0

        for scene in scenes:
            if not scene.strip():
                continue

            pov_chars = re.findall(
                r'^[^。！？\n]{0,30}?([\u4e00-\u9fff]{2,4})[的先是看了望转说]',
                scene,
                re.MULTILINE,
            )
            if not pov_chars:
                continue
            pov_char = pov_chars[0]

            for marker in thought_markers:
                pattern = rf'([\u4e00-\u9fff]{{2,4}}){marker}'
                matches = re.findall(pattern, scene)
                for match in matches:
                    if match != pov_char:
                        violation_count += 1

        threshold = self.thresholds["pov_violation"]
        if violation_count > threshold:
            issues.append(TraceIssue(
                trait_type="pov_violation",
                severity="critical",
                fix_level=3,
                detail=f"检测到 {violation_count} 处POV越界（阈值 {threshold}）",
                suggestion="限制心理活动描写仅限于当前POV角色，避免描述其他角色内心想法",
            ))

        return issues

    def _check_negation_pattern(self, text: str) -> List[TraceIssue]:
        """特征11: "不是A，是B" 否定对比句检测

        这是 AI 输出中最明显的语言模式之一。
        规则：同200字内超过1处、或同章超过10处"不是"→判定为AI痕迹。
        """
        issues: List[TraceIssue] = []

        negation_matches = list(self.NEGATION_PATTERN.finditer(text))
        total_count = len(negation_matches)

        chapter_threshold = self.thresholds["negation_max_per_chapter"]
        if total_count > chapter_threshold:
            issues.append(TraceIssue(
                trait_type="negation_pattern",
                severity="critical",
                fix_level=2,
                detail=f"否定对比句（不是A，是B）全章 {total_count} 处（阈值 {chapter_threshold}）",
                suggestion="将否定对比句改为直接肯定陈述，如'规则是物理法则'而非'不是警告，不是威胁，是物理法则'",
            ))
            return issues

        density_threshold = self.thresholds["negation_max_per_200chars"]
        for i, match in enumerate(negation_matches):
            start = max(0, match.start() - 100)
            end = min(len(text), match.end() + 100)
            nearby = sum(1 for m in negation_matches if start <= m.start() <= end)
            if nearby > density_threshold:
                issues.append(TraceIssue(
                    trait_type="negation_pattern",
                    severity="critical",
                    fix_level=2,
                    detail=f"200字内出现 {nearby} 处否定对比句（阈值 {density_threshold}）",
                    suggestion=f"将'不是……是……'改为直接肯定陈述",
                    position=match.start(),
                ))
                break

        return issues

    def _check_simile_overuse(self, text: str) -> List[TraceIssue]:
        """特征12: "像/仿佛……一样" 比喻堆叠检测"""
        issues: List[TraceIssue] = []

        total_similes = 0
        for pattern in self.SIMILE_PATTERNS:
            total_similes += len(pattern.findall(text))

        chapter_threshold = self.thresholds["simile_max_per_chapter"]
        if total_similes > chapter_threshold:
            issues.append(TraceIssue(
                trait_type="simile_overuse",
                severity="warning",
                fix_level=1,
                detail=f"比喻句式全章 {total_similes} 处（阈值 {chapter_threshold}），比喻过于频繁",
                suggestion="精简比喻数量，每章不超过3处。能用具体描写替代的，就不用比喻",
            ))
            return issues

        density_threshold = self.thresholds["simile_max_per_500chars"]
        segments = [text[i:i + 500] for i in range(0, max(len(text), 1), 500)]
        for seg_idx, seg in enumerate(segments):
            seg_count = 0
            for pattern in self.SIMILE_PATTERNS:
                seg_count += len(pattern.findall(seg))
            if seg_count > density_threshold:
                issues.append(TraceIssue(
                    trait_type="simile_overuse",
                    severity="warning",
                    fix_level=1,
                    detail=f"第 {seg_idx + 1} 个500字区间比喻 {seg_count} 处（阈值 {density_threshold}）",
                    suggestion="减少该段落中的比喻，用具体描写替代",
                ))
                break

        return issues

    def _check_sentence_start_repetition(self, text: str) -> List[TraceIssue]:
        """特征13: 同句式开头率检测

        检测以"他/她/它/这/那"开头的句子比例是否超过15%。
        """
        issues: List[TraceIssue] = []
        sentences = [s.strip() for s in text.replace("！", "。").replace("？", "。").split("。") if s.strip()]
        if len(sentences) < 5:
            return issues

        same_start_chars = {"他", "她", "它", "这", "那"}
        same_start_count = 0
        for s in sentences:
            if s and s[0] in same_start_chars:
                same_start_count += 1

        ratio = same_start_count / len(sentences)
        threshold = self.thresholds["sentence_start_repetition_max"]
        if ratio > threshold:
            issues.append(TraceIssue(
                trait_type="sentence_start_repetition",
                severity="critical",
                fix_level=2,
                detail=f"同主语开头句占比 {ratio:.1%}（阈值 {threshold:.0%}），{same_start_count}/{len(sentences)} 句以{''.join(sorted(same_start_chars))}开头",
                suggestion="用时间状语、地点状语、动作结果、短句或对话来替换部分主语开头",
            ))

        return issues

    def _check_negative_parallelism(self, text: str) -> List[TraceIssue]:
        """特征14: 排比否定堆叠检测

        检测连续2句以上以"不是"开头的排比结构。
        """
        issues: List[TraceIssue] = []
        sentences = [s.strip() for s in text.split("。") if s.strip()]
        if len(sentences) < 3:
            return issues

        threshold = self.thresholds["negative_parallelism_consecutive"]
        consecutive = 0
        for s in sentences:
            if s.startswith("不是"):
                consecutive += 1
                if consecutive >= threshold:
                    issues.append(TraceIssue(
                        trait_type="negative_parallelism",
                        severity="critical",
                        fix_level=2,
                        detail=f"连续 {consecutive} 句以'不是'开头（阈值 {threshold}），排比否定堆叠",
                        suggestion="去掉排比结构，只保留一句肯定陈述；将否定句改为肯定句叙述",
                    ))
                    return issues
            else:
                consecutive = 0

        return issues

    def _check_discourse_marker_overuse(self, text: str) -> List[TraceIssue]:
        """特征15: 结构性过渡词过频检测

        AI 倾向使用"首先/其次/最后""值得注意的是""综上所述"等
        结构化论述标记，在小说正文中显得生硬。
        """
        issues: List[TraceIssue] = []
        total_count = sum(text.count(m) for m in self.DISCOURSE_MARKERS)
        word_count = max(len(text), 1)
        density = total_count / (word_count / 1000)

        threshold = self.thresholds["discourse_marker_density"]
        if density > threshold:
            issues.append(TraceIssue(
                trait_type="discourse_marker_overuse",
                severity="critical",
                fix_level=2,
                detail=f"结构性过渡词密度 {density:.1f} 次/千字（阈值 {threshold}），论述式表达过多",
                suggestion="删除'首先/其次/值得注意的是'等论述标记，改用直接叙述推进情节",
            ))

        return issues

    def _check_hedge_language(self, text: str) -> List[TraceIssue]:
        """特征16: 模糊化表达过频检测

        AI 倾向大量使用"似乎/或许/不禁/某种/仿佛"等模糊化词汇，
        削弱了叙述的确定性和力量感。
        """
        issues: List[TraceIssue] = []
        total_count = sum(text.count(w) for w in self.HEDGE_WORDS)
        word_count = max(len(text), 1)
        density = total_count / (word_count / 1000)

        threshold = self.thresholds["hedge_density"]
        if density > threshold:
            issues.append(TraceIssue(
                trait_type="hedge_language",
                severity="warning",
                fix_level=2,
                detail=f"模糊化表达密度 {density:.1f} 次/千字（阈值 {threshold}），包含'似乎/不禁/某种'等",
                suggestion="减少模糊化词汇，用具体细节和确定性的叙述替代'似乎''仿佛'",
            ))

        return issues

    def _check_action_beat_repetition(self, text: str) -> List[TraceIssue]:
        """特征17: 动作模板重复检测

        AI 反复使用"微微一笑""点了点头""陷入沉思""深吸一口气"
        等套路化动作描写，缺乏人物个性化的肢体语言。
        """
        issues: List[TraceIssue] = []
        total_hits = sum(text.count(b) for b in self.ACTION_BEATS)

        threshold = self.thresholds["action_beat_hits"]
        if total_hits >= threshold:
            issues.append(TraceIssue(
                trait_type="action_beat_repetition",
                severity="warning",
                fix_level=2,
                detail=f"检测到 {total_hits} 处套路化动作模板（阈值 {threshold}），如'微微一笑/陷入沉思'",
                suggestion="用具体、个性化的肢体语言替代模板化动作描写，让动作体现角色性格",
            ))

        return issues

    def _check_reaction_template(self, text: str) -> List[TraceIssue]:
        """特征18: 情感反应模板检测

        AI 大量使用"心头一紧""一股暖流""眼中闪过""鼻头一酸"
        等公式化的情感反应描写。
        """
        issues: List[TraceIssue] = []
        total_hits = sum(text.count(t) for t in self.REACTION_TEMPLATES)

        threshold = self.thresholds["reaction_template_hits"]
        if total_hits >= threshold:
            issues.append(TraceIssue(
                trait_type="reaction_template",
                severity="warning",
                fix_level=2,
                detail=f"检测到 {total_hits} 处情感反应模板（阈值 {threshold}），如'心头一紧/一股暖流'",
                suggestion="用独特、具体的情感体验替代公式化反应模板，避免'心头一紧''鼻头一酸'等套话",
            ))

        return issues

    def _check_punctuation_ai_pattern(self, text: str) -> List[TraceIssue]:
        """特征19: 标点符号 AI 痕迹检测

        AI 输出中存在明显的标点符号特征：
        - 破折号"——"过频使用（用于解释/强调/戏剧停顿）
        - 省略号"……"过频使用（用于拖尾/犹豫/神秘化）
        - 叠用标点"！！？？！？。。"等
        """
        issues: List[TraceIssue] = []

        emdash_count = len(self.EMDASH_PATTERN.findall(text))
        ellipsis_count = len(self.ELLIPSIS_PATTERN.findall(text))
        combo_count = len(self.PUNCTUATION_COMBOS.findall(text))

        word_count = max(len(text), 1)
        chars_per_k = word_count / 1000

        emdash_per_k = emdash_count / max(chars_per_k, 0.1)

        threshold = self.thresholds["punctuation_ai_pattern_density"]

        total_weighted = (
            emdash_count * 1.5
            + ellipsis_count * 1.2
            + combo_count
        )
        weighted_density = total_weighted / max(chars_per_k, 0.1)

        if weighted_density < threshold:
            return issues

        detail_parts = []
        if emdash_per_k > 0.8:
            detail_parts.append(f"破折号{emdash_count}处({emdash_per_k:.1f}次/千字)")
        if ellipsis_count > 3 and ellipsis_count / max(chars_per_k, 0.1) > 1.0:
            detail_parts.append(f"省略号{ellipsis_count}处")
        if combo_count > 0:
            detail_parts.append(f"叠用标点{combo_count}处")

        if not detail_parts:
            return issues

        issues.append(TraceIssue(
            trait_type="punctuation_ai_pattern",
            severity="warning",
            fix_level=2,
            detail=f"标点AI痕迹: {'; '.join(detail_parts)}（综合密度 {weighted_density:.1f}）",
            suggestion="减少破折号使用频率，能用'是/就是'直接表达的不用破折号；减少省略号，用具体描写替代留白；避免叠用标点",
        ))

        return issues

    def load_thresholds_from_config(self, config_data: Dict[str, Any]) -> None:
        """从配置字典加载阈值"""
        detection = config_data.get("ai_trace_thresholds", {}).get("detection", {})
        if not detection:
            return

        key_map = {
            "uniform_sentence_structure": "sentence_fluctuation",
            "transition_word_overuse": "transition_density",
            "emotion_telling": "emotion_label_count",
            "functional_dialogue": "info_dialogue_ratio",
            "templated_description": "template_hits",
            "safety_bias": "safety_count",
            "hook_strength": "hook_strength",
            "rhythm_collapse": "rhythm_collapse",
            "direct_emotion_telling": "direct_emotion_telling",
            "pov_violation": "pov_violation",
            "negation_pattern": "negation_max_per_200chars",
            "simile_overuse": "simile_max_per_500chars",
            "sentence_start_repetition": "sentence_start_repetition_max",
            "negative_parallelism": "negative_parallelism_consecutive",
            "discourse_marker_overuse": "discourse_marker_density",
            "hedge_language": "hedge_density",
            "action_beat_repetition": "action_beat_hits",
            "reaction_template": "reaction_template_hits",
            "punctuation_ai_pattern": "punctuation_ai_pattern_density",
        }

        for config_key, config_value in detection.items():
            internal_key = key_map.get(config_key)
            if internal_key and isinstance(config_value, dict) and config_value.get("enabled", True):
                self.thresholds[internal_key] = config_value["threshold"]

    def update_thresholds_from_yaml(self, yaml_path: str | None = None) -> bool:
        """读取 src/config/ai_trace_thresholds.yaml 并更新阈值"""
        if yaml_path is None:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
            yaml_path = os.path.join(base_dir, "src", "config", "ai_trace_thresholds.yaml")

        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                config_data = yaml.safe_load(f)
            self.load_thresholds_from_config(config_data)
            return True
        except Exception:
            return False

    def _is_info_dense(self, line: str) -> bool:
        """判断对话行是否仅用于传递信息"""
        info_markers = [
            "因为", "所以", "因此", "根据", "按照", "首先", "其次",
            "你的任务是", "你需要", "你必须", "听好", "记住",
            "情况是", "问题是", "原因是",
        ]
        return any(marker in line for marker in info_markers)

    def update_thresholds(self, new_thresholds: Dict[str, Any]):
        """更新检测阈值"""
        self.thresholds.update(new_thresholds)

    def describe_issues(self, issues: List[TraceIssue]) -> str:
        """将问题列表格式化为可读文本"""
        if not issues:
            return "未检测到 AI 痕迹问题"

        lines = ["AI 痕迹检测报告:", ""]
        level_labels = {1: "L1 自动修复", 2: "L2 半自动", 3: "L3 仅报告"}

        for issue in issues:
            lines.append(f"  [{issue.severity.upper()}] {issue.trait_type}")
            lines.append(f"    详情: {issue.detail}")
            lines.append(f"    级别: {level_labels.get(issue.fix_level, '未知')}")
            if issue.suggestion:
                lines.append(f"    建议: {issue.suggestion}")
            lines.append("")

        return "\n".join(lines)
