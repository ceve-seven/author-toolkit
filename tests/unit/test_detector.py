"""detector 模块单元测试"""
from src.core.purifier.detector import AITraceDetector, TraceIssue


class TestAITraceDetector:
    def setup_method(self):
        self.detector = AITraceDetector()

    def test_detect_clean_text_no_issues(self):
        text = "短句。中等长度的句子在这里。这是一个稍微长一些的句子，包含更多信息。"
        issues = self.detector.detect(text)
        assert isinstance(issues, list)

    def test_sentence_rhythm_uniform(self):
        uniform = "。".join(["这是一段长度完全一样的文字"] * 20) + "。"
        issues = self.detector._check_sentence_rhythm(uniform)
        assert any(i.trait_type == "sentence_rhythm_uniform" for i in issues)

    def test_sentence_rhythm_varied_ok(self):
        varied = "短。中等长度句子。这是一个非常非常非常长的句子，包含很多很多内容，用来增加方差。短。"
        issues = self.detector._check_sentence_rhythm(varied)
        assert not any(i.trait_type == "sentence_rhythm_uniform" for i in issues)

    def test_transition_word_overuse(self):
        text = "然而然而然而然而然而然而然而然而然而然而然而然而然而然而然而然而" + "字" * 500
        issues = self.detector._check_transition_words(text)
        assert any(i.trait_type == "transition_word_overuse" for i in issues)

    def test_emotion_telling(self):
        text = "他感到很开心。她觉得很难过。心中充满愤怒。内心十分纠结。感受到温暖。体会到痛苦。"
        issues = self.detector._check_emotion_telling(text)
        assert any(i.trait_type == "emotion_telling" for i in issues)

    def test_description_templates(self):
        text = "阳光透过窗户。微风拂过脸庞。空气中弥漫花香。映入眼帘的是一片花海。"
        issues = self.detector._check_description_templates(text)
        assert any(i.trait_type == "description_templated" for i in issues)

    def test_safety_bias(self):
        text = "我们应该小心。最好还是谨慎。不太合适这样做。考虑到安全。从某种角度来说需要注意。"
        issues = self.detector._check_safety_bias(text)
        assert any(i.trait_type == "safety_bias" for i in issues)

    def test_negation_pattern(self):
        text = ""
        for i in range(12):
            text += f"不是第{ i }个问题，是第{ i }个答案。"
        issues = self.detector._check_negation_pattern(text)
        assert any(i.trait_type == "negation_pattern" for i in issues)

    def test_simile_overuse(self):
        text = ""
        for i in range(6):
            text += f"像一片飘落的叶子一样，他静静地站着。仿佛一阵风一般，她转身离去。如同流水一样，时间流逝。"
        issues = self.detector._check_simile_overuse(text)
        assert any(i.trait_type == "simile_overuse" for i in issues)

    def test_sentence_start_repetition(self):
        sentences = []
        for _ in range(20):
            sentences.append("他走了过来。")
            sentences.append("她看了一眼。")
            sentences.append("它停了下来。")
        text = "".join(sentences)
        issues = self.detector._check_sentence_start_repetition(text)
        assert any(i.trait_type == "sentence_start_repetition" for i in issues)

    def test_negative_parallelism(self):
        text = "不是这样的。不是那样的。不是别的什么。是正确的方向。"
        issues = self.detector._check_negative_parallelism(text)
        assert any(i.trait_type == "negative_parallelism" for i in issues)

    def test_discourse_marker_overuse(self):
        text = ("首先，我们需要注意。其次，这个很重要。再次，不可忽视。"
                "最后，总结一下。总之，需要关注。综上所述，结论明确。"
                "值得注意的是，这一点。需要指出的是，那个问题。" + "字" * 2000)
        issues = self.detector._check_discourse_marker_overuse(text)
        assert any(i.trait_type == "discourse_marker_overuse" for i in issues)

    def test_hedge_language(self):
        text = ("似乎有什么不对。或许是这样吧。也许可能大概是这样。"
                "不禁感叹。不由得叹息。某种程度上的理解。"
                "仿佛梦境一般。一种说不出的感觉。莫名地感到不安。" + "字" * 2000)
        issues = self.detector._check_hedge_language(text)
        assert any(i.trait_type == "hedge_language" for i in issues)

    def test_action_beat_repetition(self):
        text = ("微微一笑，他开口了。点了点头，她表示同意。摇了摇头，他拒绝了。"
                "陷入沉思，他沉默良久。深吸一口气，她站了起来。")
        issues = self.detector._check_action_beat_repetition(text)
        assert any(i.trait_type == "action_beat_repetition" for i in issues)

    def test_reaction_template(self):
        text = "心头一紧，他意识到危险。一股暖流涌上心头。眼中闪过一丝惊讶。"
        issues = self.detector._check_reaction_template(text)
        assert any(i.trait_type == "reaction_template" for i in issues)

    def test_punctuation_ai_pattern(self):
        text = "他说——这是——重要的——决定——。她沉默……然后……终于……开口……。真的吗！！不会吧？？"
        issues = self.detector._check_punctuation_ai_pattern(text)
        assert any(i.trait_type == "punctuation_ai_pattern" for i in issues)

    def test_trace_issue_dataclass(self):
        issue = TraceIssue(
            trait_type="test_type",
            severity="warning",
            fix_level=2,
            detail="test detail",
            position=10,
            suggestion="fix it",
        )
        assert issue.trait_type == "test_type"
        assert issue.severity == "warning"
        assert issue.fix_level == 2
        assert issue.position == 10

    def test_update_thresholds(self):
        self.detector.update_thresholds({"sentence_fluctuation": 0.9})
        assert self.detector.thresholds["sentence_fluctuation"] == 0.9

    def test_describe_issues_empty(self):
        result = self.detector.describe_issues([])
        assert "未检测到" in result

    def test_describe_issues_with_data(self):
        issues = [TraceIssue(
            trait_type="test",
            severity="warning",
            fix_level=1,
            detail="something",
            suggestion="fix",
        )]
        result = self.detector.describe_issues(issues)
        assert "WARNING" in result
        assert "test" in result

    def test_detect_returns_list(self):
        text = "普通文本内容，没有什么特别的问题。"
        result = self.detector.detect(text)
        assert isinstance(result, list)
