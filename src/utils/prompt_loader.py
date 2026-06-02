from __future__ import annotations

import os
from typing import Dict, Optional

_PROMPT_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "ai", "prompts")

_cache: Dict[str, str] = {}


def load_prompt(filename: str) -> Optional[str]:
    if filename in _cache:
        return _cache[filename]

    filepath = os.path.join(_PROMPT_DIR, filename)
    if not os.path.exists(filepath):
        return None

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    _cache[filename] = content
    return content


def get_prompt_filename(module_name: str) -> str:
    mapping = {
        "inspiration": "inspiration.md",
        "theme_engine": "theme.md",
        "outline_builder": "outline.md",
        "world_builder": "world_building.md",
        "character_builder": "character.md",
        "arc_builder": "arc.md",
        "faction_builder": "faction.md",
        "faction_relation": "faction.md",
        "item_builder": None,
        "foreshadow_manager": "foreshadow.md",
        "synopsis_builder": "synopsis.md",
        "volume_config": None,
        "detail_outline": "detail_outline.md",
        "manuscript_writer": "manuscript_writer.md",
        "review_executor": None,
        "manuscript_fixer": None,
        "export_tool": None,
        "archive_builder": None,
        "relation_builder": None,
    }
    filename = mapping.get(module_name)
    if filename:
        return filename
    return f"{module_name}.md"


def load_module_prompt(module_name: str) -> Optional[str]:
    filename = get_prompt_filename(module_name)
    if filename:
        return load_prompt(filename)
    return None


def get_loaded_prompts() -> Dict[str, str]:
    return dict(_cache)