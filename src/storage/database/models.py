from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class NovelStatus(enum.Enum):
    创作中 = "创作中"
    已完成 = "已完成"
    已暂停 = "已暂停"


class StepStatusEnum(enum.Enum):
    待执行 = "待执行"
    执行中 = "执行中"
    已完成 = "已完成"
    已跳过 = "已跳过"
    失败 = "失败"


class ReviewLevelEnum(enum.Enum):
    通过 = "通过"
    警告 = "警告"
    失败 = "失败"
    需人工审核 = "需人工审核"


class FixStatusEnum(enum.Enum):
    待修复 = "待修复"
    已修复 = "已修复"
    修复失败 = "修复失败"
    已忽略 = "已忽略"


class Novel(Base):
    __tablename__ = "novels"

    id = Column(String(32), primary_key=True)
    title = Column(String(255), nullable=False)
    author = Column(String(128), nullable=True)
    current_step = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="创作中")
    created_at = Column(String(32), nullable=True)
    updated_at = Column(String(32), nullable=True)


class Inspiration(Base):
    __tablename__ = "inspirations"

    novel_id = Column(String(32), primary_key=True)
    direction_id = Column(String(32), primary_key=True)
    title = Column(String(255), nullable=True)
    concept = Column(Text, nullable=True)
    innovation_score = Column(Float, nullable=True)
    summary = Column(Text, nullable=True)
    emotional_potential = Column(Float, nullable=True)
    created_at = Column(String(32), nullable=True)


class Theme(Base):
    __tablename__ = "themes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    surface_theme = Column(Text, nullable=True)
    deep_theme = Column(Text, nullable=True)
    emotional_hook = Column(Text, nullable=True)
    theme_statement = Column(Text, nullable=True)
    reverse_confirmation = Column(Text, nullable=True)


class Outline(Base):
    __tablename__ = "outlines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    acts = Column(Text, nullable=True)
    causal_chain = Column(Text, nullable=True)
    rhythm_map = Column(Text, nullable=True)


class WorldBuilding(Base):
    __tablename__ = "world_building"

    novel_id = Column(String(32), primary_key=True)
    dimension_name = Column(String(64), primary_key=True)
    rules = Column(Text, nullable=True)


class WorldRule(Base):
    __tablename__ = "world_rules"

    novel_id = Column(String(32), primary_key=True)
    rule_id = Column(String(32), primary_key=True)
    dimension = Column(String(64), nullable=True)
    description = Column(Text, nullable=True)
    scope = Column(String(255), nullable=True)
    constraints = Column(Text, nullable=True)


class Character(Base):
    __tablename__ = "characters"

    novel_id = Column(String(32), primary_key=True)
    char_id = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    role = Column(String(32), nullable=True)
    layer1_json = Column(Text, nullable=True)
    layer2_json = Column(Text, nullable=True)
    layer3_json = Column(Text, nullable=True)
    layer4_json = Column(Text, nullable=True)
    weight_tier = Column(String(8), nullable=True)
    weight_score = Column(Float, nullable=True)
    weight_json = Column(Text, nullable=True)


class CharacterArc(Base):
    __tablename__ = "character_arcs"

    novel_id = Column(String(32), primary_key=True)
    char_id = Column(String(32), primary_key=True)
    arc_type = Column(String(32), primary_key=True)
    start_state = Column(Text, nullable=True)
    catalyst_event = Column(Text, nullable=True)
    change_process = Column(Text, nullable=True)
    end_state = Column(Text, nullable=True)
    chapter_mapping = Column(Text, nullable=True)


class Relation(Base):
    __tablename__ = "relations"

    novel_id = Column(String(32), primary_key=True)
    relation_id = Column(String(32), primary_key=True)
    char_a_id = Column(String(32), nullable=False)
    char_b_id = Column(String(32), nullable=False)
    type = Column(String(32), nullable=True)
    strength = Column(Float, nullable=False, default=0.5)
    asymmetry = Column(Float, nullable=False, default=0.0)
    history = Column(Text, nullable=True)
    trajectory = Column(Text, nullable=True)


