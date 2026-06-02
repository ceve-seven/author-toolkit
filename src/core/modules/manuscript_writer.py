import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult


class ManuscriptWriter(BaseModule):
    module_name = "manuscript_writer"
    depends_on = [
        "detail_outline", "world_builder", "character_builder",
        "faction_builder", "item_builder", "foreshadow_manager",
    ]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        chapters = content.get("chapters", [])
        transition_fixes = content.get("transition_fixes", [])
        total_word_count = 0

        for chapter in chapters:
            chapter_number = chapter.get("chapter_number", 0)
            scenes = chapter.get("scenes", [])
            compiled_constraint = chapter.get("compiled_constraint_file", {})

            chapter_word_count = sum(
                s.get("word_count", 0) for s in scenes
            )
            total_word_count += chapter_word_count

            db.execute(
                text("""
                    INSERT OR REPLACE INTO manuscripts
                    (novel_id, chapter_number, title, compiled_constraint_file,
                     scenes, word_count, transition_fixes, status)
                    VALUES (:novel_id, :chapter_number, :title, :compiled_constraint_file,
                            :scenes, :word_count, :transition_fixes, :status)
                """),
                {
                    "novel_id": novel_id,
                    "chapter_number": chapter_number,
                    "title": chapter.get("title", ""),
                    "compiled_constraint_file": json.dumps(
                        compiled_constraint, ensure_ascii=False
                    ),
                    "scenes": json.dumps(scenes, ensure_ascii=False),
                    "word_count": chapter_word_count,
                    "transition_fixes": json.dumps(
                        transition_fixes, ensure_ascii=False
                    ),
                    "status": "draft",
                },
            )

        db.flush()

        ctx_deps = context.get("dependencies", {})
        dep_chars = ctx_deps.get("人物设定", []) or ctx_deps.get("characters", [])
        dep_items = ctx_deps.get("物品库", []) or ctx_deps.get("items", [])
        dep_factions = ctx_deps.get("势力设定", []) or ctx_deps.get("factions", [])
        dep_world = ctx_deps.get("世界观设定", []) or ctx_deps.get("world_building", [])
        dep_foreshadows = ctx_deps.get("伏笔追踪", []) or ctx_deps.get("foreshadows", [])
        dep_detail_outlines = ctx_deps.get("章节细纲", []) or ctx_deps.get("detail_outlines", [])

        detail_outline_chapters = self._extract_detail_outlines(dep_detail_outlines)

        return ModuleResult(
            success=True,
            summary=f"已生成 {len(chapters)} 章正文，共 {total_word_count} 字",
            data={
                "chapters": chapters,
                "transition_fixes": transition_fixes,
                "_dependencies": {
                    "characters": dep_chars,
                    "items": dep_items,
                    "factions": dep_factions,
                    "world_building": dep_world,
                    "foreshadows": dep_foreshadows,
                    "detail_outline": {"chapters": detail_outline_chapters},
                },
            },
            word_count=total_word_count,
            errors=errors,
        )

    def _extract_detail_outlines(self, dep_detail_outlines: list) -> list:
        chapters = []
        for row in dep_detail_outlines:
            if isinstance(row, dict):
                scenes_raw = row.get("scenes", "[]")
                if isinstance(scenes_raw, str):
                    try:
                        scenes = json.loads(scenes_raw)
                    except (json.JSONDecodeError, TypeError):
                        scenes = []
                elif isinstance(scenes_raw, list):
                    scenes = scenes_raw
                else:
                    scenes = []
                chapters.append({
                    "chapter": row.get("chapter_number", 0),
                    "scenes": scenes,
                })
        return chapters

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        data = result.data
        chapters = data.get("chapters", [])

        prompt_rules = self.load_prompt_rules()

        deps = data.get("_dependencies", {})
        dep_chars = deps.get("characters", [])
        dep_items = deps.get("items", [])
        dep_world = deps.get("world_building", [])
        dep_foreshadows = deps.get("foreshadows", [])
        detail_outlines = deps.get("detail_outline", {}).get("chapters", [])

        outline_scene_counts = {
            ch.get("chapter", 0): len(ch.get("scenes", []))
            for ch in detail_outlines
        }

        for chapter in chapters:
            ch_num = chapter.get("chapter_number", 0)
            scenes = chapter.get("scenes", [])
            word_count = chapter.get("word_count", 0)

            expected_scenes = outline_scene_counts.get(ch_num, 0)
            if expected_scenes > 0 and len(scenes) != expected_scenes:
                issues.append(
                    f"第 {ch_num} 章场景数（{len(scenes)}）与细纲（{expected_scenes}）不一致"
                )

            for scene in scenes:
                pov_id = scene.get("pov_char_id", "")
                detail_ch = next(
                    (ch for ch in detail_outlines if ch.get("chapter") == ch_num),
                    {},
                )
                detail_scenes = detail_ch.get("scenes", [])
                matching_ds = [
                    ds
                    for ds in detail_scenes
                    if ds.get("pov_char_id") == pov_id
                ]
                if not matching_ds:
                    issues.append(
                        f"第 {ch_num} 章 POV「{pov_id}」与细纲不匹配"
                    )

                content_text = scene.get("content", "")
                if prompt_rules and content_text:
                    issues.extend(self._check_manuscript_rules(ch_num, scene, content_text))

            transition_fixes = data.get("transition_fixes", [])
            total_fix_words = sum(
                f.get("word_count", 0) for f in transition_fixes
            )
            if total_fix_words > word_count * 0.05 and word_count > 0:
                issues.append(
                    f"第 {ch_num} 章过渡段落字数（{total_fix_words}）超过总字数 5%"
                )

            if dep_chars:
                issues.extend(self._validate_char_consistency_in_chapter(ch_num, scenes, dep_chars))

            if dep_items:
                issues.extend(self._validate_item_usage_in_chapter(ch_num, scenes, dep_items))

            issues.extend(self._validate_common_sense_in_chapter(ch_num, scenes))

        if dep_chars:
            issues.extend(self._validate_pov_consistency(chapters, dep_chars))

        issues.extend(self._validate_timeline_across_chapters(chapters))

        return issues

    def _check_manuscript_rules(self, ch_num: int, scene: dict, text: str) -> list[str]:
        scene_issues = []
        text_len = len(text)
        if text_len < 100:
            return scene_issues

        emotion_labels = ["感到", "觉得", "心中充满", "内心", "感受到", "体会到"]
        emotion_count = sum(text.count(w) for w in emotion_labels)
        if emotion_count > 0:
            scene_issues.append(
                f"第 {ch_num} 章场景「{scene.get('scene_id', '')}」检测到 {emotion_count} 处直接情感告知（如'感到''觉得'），违反情感层次规则"
            )

        transition_words = ["然而", "因此", "与此同时", "另外", "但是", "所以", "此外", "不过", "于是"]
        per_500 = text_len / 500
        transition_count = sum(text.count(w) for w in transition_words) / max(per_500, 1)
        if transition_count > 2:
            scene_issues.append(
                f"第 {ch_num} 章场景过渡词密度 {transition_count:.1f} 次/500字，超过≤2次限制"
            )

        sentences = text.replace("！", "。").replace("？", "。").split("。")
        same_start = 0
        prev_start = ""
        for s in sentences:
            s = s.strip()
            if not s:
                continue
            start_char = s[0]
            if start_char == prev_start:
                same_start += 1
            else:
                same_start = 0
            prev_start = start_char
            if same_start >= 2:
                scene_issues.append(
                    f"第 {ch_num} 章场景连续3句以'{start_char}'开头，违反句式多样性规则"
                )
                break

        short_sentences = sum(1 for s in sentences if len(s.strip()) > 0 and len(s.strip()) <= 8)
        long_sentences = sum(1 for s in sentences if len(s.strip()) >= 25)
        if short_sentences == 0 or long_sentences == 0:
            scene_issues.append(
                f"第 {ch_num} 章场景缺少{'短句(≤8字)' if short_sentences == 0 else '中长句(≥25字)'}"
            )

        return scene_issues

    def _validate_common_sense_in_chapter(self, ch_num: int, scenes: list) -> list[str]:
        issues = []
        for scene in scenes:
            scene_id = scene.get("scene_id", "")
            content = scene.get("content", "")
            if not content or len(content) < 50:
                continue

            content_lower = content.lower()

            if any(w in content_lower for w in ["黑暗", "关灯", "熄灯", "无光", "漆黑", "没有灯"]):
                reading_kw = ["阅读", "看信", "看书", "看文件", "看清", "看颜色", "看字"]
                if any(w in content for w in reading_kw):
                    issues.append(f"第 {ch_num} 章场景「{scene_id}」正文描述黑暗环境，却包含阅读/看清行为")

            if any(w in content_lower for w in ["水下", "水中", "海底", "深海"]):
                speech_kw = ["大声说", "喊", "大声道", "叫道"]
                if any(w in content for w in speech_kw):
                    issues.append(f"第 {ch_num} 章场景「{scene_id}」正文描述水下环境，却包含大声说话")
                if "深呼吸" in content:
                    issues.append(f"第 {ch_num} 章场景「{scene_id}」正文描述水下环境，却包含深呼吸")

            if any(w in content_lower for w in ["真空", "太空", "外太空", "宇宙空间"]):
                sound_kw = ["听见", "听到", "脚步声", "风声", "声音"]
                if any(w in content for w in sound_kw):
                    issues.append(f"第 {ch_num} 章场景「{scene_id}」正文描述真空/太空，却包含听觉描写")

        return issues

    def _validate_char_consistency_in_chapter(self, ch_num: int, scenes: list, dep_chars: list) -> list[str]:
        issues = []
        char_map = {}
        for c in dep_chars:
            name = c.get("name", "")
            role = c.get("role", "")
            layer1 = c.get("layer1_identity") or c.get("layer1_json") or {}
            if isinstance(layer1, str):
                try:
                    layer1 = json.loads(layer1)
                except (json.JSONDecodeError, TypeError):
                    layer1 = {}
            char_map[name] = {
                "role": role,
                "identity": layer1.get("identity", "") or layer1.get("job", "") or "",
            }

        for scene in scenes:
            content = scene.get("content", "")
            if not content:
                continue

            for char_name, char_info in char_map.items():
                if char_name not in content:
                    continue

                identity = char_info["identity"]
                role = char_info["role"]

                if identity and "市民" in identity and role in ("配角", "supporting"):
                    sensitive = ["军事机密", "最高机密", "国家机密", "核弹密码"]
                    if any(w in content for w in sensitive):
                        issues.append(
                            f"第 {ch_num} 章角色'{char_name}'身份为普通市民，正文中涉及机密信息"
                        )

        return issues

    def _validate_item_usage_in_chapter(self, ch_num: int, scenes: list, dep_items: list) -> list[str]:
        issues = []
        item_map = {}
        for i in dep_items:
            name = i.get("name", "")
            purpose = i.get("purpose", "") or i.get("description", "") or ""
            limitation = i.get("restrictions", "") or i.get("limitation", "") or ""
            item_map[name] = {
                "purpose": purpose,
                "limitation": limitation,
            }

        for scene in scenes:
            content = scene.get("content", "")
            if not content:
                continue

            for item_name, item_info in item_map.items():
                if item_name not in content:
                    continue

                limitation = item_info["limitation"]
                purpose = item_info["purpose"]

                if limitation and "装饰" in limitation and ("使用" in content or "功能" in content):
                    issues.append(
                        f"第 {ch_num} 章物品'{item_name}'设定为装饰品（{limitation}），但正文中使用了其功能"
                    )

        return issues

    def _validate_pov_consistency(self, chapters: list, dep_chars: list) -> list[str]:
        issues = []
        if not chapters:
            return issues

        char_roles = {c.get("name", ""): c.get("role", "") for c in dep_chars}
        main_chars = {name for name, role in char_roles.items() if role in ("主角", "protagonist")}
        if not main_chars:
            first_scenes = chapters[0].get("scenes", [])
            main_chars = {first_scenes[0].get("pov_char_id", "")} if first_scenes else set()

        consecutive_non_main = 0
        for chapter in chapters:
            ch_num = chapter.get("chapter_number", 0)
            scenes = chapter.get("scenes", [])
            ch_povs = {s.get("pov_char_id", "") for s in scenes if s.get("pov_char_id")}

            has_main = bool(ch_povs & main_chars)
            if has_main:
                consecutive_non_main = 0
            else:
                consecutive_non_main += 1

            if consecutive_non_main >= 3:
                issues.append(
                    f"第 {ch_num} 章起连续 {consecutive_non_main} 章无主角POV，读者可能忘记谁是主角"
                )

        return issues

    def _validate_timeline_across_chapters(self, chapters: list) -> list[str]:
        issues = []
        if len(chapters) < 2:
            return issues

        last_day_night = None

        for chapter in chapters:
            ch_num = chapter.get("chapter_number", 0)
            scenes = chapter.get("scenes", [])

            day_night_markers = []
            for scene in scenes:
                content = scene.get("content", "")
                if not content:
                    content = scene.get("summary", "")

                if any(w in content for w in ["凌晨", "黎明", "破晓"]):
                    day_night_markers.append("凌晨")
                if any(w in content for w in ["早晨", "清晨", "早上"]):
                    day_night_markers.append("早晨")
                if any(w in content for w in ["中午", "正午", "晌午"]):
                    day_night_markers.append("中午")
                if any(w in content for w in ["下午"]):
                    day_night_markers.append("下午")
                if any(w in content for w in ["傍晚", "黄昏", "夕阳"]):
                    day_night_markers.append("傍晚")
                if any(w in content for w in ["晚上", "夜晚", "深夜", "午夜", "半夜"]):
                    day_night_markers.append("晚上")

            if day_night_markers and last_day_night:
                last_set = set(last_day_night)
                current_set = set(day_night_markers)
                time_order = ["凌晨", "早晨", "中午", "下午", "傍晚", "晚上"]

                last_idx = -1
                for m in last_set:
                    if m in time_order:
                        last_idx = max(last_idx, time_order.index(m))
                curr_idx = len(time_order) + 1
                for m in current_set:
                    if m in time_order:
                        curr_idx = min(curr_idx, time_order.index(m))

                if last_idx >= 0 and curr_idx < len(time_order) and curr_idx < last_idx:
                    gap_desc = f"第 {ch_num-1} 章{'/'.join(last_set)} → 第 {ch_num} 章{'/'.join(current_set)}"
                    chapter_title = chapter.get("title", "")
                    has_marker = any(w in chapter_title + " " + " ".join(s.get("content", "")[:100] for s in scenes) for w in ["第二天", "次日", "隔天", "几天后", "一周后", "数日后"])
                    if not has_marker:
                        issues.append(
                            f"时间线异常：{gap_desc}，相邻章节时间倒退但未标注时间跳跃"
                        )

            if day_night_markers:
                last_day_night = day_night_markers

        return issues


