"""registry 模块单元测试"""
from src.core.modules.base_module import BaseModule, ModuleResult
from src.core.modules.registry import ModuleRegistry


class FakeModuleA(BaseModule):
    module_name = "fake_a"
    depends_on = []

    def run(self, context, content):
        return ModuleResult(success=True, summary="A done")


class FakeModuleB(BaseModule):
    module_name = "fake_b"
    depends_on = ["fake_a"]

    def run(self, context, content):
        return ModuleResult(success=True, summary="B done")


class FakeModuleC(BaseModule):
    module_name = "fake_c"
    depends_on = ["fake_b"]

    def run(self, context, content):
        return ModuleResult(success=True, summary="C done")


class TestModuleRegistry:
    def setup_method(self):
        self.registry = ModuleRegistry.__new__(ModuleRegistry)
        self.registry._modules = {}
        self.registry._initialized = False

    def test_register_module(self):
        self.registry.register(FakeModuleA)
        assert self.registry.get("fake_a") is FakeModuleA

    def test_get_nonexistent_returns_none(self):
        assert self.registry.get("no_such") is None

    def test_list_modules(self):
        self.registry.register(FakeModuleA)
        self.registry.register(FakeModuleB)
        names = self.registry.list_modules()
        assert "fake_a" in names
        assert "fake_b" in names

    def test_get_dependencies(self):
        self.registry.register(FakeModuleB)
        deps = self.registry.get_dependencies("fake_b")
        assert deps == ["fake_a"]

    def test_get_dependencies_nonexistent(self):
        deps = self.registry.get_dependencies("no_such")
        assert deps == []

    def test_get_sorted_modules_dfs(self):
        self.registry.register(FakeModuleC)
        self.registry.register(FakeModuleA)
        self.registry.register(FakeModuleB)
        sorted_modules = self.registry.get_sorted_modules()
        names = [m.module_name for m in sorted_modules]
        assert names.index("fake_a") < names.index("fake_b")
        assert names.index("fake_b") < names.index("fake_c")

    def test_get_execution_order(self):
        self.registry.register(FakeModuleC)
        self.registry.register(FakeModuleA)
        self.registry.register(FakeModuleB)
        order = self.registry.get_execution_order()
        assert order.index("fake_a") < order.index("fake_b")
        assert order.index("fake_b") < order.index("fake_c")

    def test_register_without_module_name_uses_class_name(self):
        class NoName(BaseModule):
            depends_on = []
            def run(self, context, content):
                return ModuleResult()
        self.registry.register(NoName)
        assert self.registry.get("NoName") is NoName


class TestBaseModule:
    def test_run_raises_not_implemented(self):
        mod = BaseModule()
        try:
            mod.run({}, None)
            assert False, "should raise"
        except NotImplementedError:
            pass

    def test_module_result_defaults(self):
        r = ModuleResult()
        assert r.success is True
        assert r.summary == ""
        assert r.data == {}
        assert r.word_count == 0
        assert r.errors == []

    def test_validate_returns_empty_list(self):
        mod = BaseModule()
        mod.module_name = ""
        r = ModuleResult()
        result = mod.validate(r)
        assert result == []