class Faction(Base):
    __tablename__ = "factions"

    novel_id = Column(String(32), primary_key=True)
    faction_id = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=True)
    hierarchy = Column(Text, nullable=True)
    goals = Column(Text, nullable=True)
    resources = Column(Text, nullable=True)
    doctrines = Column(Text, nullable=True)
    reputation = Column(Float, nullable=True)


class FactionMember(Base):
    __tablename__ = "faction_members"

    novel_id = Column(String(32), primary_key=True)
    faction_id = Column(String(32), primary_key=True)
    char_id = Column(String(32), primary_key=True)
    role = Column(String(64), nullable=True)
    rank = Column(String(64), nullable=True)


class FactionRelation(Base):
    __tablename__ = "faction_relations"

    novel_id = Column(String(32), primary_key=True)
    relation_id = Column(String(32), primary_key=True)
    faction_a_id = Column(String(32), nullable=False)
    faction_b_id = Column(String(32), nullable=False)
    type = Column(String(32), nullable=True)
    strength = Column(Float, nullable=False, default=0.5)
    history = Column(Text, nullable=True)
    treaties = Column(Text, nullable=True)
    hidden_agenda = Column(Text, nullable=True)


class CharFactionLink(Base):
    __tablename__ = "char_faction_links"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    char_id = Column(String(32), nullable=False)
    faction_id = Column(String(32), nullable=False)
    membership_type = Column(String(32), nullable=True)
    join_chapter = Column(Integer, nullable=True)
    leave_chapter = Column(Integer, nullable=True)
    role_in_faction = Column(String(64), nullable=True)
    loyalty = Column(Float, nullable=True)
    notes = Column(Text, nullable=True)


class Item(Base):
    __tablename__ = "items"

    novel_id = Column(String(32), primary_key=True)
    item_id = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    type = Column(String(32), nullable=True)
    purpose = Column(Text, nullable=True)
    background_story = Column(Text, nullable=True)
    restrictions = Column(Text, nullable=True)
    current_owner = Column(String(32), nullable=True)
    significance_to_plot = Column(Text, nullable=True)
    first_appearance_chapter = Column(Integer, nullable=True)


class Foreshadow(Base):
    __tablename__ = "foreshadows"

    novel_id = Column(String(32), primary_key=True)
    foreshadow_id = Column(String(32), primary_key=True)
    type = Column(String(32), nullable=True)
    status = Column(String(32), nullable=True)
    plant_chapter = Column(Integer, nullable=True)
    plant_location = Column(String(255), nullable=True)
    plant_form = Column(Text, nullable=True)
    reveal_chapter_planned = Column(Integer, nullable=True)
    reveal_chapter_actual = Column(Integer, nullable=True)
    reveal_form = Column(Text, nullable=True)
    payload = Column(Text, nullable=True)
    surface = Column(Text, nullable=True)
    depth = Column(Text, nullable=True)
    related_char = Column(Text, nullable=True)
    related_item = Column(Text, nullable=True)
    related_plot = Column(Text, nullable=True)
    parent_fore = Column(String(32), nullable=True)
    child_fores = Column(Text, nullable=True)
    tags = Column(Text, nullable=True)
    importance = Column(Float, nullable=True, default=0.5)
    chroma_id = Column(String(64), nullable=True)
    created_at = Column(String(32), nullable=True)
    last_modified = Column(String(32), nullable=True)


class ForeshadowDensitySnapshot(Base):
    __tablename__ = "foreshadow_density_snapshots"

    novel_id = Column(String(32), primary_key=True)
    chapter = Column(Integer, primary_key=True)
    active_count = Column(Integer, nullable=True)
    density_per_kword = Column(Float, nullable=True)
    new_count = Column(Integer, nullable=True)
    resolved_count = Column(Integer, nullable=True)


class Volume(Base):
    __tablename__ = "volumes"

    novel_id = Column(String(32), primary_key=True)
    volume_id = Column(String(32), primary_key=True)
    name = Column(String(128), nullable=False)
    chapter_range = Column(String(64), nullable=True)
    boundary_gravity = Column(Text, nullable=True)
    pacing = Column(String(255), nullable=True)
    major_conflict = Column(Text, nullable=True)
    character_focus = Column(Text, nullable=True)
    themes = Column(Text, nullable=True)
    cliffhanger = Column(Text, nullable=True)
    volume_rhythm_curve = Column(Text, nullable=True)
    volume_rhythm_evaluation = Column(Text, nullable=True)