class ManuscriptFixer(BaseModule):
    module_name = "manuscript_fixer"
    depends_on = ["manuscript_writer", "review_executor"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        chapters = content.get("chapters", [])
        fixes = content.get("fixes", [])
        total_word_count = 0

        for chapter in chapters:
            chapter_number = chapter.get("chapter_number", 0)
            scenes = chapter.get("scenes", [])
            chapter_word_count = sum(
                s.get("word_count", 0) for s in scenes
            )
            total_word_count += chapter_word_count

            chapter_title = chapter.get("title", "")

            existing = db.execute(
                text("""
                    SELECT scenes FROM manuscripts
                    WHERE novel_id = :novel_id AND chapter_number = :chapter_number
                """),
                {"novel_id": novel_id, "chapter_number": chapter_number},
            ).scalar()

            db.execute(
                text("""
                    UPDATE manuscripts
                    SET scenes = :scenes, word_count = :word_count,
                        title = :title, status = 'fixed'
                    WHERE novel_id = :novel_id AND chapter_number = :chapter_number
                """),
                {
                    "novel_id": novel_id,
                    "chapter_number": chapter_number,
                    "title": chapter_title,
                    "scenes": json.dumps(scenes, ensure_ascii=False),
                    "word_count": chapter_word_count,
                },
            )

        for fix in fixes:
            db.execute(
                text("""
                    INSERT INTO fix_logs
                    (novel_id, chapter_number, fix_type, issue_ref,
                     original_summary, fixed_summary, timestamp)
                    VALUES (:novel_id, :chapter_number, :fix_type, :issue_ref,
                            :original_summary, :fixed_summary, :timestamp)
                """),
                {
                    "novel_id": novel_id,
                    "chapter_number": fix.get("chapter_number", 0),
                    "fix_type": fix.get("fix_type", ""),
                    "issue_ref": fix.get("issue_ref", ""),
                    "original_summary": fix.get("original_text", "")[:200],
                    "fixed_summary": fix.get("fixed_text", "")[:200],
                    "timestamp": __import__(
                        "datetime"
                    ).datetime.now(
                        __import__("datetime").timezone.utc
                    ).isoformat(),
                },
            )

        db.flush()

        return ModuleResult(
            success=True,
            summary=f"已修正 {len(chapters)} 章，{len(fixes)} 处修复，共 {total_word_count} 字",
            data={"chapters": chapters, "fixes": fixes},
            word_count=total_word_count,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        data = result.data
        chapters = data.get("chapters", [])
        fixes = data.get("fixes", [])

        dependencies = result.data.get("_dependencies", {})
        review_results = dependencies.get("review_executor", {}).get(
            "review_result", {}
        )

        blocker_issues = []
        layer1 = review_results.get("layer1_setting_consistency", {})
        if not layer1.get("passed", True):
            blocker_issues.extend(layer1.get("issues", []))

        for blocker in blocker_issues:
            fixed = any(
                f.get("issue_ref") == blocker.get("description", "")
                for f in fixes
            )
            if not fixed:
                issues.append(
                    f"BLOCKER 级别 issue 未修复：{blocker.get('description', '')}"
                )

        return issues
