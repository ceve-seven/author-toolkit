"""
测试 AI 痕迹检测和清除流水线。

本测试覆盖：
1. ai_trace_thresholds.yaml 的加载和解析
2. AI 痕迹检测器的 6 大特征检测
3. 三级清除流水线的编排
4. 自动修复器的基本功能
"""

import sys
from pathlib import Path

import pytest
import yaml

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =========================================================================
# Fixtures
# =========================================================================

@pytest.fixture(scope="module")
def ai_trace_config() -> dict:
    """加载 ai_trace_thresholds.yaml"""
    yaml_path = PROJECT_ROOT / "src" / "config" / "ai_trace_thresholds.yaml"
    assert yaml_path.exists(), f"配置文件不存在: {yaml_path}"
    with open(yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    assert data is not None
    return data


@pytest.fixture(scope="module")
def thresholds(ai_trace_config) -> dict:
    """返回 detection 节下的阈值配置"""
    assert "ai_trace_thresholds" in ai_trace_config
    assert "detection" in ai_trace_config["ai_trace_thresholds"]
    return ai_trace_config["ai_trace_thresholds"]["detection"]


@pytest.fixture(scope="module")
def fix_strategy(ai_trace_config) -> dict:
    """返回 fix_strategy 节下的分级修复策略"""
    return ai_trace_config["ai_trace_thresholds"]["fix_strategy"]


@pytest.fixture
def ai_generated_text() -> str:
    """模拟 AI 生成的文本，包含各种 AI 痕迹"""
    return (
        "陈渡走进房间，阳光透过窗帘洒在地板上。"
        "他感到内心充满了不安。"
        "然而，他仍然决定继续前进。"
        "因此，他深吸一口气，推开了门。"
        "与此同时，另一个人从侧门走了进来。"
        "他感到一阵寒意。"
        "空气中弥漫着一股奇怪的气味。"
        "时间仿佛在这一刻凝固了。"
        "但是他没有停下来。"
        "所以他继续向前走。"
        "他觉得事情不太对劲。"
        "然而他必须完成这个任务。"
        "于是他又加快了脚步。"
    )


@pytest.fixture
def natural_text() -> str:
    """模拟人类创作的文本，无明显 AI 痕迹"""
    return (
        "门开了。陈渡站在门口，眯起眼。"
        "阳光切过窗帘——一道白线割开暗红的地板。"
        "三秒。五秒。他数着自己的呼吸。"
        "陈渡迈了一步。地板在他脚下咯吱作响，像某种警告。"
        " \"你来晚了。\" 暗处有声音说。"
        "陈渡没回答。他在等眼睛适应黑暗。"
        "十二年了，他还是不习惯这种重逢。"
    )


# =========================================================================
# 阈值配置测试
# =========================================================================

class TestThresholdConfig:
    """测试 AI 痕迹阈值配置的正确性"""

    def test_thresholds_yaml_loads(self, ai_trace_config):
        """ai_trace_thresholds.yaml 能正确加载"""
        assert "ai_trace_thresholds" in ai_trace_config
        config = ai_trace_config["ai_trace_thresholds"]
        assert "detection" in config
        assert "fix_strategy" in config

    def test_all_detectors_exist(self, thresholds):
        """所有特征检测器配置都存在"""
        expected = {
            "uniform_sentence_structure",
            "transition_word_overuse",
            "emotion_telling",
            "functional_dialogue",
            "templated_description",
            "safety_bias",
            "hook_strength",
            "rhythm_collapse",
            "direct_emotion_telling",
            "pov_violation",
            "negation_pattern",
            "simile_overuse",
            "sentence_start_repetition",
            "negative_parallelism",
            "discourse_marker_overuse",
            "hedge_language",
            "action_beat_repetition",
            "reaction_template",
            "punctuation_ai_pattern",
        }
        actual = set(thresholds.keys())
        missing = expected - actual
        assert not missing, f"缺少以下检测器配置: {missing}"

    def test_each_detector_has_required_fields(self, thresholds):
        """每个检测器配置都有 enabled/threshold/description 字段"""
        for name, config in thresholds.items():
            assert isinstance(config, dict), f"检测器 {name} 的配置不是字典"
            assert "enabled" in config, f"检测器 {name} 缺少 enabled"
            assert "threshold" in config, f"检测器 {name} 缺少 threshold"
            assert "description" in config, f"检测器 {name} 缺少 description"

    def test_threshold_values_in_range(self, thresholds):
        """非字符数/计数类阈值在 0-1 之间"""
        exclude = {
            "rhythm_collapse",
            "transition_word_overuse",
            "emotion_telling",
            "templated_description",
            "safety_bias",
            "simile_overuse",
            "negative_parallelism",
            "pov_violation",
            "negation_pattern",
            "discourse_marker_overuse",
            "hedge_language",
            "action_beat_repetition",
            "reaction_template",
            "punctuation_ai_pattern",
        }
        for name, config in thresholds.items():
            if name in exclude:
                continue
            t = config["threshold"]
            assert 0 <= t <= 1, f"检测器 {name} 的阈值 {t} 不在 [0,1] 范围内"

    def test_fix_strategy_three_levels(self, fix_strategy):
        """修复策略分三级"""
        assert "level1_auto_fix" in fix_strategy, "缺少 level1_auto_fix"
        assert "level2_semi_auto" in fix_strategy, "缺少 level2_semi_auto"
        assert "level3_report_only" in fix_strategy, "缺少 level3_report_only"

    def test_fix_level_coverage(self, fix_strategy, thresholds):
        """所有检测器都在某个修复级别中"""
        all_detectors = set(thresholds.keys())
        covered = set()
        for level in ["level1_auto_fix", "level2_semi_auto", "level3_report_only"]:
            covered.update(fix_strategy.get(level, []))
        uncovered = all_detectors - covered
        assert not uncovered, f"以下检测器未被任何修复级别覆盖: {uncovered}"


# =========================================================================
# 特征检测算法测试（纯静态分析）
# =========================================================================

class _Detector:
    """
    简化的 AI 痕迹检测器（测试用）。
    模拟 src/ai_purifier/detector.py 中的检测逻辑。
    """

    @staticmethod
    def detect_uniform_sentence(text: str, threshold: float = 0.3) -> bool:
        """检测句式匀质化：计算句式波动系数"""
        import statistics
        sentences = [s for s in text.replace("！", "。").replace("？", "。").split("。") if s.strip()]
        if len(sentences) < 2:
            return False
        lengths = [len(s) for s in sentences]
        mean = statistics.mean(lengths)
        std = statistics.stdev(lengths)
        fluctuation = std / mean if mean > 0 else 1
        return fluctuation < threshold

    @staticmethod
    def detect_transition_overuse(text: str, threshold: float = 15.0) -> bool:
        """检测过渡词过度使用"""
        transition_words = ["然而", "因此", "与此同时", "另外", "但是", "所以", "此外", "不过", "于是"]
        word_count = max(len(text), 1)
        transition_count = sum(text.count(w) for w in transition_words)
        density = transition_count / (word_count / 1000)
        return density > threshold

    @staticmethod
    def detect_emotion_telling(text: str, threshold: int = 3) -> bool:
        """检测情感告知化表达"""
        emotion_labels = ["感到", "觉得", "心中充满", "内心", "感受到", "体会到"]
        emotion_count = sum(text.count(w) for w in emotion_labels)
        return emotion_count > threshold

    @staticmethod
    def detect_templated_description(text: str, threshold: int = 2) -> bool:
        """检测描写模板化"""
        templates = ["阳光透过", "微风拂过", "空气中弥漫", "映入眼帘",
                     "深吸一口气", "时间仿佛", "无声的"]
        template_hits = sum(1 for t in templates if t in text)
        return template_hits >= threshold

    @staticmethod
    def detect_safety_bias(text: str) -> bool:
        """检测安全化倾向"""
        safety_markers = ["我们应该", "最好还是", "不太合适", "考虑到"]
        safety_count = sum(text.count(m) for m in safety_markers)
        return safety_count > 0


class TestDetectorAlgorithms:
    """测试 6 大特征检测算法的正确性"""

    def test_uniform_sentence_detects_ai_text(self, ai_generated_text):
        """AI 生成文本应被检测为句式匀质化"""
        result = _Detector.detect_uniform_sentence(ai_generated_text, threshold=0.3)
        assert result is True

    def test_uniform_sentence_passes_natural_text(self, natural_text):
        """自然文本应通过句式匀质化检测"""
        result = _Detector.detect_uniform_sentence(natural_text, threshold=0.3)
        assert result is False

    def test_transition_overuse_detects_ai_text(self, ai_generated_text):
        """AI 生成文本应被检测为过渡词过度使用（阈值 15 次/千字）"""
        result = _Detector.detect_transition_overuse(ai_generated_text, threshold=15.0)
        assert result is True

    def test_transition_overuse_passes_natural_text(self, natural_text):
        """自然文本应通过过渡词密度检测"""
        result = _Detector.detect_transition_overuse(natural_text, threshold=15.0)
        assert result is False

    def test_emotion_telling_detects_ai_text(self, ai_generated_text):
        """AI 生成文本应被检测为情感告知化"""
        result = _Detector.detect_emotion_telling(ai_generated_text, threshold=3)
        assert result is True

    def test_emotion_telling_passes_natural_text(self, natural_text):
        """自然文本应通过情感告知化检测"""
        result = _Detector.detect_emotion_telling(natural_text, threshold=3)
        assert result is False

    def test_templated_description_detects_ai_text(self, ai_generated_text):
        """AI 生成文本应被检测为描写模板化"""
        result = _Detector.detect_templated_description(ai_generated_text, threshold=2)
        assert result is True

    def test_templated_description_passes_natural_text(self, natural_text):
        """自然文本应通过描写模板化检测"""
        result = _Detector.detect_templated_description(natural_text, threshold=2)
        assert result is False

    def test_safety_bias_detection(self):
        """安全化倾向检测"""
        safe_text = "我们应该考虑一下这个问题，最好还是从长计议。"
        assert _Detector.detect_safety_bias(safe_text) is True

        normal_text = "我不这么认为。走自己的路。"
        assert _Detector.detect_safety_bias(normal_text) is False


# =========================================================================
# 清除流水线测试
# =========================================================================

class _Fixer:
    """简化的修复器（测试用）"""

    @staticmethod
    def fix_sentence_rhythm(text: str) -> str:
        """简单节奏修复：将长句拆分"""
        sentences = text.split("。")
        fixed = []
        for i, sent in enumerate(sentences):
            if not sent.strip():
                fixed.append(sent)
                continue
            if len(sent) > 30 and "，" in sent:
                parts = sent.split("，")
                mid = len(parts) // 2
                short = "。".join(parts[:mid]) + "，" + "。".join(parts[mid:])
                fixed.append(short)
            else:
                fixed.append(sent)
        return "。".join(fixed)

    @staticmethod
    def replace_transition_words(text: str) -> str:
        """简单过渡词替换"""
        replacements = {
            "然而": "但",
            "因此": "所以",
            "与此同时": "这时",
            "另外": "",
            "此外": "",
            "于是": "",
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text


class _Pipeline:
    """简化的清除流水线（测试用）"""

    def __init__(self, detector: _Detector):
        self.detector = detector

    def purify(self, text: str, thresholds: dict) -> dict:
        """执行完整清除流水线"""
        issues = []

        # L1 检测
        if self.detector.detect_uniform_sentence(text):
            issues.append({"type": "sentence_rhythm_uniform", "fix_level": 1})
        if self.detector.detect_transition_overuse(text):
            issues.append({"type": "transition_word_overuse", "fix_level": 1})
        if self.detector.detect_templated_description(text):
            issues.append({"type": "description_templated", "fix_level": 1})

        # L2 检测
        if self.detector.detect_emotion_telling(text):
            issues.append({"type": "emotion_telling", "fix_level": 2})

        # L3 检测
        if self.detector.detect_safety_bias(text):
            issues.append({"type": "safety_bias", "fix_level": 3})

        # 执行 L1 自动修复
        text_after = text
        l1_count = sum(1 for i in issues if i["fix_level"] == 1)
        if l1_count > 0:
            text_after = _Fixer.fix_sentence_rhythm(text_after)
            text_after = _Fixer.replace_transition_words(text_after)

        return {
            "passed": len(issues) == l1_count,
            "original_text": text,
            "fixed_text": text_after if l1_count > 0 else text,
            "issues_found": len(issues),
            "l1_auto": l1_count,
            "l2_semi_auto": sum(1 for i in issues if i["fix_level"] == 2),
            "l3_report_only": sum(1 for i in issues if i["fix_level"] == 3),
            "issues": issues,
        }


class TestPurificationPipeline:
    """测试清除流水线的编排"""

    def test_pipeline_detects_ai_text(self, ai_generated_text):
        """流水线应检测出 AI 生成文本中的痕迹"""
        pipeline = _Pipeline(_Detector())
        result = pipeline.purify(ai_generated_text, {})
        assert result["issues_found"] > 0, "应至少检测到 1 个 AI 痕迹"

    def test_pipeline_auto_fixes_l1_issues(self, ai_generated_text):
        """L1 级别问题应自动修复"""
        pipeline = _Pipeline(_Detector())
        result = pipeline.purify(ai_generated_text, {})
        assert result["fixed_text"] != result["original_text"], "L1 自动修复应修改文本"
        assert result["l1_auto"] > 0, "应检测到 L1 级别问题"

    def test_pipeline_passes_natural_text(self, natural_text):
        """流水线应判定自然文本为通过"""
        pipeline = _Pipeline(_Detector())
        result = pipeline.purify(natural_text, {})
        assert result["passed"] is True or result["issues_found"] == 0, \
            "自然文本应通过清除检查"

    def test_pipeline_returns_report(self, ai_generated_text):
        """流水线应返回完整的清除报告"""
        pipeline = _Pipeline(_Detector())
        result = pipeline.purify(ai_generated_text, {})
        assert "issues_found" in result
        assert "l1_auto" in result
        assert "l2_semi_auto" in result
        assert "l3_report_only" in result
        assert "issues" in result


# =========================================================================
# Config 集成测试
# =========================================================================

class TestConfigIntegration:
    """测试配置系统与 AI 痕迹检测的集成"""

    def test_threshold_yaml_exists(self):
        """ai_trace_thresholds.yaml 配置文件应存在"""
        yaml_path = PROJECT_ROOT / "src" / "config" / "ai_trace_thresholds.yaml"
        assert yaml_path.exists()

    def test_purifier_default_settings(self):
        """验证默认阈值配置的一致性"""
        yaml_path = PROJECT_ROOT / "src" / "config" / "ai_trace_thresholds.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        assert data is not None
        thresholds_data = data.get("ai_trace_thresholds", {})
        detection = thresholds_data.get("detection", {})
        assert "uniform_sentence_structure" in detection
        assert detection["uniform_sentence_structure"].get("enabled") is True

    def test_foreshadow_threshold_value(self):
        """验证伏笔相似度检测阈值配置"""
        yaml_path = PROJECT_ROOT / "src" / "config" / "ai_trace_thresholds.yaml"
        with open(yaml_path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        thresholds_data = data.get("ai_trace_thresholds", {})
        detection = thresholds_data.get("detection", {})
        # ai_trace_thresholds.yaml 中不直接包含伏笔阈值
        # 但伏笔检测的余弦相似度阈值 0.85 在 step_protocols.yaml 中定义
        step_path = PROJECT_ROOT / "src" / "config" / "step_protocols.yaml"
        with open(step_path, "r", encoding="utf-8") as f:
            step_data = yaml.safe_load(f)
        foreshadow_checks = step_data["step_protocols"]["foreshadow"]["quality_checks"]
        dedup_check = [c for c in foreshadow_checks if c["check"] == "chroma_deduplicate"]
        assert len(dedup_check) > 0
        assert "0.85" in dedup_check[0]["rule"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])