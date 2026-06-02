import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult
from src.utils import validate_table_name

MIN_SCENES_PER_CHAPTER = 2
MIN_WORD_COUNT_PER_CHAPTER = 2000


class DetailOutlineBuilder(BaseModule):
    module_name = "detail_outline"
    depends_on = ["volume_config", "world_builder", "character_builder", "foreshadow_manager"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        chapters = content.get("chapters", [])

        for chapter in chapters:
            chapter_number = chapter.get("chapter", 0)
            constraint_summary = chapter.get("chapter_constraint_summary", {})
            scenes = chapter.get("scenes", [])

            db.execute(
                text("""
                    INSERT OR REPLACE INTO detail_outlines
                    (novel_id, chapter_number, chapter_constraint_summary, scenes)
                    VALUES (:novel_id, :chapter_number, :chapter_constraint_summary, :scenes)
                """),
                {
                    "novel_id": novel_id,
                    "chapter_number": chapter_number,
                    "chapter_constraint_summary": json.dumps(
                        constraint_summary, ensure_ascii=False
                    ),
                    "scenes": json.dumps(scenes, ensure_ascii=False),
                },
            )

        db.flush()

        total_scenes = sum(
            len(ch.get("scenes", [])) for ch in chapters
        )
        total_word_budget = sum(
            sum(
                s.get("word_count_budget", 0)
                for s in ch.get("scenes", [])
            )
            for ch in chapters
        )

        ctx_deps = context.get("dependencies", {})
        dep_chars = ctx_deps.get("人物设定", []) or ctx_deps.get("characters", [])
        dep_items = ctx_deps.get("物品库", []) or ctx_deps.get("items", [])
        dep_factions = ctx_deps.get("势力设定", []) or ctx_deps.get("factions", [])
        dep_world = ctx_deps.get("世界观设定", []) or ctx_deps.get("world_building", [])
        dep_foreshadows = ctx_deps.get("伏笔追踪", []) or ctx_deps.get("foreshadows", [])

        return ModuleResult(
            success=True,
            summary=f"已保存 {len(chapters)} 章细纲，{total_scenes} 个场景，字数预算 {total_word_budget}",
            data={
                "chapters": chapters,
                "total_word_budget": total_word_budget,
                "_dependencies": {
                    "characters": dep_chars,
                    "items": dep_items,
                    "factions": dep_factions,
                    "world_building": dep_world,
                    "foreshadows": dep_foreshadows,
                },
            },
            word_count=total_word_budget,
            errors=errors,
        )

    def _load_dependency_data(self, db, novel_id: str, data_type: str) -> list[dict]:
        try:
            table_map = {
                "characters": "characters",
                "items": "items",
                "factions": "factions",
            }
            table = table_map.get(data_type)
            if not table:
                return []
            rows = db.execute(
                text(f"SELECT * FROM {validate_table_name(table)} WHERE novel_id = :nid"),
                {"nid": novel_id},
            ).fetchall()
            if not rows:
                return []
            keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
            return [dict(zip(keys, row)) for row in rows] if keys else []
        except Exception:
            return []

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        data = result.data
        chapters = data.get("chapters", [])
        deps = data.get("_dependencies", {})
        dep_chars = deps.get("characters", [])
        dep_items = deps.get("items", [])
        dep_factions = deps.get("factions", [])

        prompt_rules = self.load_prompt_rules()

        for chapter in chapters:
            chapter_number = chapter.get("chapter", 0)
            scenes = chapter.get("scenes", [])

            if len(scenes) < MIN_SCENES_PER_CHAPTER:
                issues.append(
                    f"第 {chapter_number} 章至少 {MIN_SCENES_PER_CHAPTER} 个场景，当前 {len(scenes)} 个"
                )

            scene_word_budget = sum(
                s.get("word_count_budget", 0) for s in scenes
            )
            if scene_word_budget < MIN_WORD_COUNT_PER_CHAPTER:
                issues.append(
                    f"第 {chapter_number} 章字数预算不足 {MIN_WORD_COUNT_PER_CHAPTER}，当前 {scene_word_budget}"
                )

            for scene in scenes:
                pov_id = scene.get("pov_char_id", "")
                if not pov_id:
                    issues.append(
                        f"第 {chapter_number} 章场景「{scene.get('id', '')}」未指定 POV"
                    )

                start_emotion = scene.get("emotional_arc", {}).get(
                    "start_emotion", ""
                )
                end_emotion = scene.get("emotional_arc", {}).get(
                    "end_emotion", ""
                )
                if start_emotion and end_emotion and start_emotion == end_emotion:
                    issues.append(
                        f"第 {chapter_number} 章场景「{scene.get('id', '')}」起始情感与结束情感相同"
                    )

                if prompt_rules:
                    word_budget = scene.get("word_count_budget", 0)
                    if word_budget < 500:
                        issues.append(
                            f"第 {chapter_number} 章场景「{scene.get('id', '')}」字数预算 {word_budget}，低于最小场景字数500"
                        )
                    if word_budget > 2500:
                        issues.append(
                            f"第 {chapter_number} 章场景「{scene.get('id', '')}」字数预算 {word_budget}，超过最大场景字数2500"
                        )

            povs_in_chapter = [
                s.get("pov_char_id", "") for s in scenes
            ]
            for i in range(len(povs_in_chapter) - 1):
                if povs_in_chapter[i] == povs_in_chapter[i + 1]:
                    issues.append(
                        f"第 {chapter_number} 章连续场景使用了相同 POV：{povs_in_chapter[i]}"
                    )

            if prompt_rules:
                self._validate_foreshadow_types(issues, chapter_number, scenes)

        if dep_chars:
            self._validate_pov_switching(issues, chapters, dep_chars)
            self._validate_character_identity(issues, chapters, dep_chars)
            self._validate_common_sense(issues, chapters, dep_chars)

        if dep_items:
            self._validate_item_function(issues, chapters, dep_items)

        self._validate_timeline(issues, chapters)

        return issues

    def _validate_foreshadow_types(self, issues: list, chapter_number: int, scenes: list):
        resolution_types = set()
        for s in scenes:
            resolution_types.add(s.get("resolution_type", ""))
        if resolution_types - {"埋设", "维持", "回收"}:
            issues.append(
                f"第 {chapter_number} 章含未知伏笔操作类型：{resolution_types - {'埋设', '维持', '回收'}}"
            )
        has_maintain = any(
            s.get("resolution_type") == "维持" for s in scenes
        )
        if not has_maintain:
            issues.append(
                f"第 {chapter_number} 章无伏笔维持操作，已埋设伏笔可能被读者遗忘"
            )

    def _validate_common_sense(self, issues: list, chapters: list, dep_chars: list):
        char_names = {c.get("name", "") for c in dep_chars}
        char_roles = {c.get("name", ""): c.get("role", "") for c in dep_chars}

        for chapter in chapters:
            ch_num = chapter.get("chapter", 0)
            scenes = chapter.get("scenes", [])
            chars_in_chapter = set()

            for scene in scenes:
                scene_id = scene.get("id", "")
                summary = scene.get("summary", "")
                setting = scene.get("setting", "")
                pov = scene.get("pov_char_id", "")
                participants = scene.get("participants", [])
                key_elements = scene.get("key_elements", [])

                if pov:
                    chars_in_chapter.add(pov)

                for p in participants:
                    p_name = p if isinstance(p, str) else p.get("name", "")
                    if p_name:
                        chars_in_chapter.add(p_name)

                for elem in (summary, setting):
                    if "已死" in elem or "die" in elem.lower():
                        for c_name in char_names:
                            if c_name in elem and "死" in elem:
                                death_idx = elem.find("死")
                                context_start = max(0, death_idx - 10)
                                context_end = min(len(elem), death_idx + 10)
                                context_text = elem[context_start:context_end]
                                if c_name in context_text and "早已" not in elem and "已经" not in elem:
                                    if elem.count(c_name) <= 1:
                                        continue

                self._validate_sense_by_setting(issues, ch_num, scene_id, setting, summary, key_elements)

            for prev_ch in chapters:
                prev_num = prev_ch.get("chapter", 0)
                if prev_num >= ch_num:
                    continue
                for prev_scene in prev_ch.get("scenes", []):
                    prev_summary = prev_scene.get("summary", "")
                    for c_name in list(chars_in_chapter):
                        death_keywords = [f"{c_name}死", f"{c_name}被杀", f"{c_name}牺牲", f"{c_name}死亡"]
                        if any(dk in prev_summary for dk in death_keywords):
                            still_alive = False
                            for curr_scene in scenes:
                                curr_summary = curr_scene.get("summary", "")
                                if c_name in curr_summary and "回忆" not in curr_summary and "闪回" not in curr_summary:
                                    still_alive = True
                            if still_alive:
                                issues.append(
                                    f"第 {ch_num} 章 '{c_name}' 在第 {prev_num} 章已死亡，但又在第 {ch_num} 章出现"
                                )

    def _validate_sense_by_setting(self, issues: list, ch_num: int, scene_id: str, setting: str, summary: str, key_elements: list):
        if not setting:
            return

        setting_lower = setting.lower()
        combined_text = f"{setting} {summary} {' '.join(key_elements)}"

        if any(w in setting_lower for w in ["黑暗", "关灯", "熄灯", "无光", "漆黑", "黑夜", "没有灯"]):
            reading_keywords = ["阅读", "看信", "看书", "看文件", "看清", "看颜色", "看字", "读"]
            if any(w in combined_text for w in reading_keywords):
                issues.append(f"第 {ch_num} 章场景「{scene_id}」设定为黑暗环境，却包含'阅读/看清'等需要光线的行为")

            color_keywords = ["红色", "蓝色", "绿色", "黄色", "彩色", "颜色"]
            if any(w in combined_text for w in color_keywords):
                issues.append(f"第 {ch_num} 章场景「{scene_id}」设定为黑暗环境，却包含颜色观察")

        if any(w in setting_lower for w in ["水下", "水中", "海底", "深海"]):
            speech_keywords = ["大声说", "喊", "叫", "说话", "对话", "喊叫"]
            if any(w in combined_text for w in speech_keywords) and not any(w in combined_text for w in ["通过手势", "手势", "潜台词", "内心独白", "腹语", "通讯设备"]):
                issues.append(f"第 {ch_num} 章场景「{scene_id}」设定为水下环境，却包含'大声说话/喊叫'等不可能的声音行为")

        if any(w in setting_lower for w in ["真空", "太空", "外太空", "宇宙空间"]):
            sound_keywords = ["听见", "听到", "声音", "响声", "脚步声", "风声"]
            if any(w in combined_text for w in sound_keywords):
                issues.append(f"第 {ch_num} 章场景「{scene_id}」设定为真空/太空，却包含'听到声音'等物理错误")

    def _validate_pov_switching(self, issues: list, chapters: list, dep_chars: list):
        if not chapters:
            return

        char_roles = {c.get("name", ""): c.get("role", "") for c in dep_chars}
        main_chars = {name for name, role in char_roles.items() if role in ("主角", "protagonist")}
        if not main_chars:
            main_chars = {chapters[0].get("scenes", [{}])[0].get("pov_char_id", "")} if chapters and chapters[0].get("scenes") else set()

        consecutive_non_main = 0
        main_appearances = 0
        total_chapters_with_pov = 0

        for chapter in chapters:
            scenes = chapter.get("scenes", [])
            ch_povs = {s.get("pov_char_id", "") for s in scenes if s.get("pov_char_id")}

            has_main = bool(ch_povs & main_chars)
            if has_main:
                main_appearances += 1
                consecutive_non_main = 0
            else:
                consecutive_non_main += 1

            if ch_povs:
                total_chapters_with_pov += 1

            if consecutive_non_main >= 3:
                issues.append(
                    f"第 {chapter.get('chapter', 0)} 章起连续 {consecutive_non_main} 章无主角POV（连续配角POV超过2章）"
                )

        if total_chapters_with_pov > 0:
            main_ratio = main_appearances / total_chapters_with_pov
            if main_ratio < 0.4:
                issues.append(
                    f"主角POV占比 {main_ratio:.0%}，低于最低要求50%"
                )

    def _validate_character_identity(self, issues: list, chapters: list, dep_chars: list):
        char_roles = {}
        for c in dep_chars:
            name = c.get("name", "")
            role = c.get("role", "")
            layer1 = c.get("layer1_identity") or c.get("layer1_json") or {}
            if isinstance(layer1, str):
                try:
                    layer1 = json.loads(layer1)
                except (json.JSONDecodeError, TypeError):
                    layer1 = {}
            char_roles[name] = {
                "role": role,
                "identity": layer1.get("identity", "") or layer1.get("job", "") or "",
                "origin": layer1.get("origin", ""),
            }

        nickname_registry = {}
        for chapter in chapters:
            ch_num = chapter.get("chapter", 0)
            scenes = chapter.get("scenes", [])

            for scene in scenes:
                summary = scene.get("summary", "")
                participants = scene.get("participants", [])

                for p in participants:
                    p_name = p if isinstance(p, str) else p.get("name", "")
                    if not p_name:
                        continue

                    if p_name in char_roles:
                        char_info = char_roles[p_name]
                        role = char_info["role"]
                        identity = char_info["identity"]

                        if identity and "市民" in identity and role in ("配角", "supporting"):
                            sensitive_topics = ["军事机密", "核弹", "最高机密", "国家机密"]
                            if any(t in summary for t in sensitive_topics):
                                issues.append(
                                    f"第 {ch_num} 章角色'{p_name}'身份为普通市民，涉及敏感机密信息"
                                )

                    if p_name not in nickname_registry:
                        nickname_registry[p_name] = p_name

    def _validate_timeline(self, issues: list, chapters: list):
        if len(chapters) < 2:
            return

        last_day_night = None

        for chapter in chapters:
            ch_num = chapter.get("chapter", 0)
            scenes = chapter.get("scenes", [])
            time_setting = chapter.get("time_setting", {})
            chapter_time_desc = (time_setting.get("description", "") if isinstance(time_setting, dict) else str(time_setting))

            day_night_markers = []
            for scene in scenes:
                setting = scene.get("setting", "")
                summary = scene.get("summary", "")

                if "凌晨" in setting or "凌晨" in summary:
                    day_night_markers.append("凌晨")
                if "早晨" in setting or "早晨" in summary or "清晨" in summary or "早上" in summary:
                    day_night_markers.append("早晨")
                if "中午" in setting or "中午" in summary:
                    day_night_markers.append("中午")
                if "下午" in setting or "下午" in summary:
                    day_night_markers.append("下午")
                if "傍晚" in setting or "傍晚" in summary or "黄昏" in summary:
                    day_night_markers.append("傍晚")
                if "晚上" in setting or "晚上" in summary or "夜晚" in summary or "深夜" in summary or "午夜" in summary:
                    day_night_markers.append("晚上")

            if day_night_markers:
                unique_markers = list(set(day_night_markers))
                if len(unique_markers) >= 3:
                    has_transition = any(w in chapter_time_desc for w in ["到", "至", "直到", "经过", "过了"])
                    if not has_transition:
                        issues.append(
                            f"第 {ch_num} 章时间跨度过大（{'/'.join(unique_markers)}），但未标注时间过渡"
                        )

                if last_day_night and day_night_markers:
                    last_set = set(last_day_night)
                    current_set = set(day_night_markers)
                    time_order = ["凌晨", "早晨", "中午", "下午", "傍晚", "晚上"]
                    if last_set and current_set:
                        last_idx = -1
                        for m in last_set:
                            if m in time_order:
                                last_idx = max(last_idx, time_order.index(m))
                        curr_idx = len(time_order) + 1
                        for m in current_set:
                            if m in time_order:
                                curr_idx = min(curr_idx, time_order.index(m))
                        if last_idx >= 0 and curr_idx < len(time_order) and curr_idx < last_idx:
                            skip_desc = f"第 {ch_num-1} 章{'/'.join(last_set)} → 第 {ch_num} 章{'/'.join(current_set)}"
                            has_time_jump = any(w in chapter_time_desc for w in ["第二天", "次日", "隔天", "几天后", "一周后"])
                            if not has_time_jump:
                                issues.append(
                                    f"第 {ch_num} 章时间线异常：{skip_desc}，时间跳跃未标注"
                                )

                last_day_night = day_night_markers

    def _validate_item_function(self, issues: list, chapters: list, dep_items: list):
        item_names = {i.get("name", ""): i for i in dep_items}
        if not item_names:
            return

        item_usage_log = {}

        for chapter in chapters:
            ch_num = chapter.get("chapter", 0)
            scenes = chapter.get("scenes", [])
            items_in_chapter = {}

            for scene in scenes:
                key_elements = scene.get("key_elements", [])
                summary = scene.get("summary", "")
                combined = " ".join(key_elements) + " " + summary

                for item_name, item_data in item_names.items():
                    if item_name not in combined:
                        continue

                    if item_name not in item_usage_log:
                        item_usage_log[item_name] = {
                            "first_seen_ch": ch_num,
                            "last_status": None,
                            "used_count": 0,
                            "chapters_used": [],
                            "damaged": False,
                            "lost": False,
                        }

                    log = item_usage_log[item_name]
                    log["used_count"] += 1
                    log["chapters_used"].append(ch_num)

                    if "损坏" in combined or "破损" in combined or "坏" in combined or "碎" in combined or "断" in combined:
                        log["damaged"] = True
                        log["last_status"] = "损坏"

                    if "丢失" in combined or "丢了" in combined or "被夺" in combined or "遗失" in combined:
                        log["lost"] = True
                        log["last_status"] = "丢失"

                    items_in_chapter[item_name] = log

            for item_name, log in items_in_chapter.items():
                if log.get("damaged") and item_name in item_usage_log:
                    for prev_ch_num in item_usage_log[item_name].get("chapters_used", []):
                        if prev_ch_num < ch_num:
                            pass

        for item_name, log in item_usage_log.items():
            if log.get("damaged") and log.get("lost"):
                repaired_or_found = False
                for ch_num in reversed(log.get("chapters_used", [])):
                    ch = next((c for c in chapters if c.get("chapter", 0) == ch_num), None)
                    if ch:
                        for scene in ch.get("scenes", []):
                            combined = " ".join(scene.get("key_elements", [])) + " " + scene.get("summary", "")
                            if "修好" in combined or "找到" in combined or "捡回" in combined or "复原" in combined:
                                repaired_or_found = True
                                break
                    if repaired_or_found:
                        break

                if not repaired_or_found and log.get("chapters_used", []):
                    last_ch = log["chapters_used"][-1]
                    for ch_num in log["chapters_used"]:
                        ch = next((c for c in chapters if c.get("chapter", 0) == ch_num), None)
                        if ch:
                            for scene in ch.get("scenes", []):
                                combined = " ".join(scene.get("key_elements", [])) + " " + scene.get("summary", "")
                                if item_name in combined and "回忆" not in combined and "回想" not in combined:
                                    if "损坏" not in combined and "丢失" not in combined and "修复" not in combined:
                                        if ch_num > max(0, last_ch):
                                            pass
