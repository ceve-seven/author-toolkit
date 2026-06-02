from __future__ import annotations

from typing import Any, Dict, List, Optional

import structlog

TABLE_MAP: Dict[str, str] = {
    "灵感启动": "themes",
    "小说主题": "themes",
    "拟定大纲": "outlines",
    "世界观设定": "world_building",
    "人物设定": "characters",
    "人物关系": "relations",
    "角色弧线": "character_arcs",
    "势力设定": "factions",
    "势力关系": "faction_relations",
    "人物-势力关联": "char_faction_links",
    "物品库": "items",
    "伏笔追踪": "foreshadows",
    "小说档案": "archives",
    "小说简介": "synopses",
    "分卷配置": "volumes",
    "章节细纲": "detail_outlines",
    "正文初稿": "manuscripts",
    "正文审核": "review_results",
    "正文修正": "manuscripts",
    "导出发布": "novels",
}


class PipelineStage:
    """单个环节的编排数据加载器"""

    def __init__(self, step_number: int, step_name: str, module_path: str):
        self.step_number = step_number
        self.step_name = step_name
        self.module_path = module_path
        self.dependencies: List[str] = []

    def get_dependency_data(
        self, novel_id: str, db_session: Any
    ) -> Dict[str, Any]:
        """加载本环节所需的所有依赖数据"""
        data: Dict[str, Any] = {}
        for dep_name in self.dependencies:
            dep_data = self._query_dep_data(novel_id, dep_name, db_session)
            if dep_data:
                data[dep_name] = dep_data
        return data

    def _query_dep_data(
        self, novel_id: str, dep_name: str, db_session: Any
    ) -> Optional[List[Dict[str, Any]]]:
        """查询单个依赖模块的数据"""
        table = TABLE_MAP.get(dep_name)
        if not table:
            return None
        try:
            rows = db_session.execute(
                f"SELECT * FROM {table} WHERE novel_id = ?",
                (novel_id,),
            ).fetchall()
            if rows:
                columns = [desc[0] for desc in db_session.description]
                return [dict(zip(columns, row)) for row in rows]
            return None
        except Exception:
            return None


