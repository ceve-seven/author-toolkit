from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional


class JsonToMdRenderer:
    """JSON 数据 → 中文 Markdown 渲染器

    将系统 JSON 格式数据渲染为作者可读的纯 Markdown。
    支持渲染人物档案、世界观、势力、伏笔等各模块。
    """

    def render(self, module_name: str, data: Dict[str, Any], novel: Any) -> str:
        """将 JSON 数据渲染为 Markdown

        Args:
            module_name: 模块名称
            data: 模块的 JSON 数据
            novel: 小说对象

        Returns:
            纯 Markdown 文本
        """
        title = novel.title if hasattr(novel, "title") else str(novel)
        render_methods = {
            "01_主题": self._render_theme,
            "02_世界观": self._render_world,
            "03_势力": self._render_factions,
            "04_势力关系": self._render_faction_relations,
            "05_人物": self._render_characters,
            "06_人物关系": self._render_relations,
            "07_角色弧线": self._render_arcs,
            "08_物品仓库": self._render_items,
            "09_伏笔管理": self._render_foreshadows,
            "10_大纲": self._render_outline,
            "11_分卷": self._render_volumes,
            "12_细纲": self._render_detail_outline,
            "13_正文": self._render_manuscript,
            "小说概览": self._render_overview,
        }

        renderer = render_methods.get(module_name, self._render_generic)
        return renderer(module_name, data, title)

    @staticmethod
    def _ensure_list(val: Any) -> list:
        """统一将字段值转为列表，支持 str / list / JSON 数组字符串"""
        if isinstance(val, list):
            return val
        if isinstance(val, str):
            import json
            try:
                parsed = json.loads(val)
                if isinstance(parsed, list):
                    return parsed
            except (json.JSONDecodeError, TypeError):
                pass
            return [val]
        if not val:
            return []
        return [str(val)]

    def _render_theme(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染主题模块——完整文档风格，与参考文档对齐"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 小说主题",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无主题数据*")
        else:
            if isinstance(records, dict):
                records = [records]
            for rec in records:
                theme_statement = rec.get('theme_statement', '')
                reverse_confirmation = rec.get('reverse_confirmation', '')
                surface_theme = rec.get('surface_theme', '')
                deep_theme = rec.get('deep_theme', '')
                emotional_hook = rec.get('emotional_hook', '')

                lines.extend([
                    f"### **核心主题**",
                    f"",
                    f"**\"{theme_statement}\"**",
                    f"",
                ])

                if reverse_confirmation:
                    lines.extend([
                        f"### **副主题（BE驱动）**",
                        f"",
                        f"**\"{reverse_confirmation}\"**",
                        f"",
                    ])

                lines.extend([
                    f"### **三层主题结构**",
                    f"",
                ])

                if surface_theme:
                    lines.extend([
                        f"**表层主题（读者第一眼看到的）：**",
                        f"{surface_theme}",
                        f"",
                    ])

                if deep_theme:
                    deep_parts = deep_theme.split("什么是", 1)
                    if len(deep_parts) == 2:
                        middle = deep_parts[0].strip()
                        deep = "什么是" + deep_parts[1]

                        footnote_parts = deep.split("但这个命题", 1)
                        if len(footnote_parts) == 2:
                            deep_main = footnote_parts[0].strip()
                            deep_footnote = "但这个命题" + footnote_parts[1]
                        else:
                            deep_main = deep
                            deep_footnote = ""

                        lines.extend([
                            f"**中层主题（读进去后感受到的）：**",
                            f"{middle}",
                            f"",
                            f"**深层主题（读完之后回味的）：**",
                            f"{deep_main}",
                        ])
                        if deep_footnote:
                            lines.extend([
                                f"**但这个命题附带了一个残酷的注脚：** {deep_footnote[len('但这个命题'):].lstrip('附带了一个残酷的注脚：').strip()}",
                                f"",
                            ])
                        else:
                            lines.append("")
                    else:
                        footnote_parts = deep_theme.split("但这个命题", 1)
                        if len(footnote_parts) == 2:
                            deep_main = footnote_parts[0].strip()
                            deep_footnote = "但这个命题" + footnote_parts[1]
                            lines.extend([
                                f"**深层主题：**",
                                f"{deep_main}",
                                f"**但这个命题附带了一个残酷的注脚：** {deep_footnote[len('但这个命题'):].lstrip('附带了一个残酷的注脚：').strip()}",
                                f"",
                            ])
                        else:
                            lines.extend([
                                f"**深层主题：**",
                                f"{deep_theme}",
                                f"",
                            ])

                if emotional_hook:
                    lines.extend([
                        f"### **情感锚点**",
                        f"",
                    ])
                    import re
                    hooks_text = emotional_hook.replace("→", "→").replace("；", "\n").replace(";", "\n")
                    for hook_line in hooks_text.split("\n"):
                        hook_line = hook_line.strip()
                        if not hook_line:
                            continue
                        hook_line = hook_line.lstrip("- ").strip()
                        match = re.match(r'^(.+?)[：:](.*)$', hook_line)
                        if match:
                            transition = match.group(1).strip()
                            description = match.group(2).strip()
                            lines.append(f"- **{transition}**：{description}")
                        else:
                            lines.append(f"- {hook_line}")
                    lines.append("")
        return "\n".join(lines)

    def _render_world(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染世界观模块——叙事化分组格式"""
        import json as _json
        from collections import OrderedDict

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 世界观设定",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无世界观数据*")
            return "\n".join(lines)

        first_rec = records[0]

        if "rules" not in first_rec or not isinstance(first_rec.get("rules"), list):
            first_rec = None

        if first_rec is not None:
            for dim in records:
                dim_name = dim.get("name", "规则")
                rules = dim.get("rules", [])
                lines.extend([f"## {dim_name}", f""])
                for rule in rules:
                    desc = rule.get('description', '')
                    scope = rule.get('scope', '')
                    constraints = rule.get('constraints', '')
                    lines.append(f"- **{rule.get('id', '')}** — {desc}")
                    if scope:
                        lines.append(f"  - 范围：{scope}")
                    if constraints:
                        lines.append(f"  - 约束：{constraints}")
                    lines.append("")
        else:
            dimension_order = [
                "时间线", "时间历史",
                "地理格局", "地理空间",
                "菌丝生物学", "菌丝七亚种", "物理规则",
                "社会结构", "法律与治理", "经济体系", "文化习俗",
                "科技退步", "科技水平",
                "魔法/超自然体系",
            ]
            dim_section_map = {
                "时间线": "## 时间线",
                "时间历史": "## 时代背景",
                "地理格局": "## 地理格局",
                "地理空间": "## 地理空间",
                "菌丝生物学": "## 菌丝生物学特性",
                "菌丝七亚种": "## 菌丝七大自然亚种",
                "物理规则": "## 菌丝膜的物理特性",
                "社会结构": "## 社会结构",
                "法律与治理": "## 法律与治理",
                "经济体系": "## 经济体系",
                "文化习俗": "## 文化习俗",
                "科技退步": "## 科技水平倒退",
                "科技水平": "## 替代科技树",
                "魔法/超自然体系": "## 菌丝网络的深层规则",
            }

            dimension_groups = OrderedDict()
            for rec in records:
                dim = rec.get("dimension", "其他")
                dimension_groups.setdefault(dim, []).append(rec)

            for dim_name in dimension_order:
                group = dimension_groups.pop(dim_name, None)
                if not group:
                    continue
                section_header = dim_section_map.get(dim_name, f"## {dim_name}")
                lines.extend([section_header, f""])
                for rec in group:
                    entity_id = rec.get("rule_id", "")
                    desc = rec.get("description", "")
                    scope = rec.get("scope", "")
                    constraint_val = rec.get("constraints", "")
                    if isinstance(constraint_val, str) and len(constraint_val) > 2:
                        if constraint_val.startswith('"') and constraint_val.endswith('"'):
                            try:
                                constraint_val = _json.loads(constraint_val)
                            except Exception:
                                pass
                    lines.append(f"**{entity_id}** — {desc}")
                    if scope:
                        lines.append(f"  - 范围：{scope}")
                    if constraint_val:
                        lines.append(f"  - 约束：{constraint_val}")
                    lines.append("")

            for dim_name, group in dimension_groups.items():
                if group:
                    lines.extend([f"## {dim_name}", f""])
                    for rec in group:
                        entity_id = rec.get("rule_id", "")
                        desc = rec.get("description", "")
                        lines.append(f"**{entity_id}** — {desc}")
                        lines.append("")

        return "\n".join(lines)

    def _render_characters(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染人物模块——完整输出layer1-4全部数据"""
        import json as _json

        def _parse_json(val: Any) -> dict:
            if isinstance(val, str):
                try:
                    return _json.loads(val)
                except Exception:
                    return {}
            return val if isinstance(val, dict) else {}

        def _safe_list(val: Any) -> list:
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                return [val] if val else []
            return []

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 人物设定",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无人物数据*")
        else:
            for rec in records:
                entity_id = rec.get("char_id", rec.get("id", "CHAR-000"))
                name = rec.get("name", "")
                role = rec.get("role", "")
                layer1 = _parse_json(rec.get("layer1_identity", rec.get("layer1_json", {})))
                layer2 = _parse_json(rec.get("layer2_psychology", rec.get("layer2_json", {})))
                layer3 = _parse_json(rec.get("layer3_ability", rec.get("layer3_json", {})))
                layer4 = _parse_json(rec.get("layer4_special", rec.get("layer4_json", {})))
                weight = _parse_json(rec.get("weight_json", rec.get("weight", {})))

                # 基础信息
                age = layer1.get("age", rec.get("age", ""))
                gender = layer1.get("gender", "")
                appearance = layer1.get("appearance", "")
                background = layer1.get("background", "")
                social_position = layer1.get("social_position", "")
                height = layer1.get("height", "")

                # 势力信息
                faction_name = rec.get("faction_name", layer1.get("faction", ""))

                lines.extend([
                    f"## {entity_id} {name}",
                    f"",
                    f"### 身份信息",
                    f"",
                    f"| 字段 | 内容 |",
                    f"|------|------|",
                    f"| 姓名 | {name} |",
                    f"| 年龄 | {age} |",
                    f"| 性别 | {gender} |",
                    f"| 身高 | {height} |",
                    f"| 角色定位 | {role} |",
                    f"| 社会位置 | {social_position} |",
                    f"| 所属势力 | {faction_name} |",
                    f"",
                    f"### 外貌",
                    f"",
                    f"{appearance}",
                    f"",
                    f"### 背景",
                    f"",
                    f"{background}",
                    f"",
                ])

                # 心理层
                if layer2:
                    lines.append("### 心理特征")
                    lines.append("")
                    if layer2.get("core_personality"):
                        lines.extend(["**核心性格：**", f"", layer2["core_personality"], f""])
                    if layer2.get("core_motivation"):
                        lines.extend(["**核心动机：**", f"", layer2["core_motivation"], f""])
                    if layer2.get("inner_conflict"):
                        lines.extend(["**内心冲突：**", f"", layer2["inner_conflict"], f""])
                    if layer2.get("habit"):
                        lines.extend(["**习惯/标志性动作：**", f"", layer2["habit"], f""])
                    if layer2.get("body_language_dictionary"):
                        bld = layer2["body_language_dictionary"]
                        if isinstance(bld, dict):
                            lines.append("**肢体语言词典：**")
                            lines.append("")
                            for emotion, actions in bld.items():
                                act_list = _safe_list(actions)
                                lines.append(f"- **{emotion}**：{'；'.join(act_list)}")
                            lines.append("")

                # 能力层
                if layer3:
                    lines.append("### 能力体系")
                    lines.append("")
                    skills = _safe_list(layer3.get("core_skills", []))
                    if skills:
                        lines.append("**核心技能：**")
                        for s in skills:
                            lines.append(f"- {s}")
                        lines.append("")
                    if layer3.get("combat_ability"):
                        lines.extend(["**战斗能力：**", f"", layer3["combat_ability"], f""])
                    if layer3.get("growth_system"):
                        lines.extend(["**成长体系：**", f"", layer3["growth_system"], f""])
                    kb = layer3.get("knowledge_boundaries", {})
                    if isinstance(kb, dict):
                        knows = _safe_list(kb.get("knows", []))
                        not_knows = _safe_list(kb.get("not_knows", []))
                        if knows:
                            lines.append("**知识领域（擅长）：**")
                            for k in knows:
                                lines.append(f"- {k}")
                            lines.append("")
                        if not_knows:
                            lines.append("**知识盲区（不擅长）：**")
                            for k in not_knows:
                                lines.append(f"- {k}")
                            lines.append("")

                # 特殊层
                if layer4:
                    lines.append("### 特殊设定")
                    lines.append("")
                    secrets = _safe_list(layer4.get("secrets", []))
                    if secrets:
                        lines.append("**秘密：**")
                        for s in secrets:
                            if s:
                                lines.append(f"- {s}")
                        lines.append("")
                    cracks = _safe_list(layer4.get("cracks", []))
                    if cracks:
                        lines.append("**弱点/裂隙：**")
                        for c in cracks:
                            if c:
                                lines.append(f"- {c}")
                        lines.append("")
                    if layer4.get("uniqueness"):
                        lines.extend(["**独特性：**", f"", layer4["uniqueness"], f""])

                # 权重
                if weight:
                    lines.append("### 叙事权重")
                    lines.append("")
                    lines.extend([
                        f"| 维度 | 评分 |",
                        f"|------|------|",
                        f"| 角色等级 | {weight.get('tier', '')} |",
                        f"| 弧线贡献 | {weight.get('arc_contribution', '')} |",
                        f"| 剧情驱动 | {weight.get('plot_driving', '')} |",
                        f"| 主题承载 | {weight.get('theme_carrying', '')} |",
                        f"| 网络中心度 | {weight.get('network_centrality', '')} |",
                        f"",
                    ])

        return "\n".join(lines)

    def _render_factions(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染势力模块——叙事化格式"""
        import json as _json
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 势力设定",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无势力数据*")
        else:
            for rec in records:
                entity_id = rec.get("faction_id", rec.get("id", "FAC-000"))
                name = rec.get("name", "")
                faction_type = rec.get("type", "")
                reputation = rec.get("reputation", "")

                lines.extend([
                    f"## {entity_id} {name}",
                    f"",
                    f"**类型：** {faction_type} | **声誉：** {reputation}",
                    f"",
                ])

                hierarchy = rec.get("hierarchy", "")
                if hierarchy:
                    hierarchy_str = hierarchy if isinstance(hierarchy, str) else " → ".join(hierarchy)
                    lines.extend([
                        f"### 组织层级",
                        f"",
                        f"{hierarchy_str}",
                        f"",
                    ])

                goals = self._ensure_list(rec.get("goals", []))
                if goals:
                    lines.extend([f"### 核心目标", f""])
                    for j, g in enumerate(goals, 1):
                        lines.append(f"{j}. {g}")
                    lines.append("")

                resources = self._ensure_list(rec.get("resources", []))
                if resources:
                    lines.extend([f"### 资源", f""])
                    for j, r in enumerate(resources, 1):
                        lines.append(f"{j}. {r}")
                    lines.append("")

                doctrines = self._ensure_list(rec.get("doctrines", []))
                if doctrines:
                    lines.extend([f"### 教义/准则", f""])
                    for j, d in enumerate(doctrines, 1):
                        lines.append(f"{j}. {d}")
                    lines.append("")

                members = rec.get("members", [])
                if isinstance(members, list) and members:
                    lines.extend([f"### 成员", f""])
                    lines.extend([
                        f"| 角色 ID | 职责 | 层级 |",
                        f"|---------|------|------|",
                    ])
                    for m in members:
                        lines.append(
                            f"| {m.get('char_id', '')} | {m.get('role', '')} | {m.get('rank', '')} |"
                        )
                    lines.append("")

        return "\n".join(lines)

    def _render_faction_relations(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染势力关系模块——叙事化格式"""
        import json as _json

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 势力关系",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]

        def _parse_history(val):
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    parsed = _json.loads(val)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
                return [val]
            return [str(val)]

        records = data.get("records", [])
        if not records:
            lines.append("*暂无势力关系数据*")
        else:
            for rec in records:
                faction_a = rec.get('faction_a_name', rec.get('faction_a_id', ''))
                faction_b = rec.get('faction_b_name', rec.get('faction_b_id', ''))
                rel_type = rec.get('type', rec.get('relation_type', ''))
                rel_type_cn = {
                    'alliance': '盟友', 'enmity': '敌对', 'tension': '紧张',
                    'neutral': '中立', 'cooperation': '合作', 'war': '战争',
                }.get(rel_type, rel_type)

                history = _parse_history(rec.get('history', ''))
                treaties = rec.get('treaties', '')
                hidden_agenda = rec.get('hidden_agenda', '')

                lines.extend([
                    f"## {faction_a} ↔ {faction_b}",
                    f"",
                    f"**关系类型：** {rel_type_cn}（{rel_type}）",
                    f"",
                ])

                if history:
                    lines.append("**关系发展历程：**")
                    lines.append("")
                    for h in history:
                        h = str(h).strip()
                        if h:
                            lines.append(f"- {h}")
                    lines.append("")

                if treaties:
                    lines.extend([
                        f"**条约/协议：** {treaties}",
                        f"",
                    ])

                if hidden_agenda:
                    lines.extend([
                        f"**隐藏议程：** {hidden_agenda}",
                        f"",
                    ])

        return "\n".join(lines)

    def _render_relations(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染人物关系模块——叙事化格式"""
        import json as _json

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 人物关系",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]

        def _parse_history(val):
            if isinstance(val, list):
                return val
            if isinstance(val, str):
                try:
                    parsed = _json.loads(val)
                    if isinstance(parsed, list):
                        return parsed
                except Exception:
                    pass
                return [val]
            return [str(val)]

        records = data.get("records", [])
        if not records:
            lines.append("*暂无关系数据*")
        else:
            for rec in records:
                char_a = rec.get('char_a_name', rec.get('char_a_id', ''))
                char_b = rec.get('char_b_name', rec.get('char_b_id', ''))
                rel_type = rec.get('type', rec.get('relation_type', ''))
                rel_type_cn = {
                    'friendship': '友谊', 'rivalry': '对手/竞争', 'mentorship': '师徒',
                    'alliance': '盟友', 'enmity': '敌对', 'neutral': '中立',
                    'tension': '紧张', 'family': '亲情', 'love': '爱情',
                }.get(rel_type, rel_type)

                history = _parse_history(rec.get('history', ''))
                trajectory = rec.get('trajectory', '')

                lines.extend([
                    f"## {char_a} ↔ {char_b}",
                    f"",
                    f"**关系类型：** {rel_type_cn}（{rel_type}）",
                    f"",
                ])

                if history:
                    lines.append("**关系发展历程：**")
                    lines.append("")
                    for h in history:
                        h = str(h).strip()
                        if h:
                            lines.append(f"- {h}")
                    lines.append("")

                if trajectory:
                    lines.extend([
                        f"**关系走向：** {trajectory}",
                        f"",
                    ])

        return "\n".join(lines)

    def _render_arcs(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染角色弧线模块"""
        import json as _json

        def _parse(val: Any):
            if isinstance(val, str):
                try:
                    return _json.loads(val)
                except Exception:
                    return val
            return val

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 角色弧线",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无弧线数据*")
        else:
            for rec in records:
                char_id = rec.get("char_id", "")
                char_name = rec.get("character_name", char_id)
                arc_type = rec.get("arc_type", "")

                title_line = f"## {char_id}"
                if char_name and char_name != char_id:
                    title_line += f" {char_name}"
                if arc_type:
                    title_line += f" — {arc_type}"
                lines.extend([title_line, f""])

                start_state = _parse(rec.get("start_state", {}))
                if isinstance(start_state, dict):
                    status = start_state.get("status", str(start_state))
                    mentality = start_state.get("mentality", "")
                    lines.extend([
                        f"**起点：** {status}",
                        f"",
                    ])
                    if mentality:
                        lines.extend([f"> {mentality}", f""])
                elif start_state:
                    lines.extend([f"**起点：** {start_state}", f""])

                catalyst = rec.get("catalyst_event", rec.get("turning_point", ""))
                if catalyst:
                    lines.extend([f"**催化剂事件：** {catalyst}", f""])

                change_process = rec.get("change_process", [])
                if isinstance(change_process, str):
                    change_process = _parse(change_process)
                if isinstance(change_process, list) and change_process:
                    lines.append("**变化过程：**")
                    lines.append("")
                    for cp in change_process:
                        if isinstance(cp, dict):
                            phase = cp.get("phase", "")
                            event = cp.get("event", "")
                            state = cp.get("state", "")
                            if event:
                                lines.append(f"- **{event}**：{state}")
                        elif isinstance(cp, str):
                            lines.append(f"- {cp}")
                    lines.append("")

                end_state = _parse(rec.get("end_state", {}))
                if isinstance(end_state, dict):
                    status = end_state.get("status", str(end_state))
                    mentality = end_state.get("mentality", "")
                    lines.extend([
                        f"**终点：** {status}",
                        f"",
                    ])
                    if mentality:
                        lines.extend([f"> {mentality}", f""])
                elif end_state:
                    lines.extend([f"**终点：** {end_state}", f""])

                chapter_mapping = rec.get("chapter_mapping", [])
                if isinstance(chapter_mapping, str):
                    chapter_mapping = _parse(chapter_mapping)
                if isinstance(chapter_mapping, list) and chapter_mapping:
                    lines.append("**章节映射：**")
                    lines.append("")
                    for cm in chapter_mapping:
                        if isinstance(cm, dict):
                            phase = cm.get("phase", "")
                            chapters = cm.get("chapters", [])
                            if isinstance(chapters, list):
                                ch_str = ", ".join(f"第{ch}章" for ch in chapters)
                            else:
                                ch_str = str(chapters)
                            lines.append(f"- {phase}：{ch_str}")
                    lines.append("")

        return "\n".join(lines)

    def _render_items(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染物品模块——按A/B/C分类展示"""
        import json as _json
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 物品库",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无物品数据*")
            return "\n".join(lines)

        a_items = []
        b_items = []
        c_items = []

        for rec in records:
            type_ = rec.get("type", "")
            if type_ in ("菌株制品", "A类", "A"):
                a_items.append(rec)
            elif type_ in ("通用末世物资", "B类", "B", "盐", "燃料", "抗生素", "净水药片", "打火机", "种子", "金属工具", "纸笔", "书籍", "无线电零件"):
                b_items.append(rec)
            elif type_ in ("关键剧情道具", "C类", "C"):
                c_items.append(rec)
            else:
                a_items.append(rec)

        if a_items:
            lines.extend([
                f"### **A类：菌株制品（主角团队特产）**",
                f"",
            ])
            for rec in a_items:
                self._render_single_item(lines, rec)
            lines.append("")

        if b_items:
            lines.extend([
                f"### **B类：通用末世物资**",
                f"",
            ])
            for rec in b_items:
                self._render_single_item(lines, rec)
            lines.append("")

        if c_items:
            lines.extend([
                f"### **C类：关键剧情道具（唯一性物品）**",
                f"",
            ])
            for rec in c_items:
                self._render_single_item(lines, rec)
            lines.append("")

        return "\n".join(lines)

    def _render_single_item(self, lines: list, rec: dict):
        entity_id = rec.get("item_id", rec.get("id", "ITEM-000"))
        name = rec.get("name", "")
        type_ = rec.get("type", "")
        purpose = rec.get("purpose", rec.get("description", ""))
        owner = rec.get("current_owner", rec.get("owner", rec.get("holder", "")))
        bg = rec.get("background_story", "")
        restrictions = rec.get("restrictions", [])
        plot_significance = rec.get("significance_to_plot", rec.get("significance", ""))
        lines.extend([
            f"#### {entity_id}: {name}",
            f"",
            f"| 字段 | 内容 |",
            f"|------|------|",
            f"| 名称 | {name} |",
            f"| 类型 | {type_} |",
            f"| 用途 | {purpose} |",
            f"| 持有者 | {owner} |",
            f"",
        ])
        if bg:
            lines.extend([f"**背景故事：** {bg}", f""])
        if restrictions:
            restrictions = self._normalize_restrictions(restrictions)
            if restrictions:
                lines.append("**限制条件：**")
                for idx, r in enumerate(restrictions, 1):
                    lines.append(f"{idx}. {r}")
                lines.append("")
        if plot_significance:
            lines.extend([
                f"**剧情意义：** {plot_significance}",
                f"",
            ])

    @staticmethod
    def _normalize_restrictions(val: Any) -> list:
        """规范化限制条件列表，修复字符被拆分等异常格式"""
        import json as _json
        if isinstance(val, list):
            if len(val) == 0:
                return []
            joined = "".join(str(v) for v in val)
            if len(joined) > 10:
                try:
                    parsed = _json.loads(joined)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed if v]
                    if isinstance(parsed, str):
                        return [parsed]
                except Exception:
                    pass
            if all(len(str(v)) <= 1 for v in val) and len(joined) > 1:
                result = joined.replace("。", "。\n").replace("；", "；\n").replace("，", "，\n")
                return [s.strip() for s in result.split("\n") if s.strip()]
            return [str(v) for v in val if v]
        if isinstance(val, str):
            try:
                parsed = _json.loads(val)
                if isinstance(parsed, list):
                    return [str(v) for v in parsed if v]
                return [str(parsed)]
            except Exception:
                pass
            if len(val) > 5:
                result = val.replace("。", "。\n").replace("；", "；\n")
                return [s.strip() for s in result.split("\n") if s.strip()]
            return [val]
        if val:
            return [str(val)]
        return []

    def _render_foreshadows(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染伏笔模块"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 伏笔管理",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无伏笔数据*")
        else:
            for rec in records:
                entity_id = rec.get("foreshadow_id", rec.get("id", "FORE-000"))
                status = rec.get('status', '待埋设')
                description = rec.get('payload', rec.get('description', ''))
                target = rec.get('reveal_chapter_planned', rec.get('target_chapter', '?'))
                lines.extend([
                    f"## {entity_id}",
                    f"",
                    f"| 字段 | 内容 |",
                    f"|------|------|",
                    f"| 类型 | {rec.get('type', '')} |",
                    f"| 描述 | {description} |",
                    f"| 目标章节 | {target} |",
                    f"| 重要性 | {rec.get('importance', '')} |",
                    f"| 状态 | {status} |",
                    f"",
                    f"> 伏笔「{description[:30]}」预计在第 {target} 章回收",
                    f"",
                ])
        return "\n".join(lines)

    def _render_outline(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染大纲模块"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 大纲",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]

        def _parse(val):
            if isinstance(val, str):
                try:
                    import json
                    return json.loads(val)
                except Exception:
                    return val
            return val

        records = data.get("records", [])

        acts = []
        causal_chain = []
        rhythm_map = []

        if records and isinstance(records, list) and len(records) > 0:
            first_rec = records[0] if isinstance(records[0], dict) else {}
            if first_rec:
                raw_acts = first_rec.get("acts")
                raw_causal = first_rec.get("causal_chain")
                raw_rhythm = first_rec.get("rhythm_map")
                if raw_acts:
                    acts = _parse(raw_acts) if isinstance(raw_acts, str) else raw_acts
                if raw_causal:
                    causal_chain = _parse(raw_causal) if isinstance(raw_causal, str) else raw_causal
                if raw_rhythm:
                    rhythm_map = _parse(raw_rhythm) if isinstance(raw_rhythm, str) else raw_rhythm

        if not isinstance(acts, list):
            acts = []

        if not isinstance(causal_chain, list):
            causal_chain = []

        if not isinstance(rhythm_map, list):
            rhythm_map = []

        for act in acts:
            if not isinstance(act, dict):
                continue
            name = act.get("title") or act.get("name") or act.get("act") or act.get("act_name", "")
            chapters = act.get("chapters", "")
            summary = act.get("description") or act.get("summary", "")
            events = act.get("key_events", [])
            if isinstance(events, str):
                events = _parse(events) if events else []
            events_str = "\n".join(f"  - {e}" for e in events) if isinstance(events, list) else str(events)
            lines.extend([
                f"## {name}",
                f"",
                f"- **章节数**: {chapters}",
                f"- **摘要**: {summary}",
                f"",
            ])
            if events_str:
                lines.extend([
                    f"### 关键事件",
                    f"{events_str}",
                    f"",
                ])

        if causal_chain:
            lines.extend([
                f"## 因果链",
                f"",
                f"| 起因 | 类型 | 结果 |",
                f"|------|------|------|",
            ])
            for link in causal_chain:
                lines.append(
                    f"| {link.get('from_event', '')} "
                    f"| {link.get('cause_type', '')} "
                    f"| {link.get('to_event', '')} |"
                )
            lines.append("")

        if rhythm_map:
            lines.extend([
                f"## 节奏映射",
                f"",
                f"| 段落 | 章节 | 紧张度 |",
                f"|------|------|--------|",
            ])
            for rm in rhythm_map:
                lines.append(
                    f"| {rm.get('section', '')} "
                    f"| {rm.get('chapters', '')} "
                    f"| {rm.get('tension', '')} |"
                )
            lines.append("")

        if not acts and not causal_chain and not rhythm_map:
            lines.append("*暂无大纲数据*")
        return "\n".join(lines)

    def _render_volumes(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染分卷模块"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 分卷配置",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", data.get("volumes", []))
        if not records:
            lines.append("*暂无分卷数据*")
        else:
            for vol in records:
                name = vol.get('name', vol.get('volume_name', ''))
                
                vol_id = vol.get('volume_number', vol.get('vol_number', vol.get('volume_id', '')))
                
                cr = vol.get('chapter_range', [])
                if isinstance(cr, str):
                    import json as _json2
                    try:
                        cr = _json2.loads(cr)
                    except Exception:
                        cr = []
                if isinstance(cr, list) and len(cr) >= 2:
                    start_ch = cr[0]
                    end_ch = cr[1]
                else:
                    start_ch = vol.get('start_chapter', '')
                    end_ch = vol.get('end_chapter', '')
                
                summary = vol.get('summary', vol.get('major_conflict', ''))
                pacing = vol.get('pacing', '')
                
                cf = vol.get('character_focus', [])
                cf_str = ', '.join(cf) if isinstance(cf, list) else str(cf)
                
                themes = vol.get('themes', [])
                themes_str = '、'.join(themes) if isinstance(themes, list) else str(themes)
                
                cliff = vol.get('cliffhanger', '')
                bg = vol.get('boundary_gravity', '')
                
                lines.extend([
                    f"## {name}",
                    f"",
                    f"| 字段 | 内容 |",
                    f"|------|------|",
                    f"| 卷号 | {vol_id} |",
                    f"| 章节范围 | 第{start_ch}章 — 第{end_ch}章 |",
                    f"| 节奏 | {pacing} |",
                    f"| 核心冲突 | {summary} |",
                    f"| 焦点角色 | {cf_str} |",
                    f"| 主题 | {themes_str} |",
                    f"| 边界引力 | {bg} |",
                    f"| 卷末悬念 | {cliff} |",
                    f"",
                ])
        return "\n".join(lines)

    def _render_detail_outline(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染章节细纲模块"""
        import json as _json
        
        def _parse_json(val):
            if isinstance(val, str):
                try:
                    return _json.loads(val)
                except Exception:
                    return {}
            return val if isinstance(val, dict) else {}

        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 章节细纲",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无细纲数据*")
            return "\n".join(lines)

        last_volume = ""
        for ch in records:
            chapter_num = ch.get("chapter_number", ch.get("num", ""))
            
            constraint = _parse_json(ch.get("chapter_constraint_summary", "{}"))
            scenes = _parse_json(ch.get("scenes", []))
            if not isinstance(scenes, list):
                scenes = []
            
            volume = constraint.get("volume", "")
            pacing = constraint.get("pacing", "")
            mood = constraint.get("mood", "")
            chapter_type = constraint.get("chapter_type", "")
            
            if volume and volume != last_volume:
                last_volume = volume
                lines.extend([f"## {volume}", f""])
            
            lines.append(f"### 第 {chapter_num} 章")
            if pacing or mood:
                meta_parts = []
                if pacing:
                    meta_parts.append(f"节奏: {pacing}")
                if mood:
                    meta_parts.append(f"氛围: {mood}")
                if chapter_type:
                    meta_parts.append(f"类型: {chapter_type}")
                lines.append(f"*{' | '.join(meta_parts)}*")
            lines.append("")
            
            if scenes:
                for i, scene in enumerate(scenes, 1):
                    if isinstance(scene, dict):
                        scene_id = scene.get("id", f"s{i}")
                        pov = scene.get("pov_char_id", "")
                        summary = scene.get("summary", "")
                        setting = scene.get("setting", "")
                        participants = scene.get("participants", [])
                        key_elements = scene.get("key_elements", [])
                        
                        if isinstance(participants, str):
                            participants = [participants]
                        if isinstance(key_elements, str):
                            key_elements = [key_elements]
                        
                        lines.append(f"**场景{i}** ({scene_id})")
                        if pov:
                            lines.append(f"- 视角: {pov}")
                        if summary:
                            lines.append(f"- 摘要: {summary}")
                        if setting:
                            lines.append(f"- 地点: {setting}")
                        if participants:
                            lines.append(f"- 参与者: {', '.join(p for p in participants if p)}")
                        if key_elements:
                            ke_str = ', '.join(k for k in key_elements if k)
                            if len(ke_str) > 200:
                                ke_str = ke_str[:200] + "..."
                            lines.append(f"- 关键元素: {ke_str}")
                        lines.append("")
                    else:
                        lines.append(f"{i}. {scene}")
                        lines.append("")
            else:
                lines.append("*暂无场景数据*")
                lines.append("")
            lines.append("---")
            lines.append("")
        return "\n".join(lines)

    def _render_manuscript(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染正文模块"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# 正文",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", [])
        if not records:
            lines.append("*暂无正文数据*")
        else:
            for rec in records:
                chapter_num = rec.get("chapter_number", "?")
                lines.extend([
                    f"## 第 {chapter_num} 章",
                    f"",
                ])
                text = rec.get("text", rec.get("content", rec.get("scenes", "")))
                if text:
                    scenes = self.parse_scenes(text)
                    if scenes:
                        for i, scene in enumerate(scenes):
                            scene_content = scene.get("content", "") if isinstance(scene, dict) else str(scene)
                            if scene_content:
                                lines.append(scene_content)
                                if i < len(scenes) - 1:
                                    lines.append("")
                                    lines.append("* * *")
                                    lines.append("")
                    else:
                        lines.append(str(text))
                lines.append("")
        return "\n".join(lines)

    def parse_scenes(self, text: Any) -> List[Any]:
        """尝试将正文文本解析为场景列表"""
        if isinstance(text, list):
            return text
        if isinstance(text, str):
            text = text.strip()
            if text.startswith("[") or text.startswith("{"):
                try:
                    import json
                    parsed = json.loads(text)
                    if isinstance(parsed, list):
                        return parsed
                    return [parsed]
                except (json.JSONDecodeError, TypeError):
                    pass
        return []

    def _render_overview(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """渲染小说概览"""
        lines = [
            f"# 小说概览",
            f"",
            f"**小说 ID**：{data.get('id', '')}",
            f"",
            f"## 基本信息",
            f"",
            f"| 字段 | 内容 |",
            f"|------|------|",
            f"| 书名 | {title} |",
            f"| 状态 | 创作中 |",
            f"",
        ]
        return "\n".join(lines)

    def _render_generic(self, _module: str, data: Dict[str, Any], title: str) -> str:
        """通用渲染器（未匹配特定模块时使用）"""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        lines = [
            f"# {_module}",
            f"",
            f"> 小说：《{title}》",
            f"> 最后更新：{now}",
            f"",
        ]
        records = data.get("records", data)
        if isinstance(records, list) and records:
            for rec in records:
                lines.append(f"```json")
                import json
                lines.append(json.dumps(rec, ensure_ascii=False, indent=2))
                lines.append(f"```")
                lines.append("")
        elif isinstance(records, dict):
            lines.append(f"```json")
            import json
            lines.append(json.dumps(records, ensure_ascii=False, indent=2))
            lines.append(f"```")
        else:
            lines.append("*暂无数据*")

        return "\n".join(lines)