import importlib
import inspect
import pkgutil
from typing import Any, Type

from src.core.modules.base_module import BaseModule


class ModuleRegistry:
    _instance = None
    _modules: dict[str, Type[BaseModule]] = {}
    _initialized = False

    def __new__(cls) -> "ModuleRegistry":
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def register(self, module_class: Type[BaseModule]) -> None:
        name = module_class.module_name
        if not name:
            name = module_class.__name__
        self._modules[name] = module_class

    def get(self, module_name: str) -> Type[BaseModule] | None:
        return self._modules.get(module_name)

    def get_dependencies(self, module_name: str) -> list[str]:
        cls = self.get(module_name)
        if cls is None:
            return []
        return list(cls.depends_on)

    def list_modules(self) -> list[str]:
        return list(self._modules.keys())

    def _scan_package(self, package_name: str = "src.core.modules") -> None:
        package = importlib.import_module(package_name)
        for _, module_name, is_pkg in pkgutil.walk_packages(
            package.__path__, package.__name__ + ".",
        ):
            if is_pkg or module_name.endswith("base_module") or module_name.endswith("registry"):
                continue
            try:
                module = importlib.import_module(module_name)
                for _, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        issubclass(obj, BaseModule)
                        and obj is not BaseModule
                        and hasattr(obj, "module_name")
                        and obj.module_name
                    ):
                        self.register(obj)
            except Exception:
                pass

    def initialize(self) -> None:
        if self._initialized:
            return
        self._scan_package("src.core.modules")
        self._scan_package("src.core.quality")
        self._initialized = True

    def get_sorted_modules(self) -> list[Type[BaseModule]]:
        self.initialize()
        sorted_list: list[Type[BaseModule]] = []
        visited: set[str] = set()

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            for dep in self.get_dependencies(name):
                visit(dep)
            cls = self.get(name)
            if cls is not None and cls not in sorted_list:
                sorted_list.append(cls)

        for name in self._modules:
            visit(name)

        return sorted_list

    def get_execution_order(self) -> list[str]:
        return [cls.module_name for cls in self.get_sorted_modules()]


_registry = ModuleRegistry()


def get_registry() -> ModuleRegistry:
    return _registry