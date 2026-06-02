from dataclasses import dataclass, field
from typing import Any, Optional

from src.utils.prompt_loader import load_module_prompt


@dataclass
class ModuleResult:
    success: bool = True
    summary: str = ""
    data: dict = field(default_factory=dict)
    word_count: int = 0
    errors: list = field(default_factory=list)


class BaseModule:
    module_name: str = ""
    depends_on: list[str] = []
    _prompt_rules: Optional[str] = None

    def load_prompt_rules(self) -> Optional[str]:
        if self._prompt_rules is None:
            self._prompt_rules = load_module_prompt(self.module_name)
        return self._prompt_rules

    def get_prompt_rules_summary(self) -> str:
        rules = self.load_prompt_rules()
        if not rules:
            return ""
        lines = rules.strip().split("\n")
        headings = [l.strip("# ") for l in lines if l.startswith("##")]
        return "; ".join(headings) if headings else ""

    def run(self, context: dict, content: Any) -> ModuleResult:
        raise NotImplementedError

    def validate(self, result: ModuleResult) -> list[str]:
        prompt_rules = self.load_prompt_rules()
        if prompt_rules:
            result.data["_loaded_prompt"] = self.module_name
        return []