class PipelineOrchestrator:
    """环节编排器——管理所有环节的依赖数据加载和状态追踪"""

    STEPS: List[tuple] = [
        (1,  "灵感启动",   "modules.theme_engine.ThemeEngine"),
        (2,  "小说主题",   "modules.theme_engine.ThemeEngine"),
        (3,  "世界观设定", "modules.world_builder.WorldBuilder"),
        (4,  "人物设定",   "modules.character_builder.CharacterBuilder"),
        (5,  "势力设定",   "modules.faction_builder.FactionBuilder"),
        (6,  "物品库",     "modules.item_builder.ItemBuilder"),
        (7,  "人物关系",   "modules.relation_builder.RelationBuilder"),
        (8,  "势力关系",   "modules.faction_relation.FactionRelationBuilder"),
        (9,  "人物-势力关联", "modules.char_faction_bridge.CharFactionBridge"),
        (10, "角色弧线",   "modules.arc_builder.ArcBuilder"),
        (11, "伏笔追踪",   "modules.foreshadow_manager.ForeshadowManager"),
        (12, "拟定大纲",   "modules.outline_builder.OutlineBuilder"),
        (13, "分卷配置",   "modules.volume_config.VolumeConfig"),
        (14, "章节细纲",   "modules.detail_outline.DetailOutlineBuilder"),
        (15, "小说档案",   "modules.archive_builder.ArchiveBuilder"),
        (16, "小说简介",   "modules.synopsis_builder.SynopsisBuilder"),
        (17, "正文初稿",   "modules.manuscript_writer.ManuscriptWriter"),
        (18, "正文审核",   "quality.review_executor.ReviewExecutor"),
        (19, "正文修正",   "modules.manuscript_writer.ManuscriptFixer"),
        (20, "导出发布",   "modules.export_tool.ExportTool"),
    ]

    DEPENDENCY_MAP: Dict[str, List[str]] = {
        "灵感启动": [],
        "小说主题": ["灵感启动"],
        "世界观设定": ["小说主题"],
        "人物设定": ["世界观设定"],
        "势力设定": ["世界观设定"],
        "物品库": ["世界观设定"],
        "人物关系": ["人物设定"],
        "势力关系": ["势力设定"],
        "人物-势力关联": ["人物设定", "势力设定", "人物关系", "势力关系"],
        "角色弧线": ["人物设定", "人物关系", "人物-势力关联"],
        "伏笔追踪": ["人物设定", "势力设定", "物品库"],
        "拟定大纲": ["灵感启动", "小说主题", "世界观设定", "人物设定", "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线", "伏笔追踪"],
        "分卷配置": ["拟定大纲"],
        "章节细纲": ["分卷配置", "世界观设定", "人物设定", "物品库", "伏笔追踪"],
        "小说档案": ["灵感启动", "小说主题", "世界观设定", "人物设定", "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线", "伏笔追踪", "拟定大纲", "分卷配置", "章节细纲"],
        "小说简介": ["小说档案"],
        "正文初稿": ["章节细纲", "世界观设定", "人物设定", "物品库", "伏笔追踪"],
        "正文审核": ["正文初稿"],
        "正文修正": ["正文审核"],
        "导出发布": ["正文修正"],
    }

    def __init__(self, db_session: Any):
        self.db = db_session
        self.logger = structlog.get_logger("pipeline")
        self._stages: Dict[str, PipelineStage] = {}
        self._init_stages()

    def _init_stages(self):
        """初始化所有环节的编排器"""
        for step_number, step_name, module_path in self.STEPS:
            stage = PipelineStage(step_number, step_name, module_path)
            stage.dependencies = self.DEPENDENCY_MAP.get(step_name, [])
            self._stages[step_name] = stage

    def get_stage(self, step_name: str) -> Optional[PipelineStage]:
        """获取指定环节的编排器"""
        return self._stages.get(step_name)

    def get_stage_by_number(self, step_number: int) -> Optional[PipelineStage]:
        """按序号获取环节"""
        for stage in self._stages.values():
            if stage.step_number == step_number:
                return stage
        return None

    def get_all_dependency_data(
        self, novel_id: str, step_name: str
    ) -> Dict[str, Any]:
        """获取指定环节的完整依赖数据"""
        stage = self.get_stage(step_name)
        if not stage:
            return {}
        return stage.get_dependency_data(novel_id, self.db)

    def get_prerequisites_status(
        self, novel_id: str, step_name: str
    ) -> Dict[str, bool]:
        """检查所有前置依赖的就绪状态"""
        stage = self.get_stage(step_name)
        if not stage:
            return {}
        status: Dict[str, bool] = {}
        for dep in stage.dependencies:
            status[dep] = self._has_data(novel_id, dep)
        return status

    def _has_data(self, novel_id: str, dep_name: str) -> bool:
        """检查依赖模块是否有数据"""
        table = TABLE_MAP.get(dep_name)
        if not table:
            return False
        try:
            row = self.db.execute(
                f"SELECT COUNT(1) FROM {table} WHERE novel_id = ?",
                (novel_id,),
            ).fetchone()
            return row is not None and row[0] > 0
        except Exception:
            return False

    def get_step_name(self, step_number: int) -> Optional[str]:
        """根据序号获取环节名称"""
        for s_num, s_name, _ in self.STEPS:
            if s_num == step_number:
                return s_name
        return None

    def iter_steps(self, start: int = 1) -> List[tuple]:
        """获取从指定序号开始的环节列表"""
        return [s for s in self.STEPS if s[0] >= start]

    def get_total_steps(self) -> int:
        return len(self.STEPS)