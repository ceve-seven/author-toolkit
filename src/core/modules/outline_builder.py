import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult


class OutlineBuilder(BaseModule):
    module_name = "outline_builder"
    depends_on = ["theme_engine"]

    VALID_CAUSE_TYPES = {"直接因果", "间接因果", "铺垫", "转折", "伏笔"}

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        acts = content.get("acts", [])
        causal_chain = content.get("causal_chain", [])
        rhythm_map = content.get("rhythm_map", [])

        db.execute(
            text("""
                INSERT OR REPLACE INTO outlines
                (novel_id, acts, causal_chain, rhythm_map)
                VALUES (:novel_id, :acts, :causal_chain, :rhythm_map)
            """),
            {
                "novel_id": novel_id,
                "acts": json.dumps(acts, ensure_ascii=False),
                "causal_chain": json.dumps(causal_chain, ensure_ascii=False),
                "rhythm_map": json.dumps(rhythm_map, ensure_ascii=False),
            },
        )
        db.flush()

        total_chapters = sum(a.get("chapters", 0) for a in acts)

        return ModuleResult(
            success=True,
            summary=f"三幕大纲已保存：共 {len(acts)} 幕，{total_chapters} 章，{len(causal_chain)} 条因果链",
            data={
                "acts": acts,
                "causal_chain": causal_chain,
                "rhythm_map": rhythm_map,
                "total_chapters": total_chapters,
            },
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        issues = []
        data = result.data

        prompt_rules = self.load_prompt_rules()

        acts = data.get("acts", [])
        causal_chain = data.get("causal_chain", [])
        rhythm_map = data.get("rhythm_map", [])

        if len(acts) != 3:
            issues.append(f"必须恰好三幕，当前 {len(acts)} 幕")

        if not causal_chain:
            issues.append("因果链不能为空")

        total_chapters = sum(a.get("chapters", 0) for a in acts)
        if total_chapters < 10 or total_chapters > 200:
            issues.append(f"总章节数 10-200，当前 {total_chapters}")

        if len(acts) == 3:
            act1_ch = acts[0].get("chapters", 0)
            act2_ch = acts[1].get("chapters", 0)
            act3_ch = acts[2].get("chapters", 0)
            if act2_ch <= act1_ch:
                issues.append(f"第二幕章节数（{act2_ch}）应大于第一幕（{act1_ch}）")

            if prompt_rules:
                total = act1_ch + act2_ch + act3_ch
                if total > 0:
                    act1_pct = act1_ch / total
                    act2_pct = act2_ch / total
                    act3_pct = act3_ch / total
                    if act1_pct > 0.30:
                        issues.append(f"第一幕占比 {act1_pct:.0%}，超过30%上限")
                    if act3_pct < 0.10:
                        issues.append(f"第三幕占比 {act3_pct:.0%}，低于10%下限")
                    if not (0.15 <= act3_pct <= 0.25):
                        issues.append(f"第三幕占比 {act3_pct:.0%}，建议控制在15-25%")

        all_key_events = []
        for act in acts:
            all_key_events.extend(act.get("key_events", []))

        if all_key_events:
            chain_events = set()
            for link in causal_chain:
                chain_events.add(link.get("from_event", ""))
                chain_events.add(link.get("to_event", ""))
            for event in all_key_events:
                if event not in chain_events:
                    issues.append(f"关键事件「{event}」未出现在因果链中")

        for link in causal_chain:
            cause_type = link.get("cause_type", "")
            if cause_type and cause_type not in self.VALID_CAUSE_TYPES:
                issues.append(f"因果类型「{cause_type}」无效，有效值：{self.VALID_CAUSE_TYPES}")

        if prompt_rules and rhythm_map:
            tensions = [r.get("tension", 0) for r in rhythm_map if r.get("tension") is not None]
            if len(tensions) >= 3:
                peaks = sum(1 for i in range(1, len(tensions)) if tensions[i] > tensions[i-1])
                if peaks < 2:
                    issues.append(f"节奏热力图至少有3次tension峰值变化，当前仅检测到 {peaks+1} 次")

            if len(tensions) >= 5:
                high_streak = 0
                for t in tensions:
                    if t >= 8:
                        high_streak += 1
                    else:
                        high_streak = 0
                    if high_streak >= 5:
                        issues.append("检测到连续5章以上冲突强度≥8，建议插入冷却点")
                        break

        if prompt_rules and causal_chain:
            acts_list = data.get("acts", [])
            if len(acts_list) >= 3:
                cross_act = 0
                for link in causal_chain:
                    from_type = link.get("cause_type", "")
                    if from_type in ("间接因果", "伏笔关联"):
                        cross_act += 1
                if cross_act < 1:
                    issues.append("至少需要1条跨幕因果链（间接因果或伏笔关联）")

        return issues