class VolumeChapter(Base):
    __tablename__ = "volume_chapters"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    volume_id = Column(String(32), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    pov_character = Column(String(128), nullable=True)
    summary = Column(Text, nullable=True)
    word_count_budget = Column(Integer, nullable=True)


class DetailOutline(Base):
    __tablename__ = "detail_outlines"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    chapter_constraint_summary = Column(Text, nullable=True)
    scenes = Column(Text, nullable=True)


class Archive(Base):
    __tablename__ = "archives"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    layer1_identity_card = Column(Text, nullable=True)
    layer2_core_summary = Column(Text, nullable=True)
    layer3_module_snapshots = Column(Text, nullable=True)
    updated_at = Column(String(32), nullable=True)


class ChangeLog(Base):
    __tablename__ = "change_log"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    timestamp = Column(String(32), nullable=True)
    step = Column(String(32), nullable=True)
    module = Column(String(64), nullable=True)
    action = Column(String(64), nullable=False)
    entity_id = Column(String(32), nullable=True)
    entity_type = Column(String(64), nullable=True)
    summary = Column(String(255), nullable=True)
    changed_fields = Column(Text, nullable=True)


class Synopsis(Base):
    __tablename__ = "synopses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    one_liner = Column(Text, nullable=True)
    short_blurb = Column(Text, nullable=True)
    standard_blurb = Column(Text, nullable=True)
    long_blurb = Column(Text, nullable=True)
    core_conflict = Column(Text, nullable=True)
    world_highlight = Column(Text, nullable=True)
    selling_points = Column(Text, nullable=True)
    target_audience = Column(Text, nullable=True)
    tone_tags = Column(Text, nullable=True)
    comparison_titles = Column(Text, nullable=True)
    hook_question = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    last_synced_at = Column(String(32), nullable=True)
    stale_status = Column(String(32), nullable=True)


class Manuscript(Base):
    __tablename__ = "manuscripts"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    chapter_number = Column(Integer, nullable=False)
    title = Column(String(255), nullable=True)
    compiled_constraint_file = Column(Text, nullable=True)
    scenes = Column(Text, nullable=True)
    word_count = Column(Integer, nullable=True)
    transition_fixes = Column(Text, nullable=True)
    status = Column(String(32), nullable=True)


class FixLog(Base):
    __tablename__ = "fix_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    chapter_number = Column(Integer, nullable=True)
    fix_type = Column(String(64), nullable=False)
    issue_ref = Column(String(255), nullable=True)
    original_summary = Column(Text, nullable=True)
    fixed_summary = Column(Text, nullable=True)
    timestamp = Column(String(32), nullable=True)


class ReviewResult(Base):
    __tablename__ = "review_results"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    step_number = Column(Integer, nullable=False)
    module_name = Column(String(64), nullable=False)
    level = Column(String(32), nullable=False)
    score = Column(Float, nullable=True)
    details = Column(Text, nullable=True)
    suggestions = Column(Text, nullable=True)
    created_at = Column(String(32), nullable=True)


class StepData(Base):
    __tablename__ = "step_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    step_number = Column(Integer, nullable=False)
    module_name = Column(String(64), nullable=False)
    status = Column(String(32), nullable=False)
    data = Column(Text, nullable=True)
    created_at = Column(String(32), nullable=True)


class StepStatus(Base):
    __tablename__ = "step_status"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    step_number = Column(Integer, nullable=False)
    step_name = Column(String(64), nullable=True)
    status = Column(String(32), nullable=True)


class IdCounter(Base):
    __tablename__ = "id_counters"

    novel_id = Column(String(32), primary_key=True)
    prefix = Column(String(16), primary_key=True)
    current_value = Column(Integer, nullable=False, default=0)


class PurificationLog(Base):
    __tablename__ = "purification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    novel_id = Column(String(32), nullable=False)
    processed_at = Column(String(32), nullable=True)
    text_length = Column(Integer, nullable=True)
    issues_found = Column(Integer, nullable=True)
    auto_fixed = Column(Integer, nullable=True)
    report = Column(Text, nullable=True)
