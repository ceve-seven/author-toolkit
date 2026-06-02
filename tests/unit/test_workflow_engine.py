"""workflow engine 模块单元测试"""
from src.core.workflow.engine import WorkflowOrchestrator, NovelProxy


class TestStepTableMap:
    def test_step_table_map_is_class_attribute(self):
        assert hasattr(WorkflowOrchestrator, "_STEP_TABLE_MAP")
        assert isinstance(WorkflowOrchestrator._STEP_TABLE_MAP, dict)

    def test_step_table_map_covers_all_steps(self):
        step_names = [s[0] for s in WorkflowOrchestrator.STEPS]
        for name in step_names:
            assert name in WorkflowOrchestrator._STEP_TABLE_MAP, f"missing: {name}"

    def test_step_table_map_values_are_valid_tables(self):
        from src.utils import VALID_TABLES
        for step, table in WorkflowOrchestrator._STEP_TABLE_MAP.items():
            assert table in VALID_TABLES, f"step '{step}' maps to invalid table '{table}'"


class TestNovelProxy:
    def test_proxy_attributes(self):
        proxy = NovelProxy(novel_id="NOV-001", title="测试", current_step=5)
        assert proxy.id == "NOV-001"
        assert proxy.title == "测试"
        assert proxy.current_step == 5

    def test_proxy_default_step(self):
        proxy = NovelProxy(novel_id="NOV-002", title="新小说")
        assert proxy.current_step == 1


class TestStepsDefinition:
    def test_steps_count_is_20(self):
        assert len(WorkflowOrchestrator.STEPS) == 20

    def test_steps_are_tuples(self):
        for step in WorkflowOrchestrator.STEPS:
            assert isinstance(step, tuple)
            assert len(step) == 2

    def test_step_names_match_main(self):
        from main import STEP_NAMES
        engine_names = [s[0] for s in WorkflowOrchestrator.STEPS]
        assert engine_names == STEP_NAMES

    def test_step_names_match_helpers(self):
        from tests.helpers import STEP_NAMES as helper_names
        engine_names = [s[0] for s in WorkflowOrchestrator.STEPS]
        assert engine_names == helper_names
