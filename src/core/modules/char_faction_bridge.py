import json

from sqlalchemy import text

from src.core.modules.base_module import BaseModule, ModuleResult


class CharFactionBridge(BaseModule):
    module_name = "char_faction_bridge"
    depends_on = ["character_builder", "faction_builder", "relation_builder", "faction_relation"]

    def run(self, context: dict, content: dict) -> ModuleResult:
        novel_id = context["novel_id"]
        db = context["db_session"]
        errors = []

        characters = self._load_chars(db, novel_id)
        factions = self._load_factions(db, novel_id)
        relations = self._load_relations(db, novel_id)
        faction_relations = self._load_faction_relations(db, novel_id)
        existing_links = self._load_existing_links(db, novel_id)
        faction_members = self._load_faction_members(db, novel_id)

        char_map = {c["char_id"]: c for c in characters}
        faction_map = {f["faction_id"]: f for f in factions}
        relation_map = self._build_relation_map(relations)
        faction_rel_map = self._build_faction_rel_map(faction_relations)

        issues, resolved_links = self._cross_validate(
            novel_id, char_map, faction_map, relation_map,
            faction_rel_map, existing_links, faction_members,
        )

        self._save_links(db, novel_id, resolved_links)
        db.flush()

        ctx_deps = context.get("dependencies", {})
        dep_chars = ctx_deps.get("人物设定", []) or ctx_deps.get("characters", [])
        dep_factions = ctx_deps.get("势力设定", []) or ctx_deps.get("factions", [])

        validation = {
            "char_faction_links": resolved_links,
            "issues": issues,
            "characters_checked": len(characters),
            "factions_checked": len(factions),
            "links_generated": len(resolved_links),
            "_dependencies": {
                "characters": dep_chars or characters,
                "factions": dep_factions or factions,
            },
        }

        return ModuleResult(
            success=len(errors) == 0,
            summary=f"已交叉验证 {len(characters)} 个角色 × {len(factions)} 个势力，"
                    f"生成 {len(resolved_links)} 条关联，发现 {len(issues)} 个一致性问题",
            data=validation,
            word_count=0,
            errors=errors,
        )

    def validate(self, result: ModuleResult) -> list[str]:
        return result.data.get("issues", [])

    def _load_chars(self, db, novel_id: str) -> list[dict]:
        rows = db.execute(
            text("SELECT * FROM characters WHERE novel_id = :nid"),
            {"nid": novel_id},
        ).fetchall()
        if not rows:
            return []
        keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
        return [dict(zip(keys, row)) for row in rows] if keys else []

    def _load_factions(self, db, novel_id: str) -> list[dict]:
        rows = db.execute(
            text("SELECT * FROM factions WHERE novel_id = :nid"),
            {"nid": novel_id},
        ).fetchall()
        if not rows:
            return []
        keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
        return [dict(zip(keys, row)) for row in rows] if keys else []

    def _load_relations(self, db, novel_id: str) -> list[dict]:
        rows = db.execute(
            text("SELECT * FROM relations WHERE novel_id = :nid"),
            {"nid": novel_id},
        ).fetchall()
        if not rows:
            return []
        keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
        return [dict(zip(keys, row)) for row in rows] if keys else []

    def _load_faction_relations(self, db, novel_id: str) -> list[dict]:
        rows = db.execute(
            text("SELECT * FROM faction_relations WHERE novel_id = :nid"),
            {"nid": novel_id},
        ).fetchall()
        if not rows:
            return []
        keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
        return [dict(zip(keys, row)) for row in rows] if keys else []

    def _load_existing_links(self, db, novel_id: str) -> list[dict]:
        rows = db.execute(
            text("SELECT * FROM char_faction_links WHERE novel_id = :nid"),
            {"nid": novel_id},
        ).fetchall()
        if not rows:
            return []
        keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
        return [dict(zip(keys, row)) for row in rows] if keys else []

    def _load_faction_members(self, db, novel_id: str) -> list[dict]:
        rows = db.execute(
            text("""
                SELECT fm.* FROM faction_members fm
                JOIN factions f ON fm.faction_id = f.faction_id
                WHERE f.novel_id = :nid
            """),
            {"nid": novel_id},
        ).fetchall()
        if not rows:
            return []
        keys = rows[0]._fields if hasattr(rows[0], "_fields") else []
        return [dict(zip(keys, row)) for row in rows] if keys else []

    def _build_relation_map(self, relations: list[dict]) -> dict:
        relation_map = {}
        for r in relations:
            aid = r.get("char_a_id", "")
            bid = r.get("char_b_id", "")
            rtype = r.get("type", "")
            strength = r.get("strength", 0.5)
            key = tuple(sorted([aid, bid]))
            relation_map[key] = {"type": rtype, "strength": strength}
        return relation_map

    def _build_faction_rel_map(self, faction_relations: list[dict]) -> dict:
        frel_map = {}
        for fr in faction_relations:
            fa = fr.get("faction_a_id", "")
            fb = fr.get("faction_b_id", "")
            rtype = fr.get("type", "")
            strength = fr.get("strength", 0.5)
            key = tuple(sorted([fa, fb]))
            frel_map[key] = {"type": rtype, "strength": strength}
        return frel_map

    def _cross_validate(
        self, novel_id: str, char_map: dict, faction_map: dict,
        relation_map: dict, faction_rel_map: dict,
        existing_links: list[dict], faction_members: list[dict],
    ) -> tuple[list[str], list[dict]]:
        issues = []
        link_map = {}
        faction_member_map = {}

        for fm in faction_members:
            fid = fm.get("faction_id", "")
            cid = fm.get("char_id", "")
            role = fm.get("role", "")
            rank = fm.get("rank", "")
            if fid not in faction_member_map:
                faction_member_map[fid] = {}
            faction_member_map[fid][cid] = {"role": role, "rank": rank}

        for el in existing_links:
            cid = el.get("char_id", "")
            fid = el.get("faction_id", "")
            link_map[(cid, fid)] = el

        char_faction_membership = {}
        for fid, members in faction_member_map.items():
            for cid, info in members.items():
                char_faction_membership.setdefault(cid, []).append({
                    "faction_id": fid,
                    "info": info,
                })

        linked_pairs = set()
        resolved_links = []

        for fid, members in faction_member_map.items():
            for cid, info in members.items():
                pair = (cid, fid)
                if pair in linked_pairs:
                    continue
                linked_pairs.add(pair)

                link_record = link_map.get(pair, {
                    "novel_id": novel_id,
                    "char_id": cid,
                    "faction_id": fid,
                    "membership_type": "正式成员",
                    "join_chapter": 1,
                    "leave_chapter": 0,
                    "role_in_faction": info.get("role", ""),
                    "loyalty": 0.7,
                    "notes": "",
                })
                link_record["role_in_faction"] = info.get("role", link_record.get("role_in_faction", ""))
                resolved_links.append(link_record)

        for cid, cdata in char_map.items():
            for fid, fdata in faction_map.items():
                if (cid, fid) in linked_pairs:
                    continue
                default_link = {
                    "novel_id": novel_id,
                    "char_id": cid,
                    "faction_id": fid,
                    "membership_type": "无关联",
                    "join_chapter": 0,
                    "leave_chapter": 0,
                    "role_in_faction": "",
                    "loyalty": 0.0,
                    "notes": "系统推断：角色与该势力暂无直接隶属关系",
                }
                resolved_links.append(default_link)
                linked_pairs.add((cid, fid))

        hostile_faction_pairs = set()
        for (fa, fb), rel in faction_rel_map.items():
            rtype = rel.get("type", "")
            strength = rel.get("strength", 0)
            if rtype in ("敌对", "战争", "竞争") or strength < 0.3:
                hostile_faction_pairs.add((fa, fb))

        for (cid, fid), link in link_map.items():
            link_type = link.get("membership_type", "")
            loyalty = link.get("loyalty", 0.5)

            char_factions = [mf["faction_id"] for mf in char_faction_membership.get(cid, [])]
            for other_fid in char_factions:
                if other_fid == fid:
                    continue
                pair = tuple(sorted([fid, other_fid]))
                if pair in hostile_faction_pairs:
                    issues.append(
                        f"角色'{char_map.get(cid, {}).get('name', cid)}'同时隶属敌对势力"
                        f"'{faction_map.get(fid, {}).get('name', fid)}'和"
                        f"'{faction_map.get(other_fid, {}).get('name', other_fid)}'"
                    )

            cname = char_map.get(cid, {}).get("name", cid)
            fname = faction_map.get(fid, {}).get("name", fid)
            layer1 = cdata.get("layer1_json") or cdata.get("layer1_identity") or "{}"
            if isinstance(layer1, str):
                try:
                    layer1 = json.loads(layer1)
                except (json.JSONDecodeError, TypeError):
                    layer1 = {}
            identity = layer1.get("identity", "") or layer1.get("job", "")

            if identity and fdata:
                fdoctrines = fdata.get("doctrines", "")
                if isinstance(fdoctrines, str):
                    try:
                        fdoctrines_list = json.loads(fdoctrines)
                    except (json.JSONDecodeError, TypeError):
                        fdoctrines_list = []
                else:
                    fdoctrines_list = fdoctrines or []
                doctrines_text = " ".join(fdoctrines_list) if isinstance(fdoctrines_list, list) else str(fdoctrines_list)

                if "军人" in identity and "和平主义" in doctrines_text:
                    issues.append(f"角色'{cname}'身份为军人，但所属势力'{fname}'信奉和平主义")
                if "学者" in identity and "反智" in doctrines_text:
                    issues.append(f"角色'{cname}'身份为学者，但所属势力'{fname}'倾向反智主义")

            if loyalty < 0.3 and link_type in ("正式成员", "核心成员"):
                issues.append(f"角色'{cname}'对'{fname}'忠诚度仅{loyalty:.0%}，但身份是'{link_type}'")

        for (fa, fb), rel in faction_rel_map.items():
            rtype = rel.get("type", "")
            if rtype in ("联盟", "同盟") and fa in faction_member_map and fb in faction_member_map:
                fa_chars = set(faction_member_map[fa].keys())
                fb_chars = set(faction_member_map[fb].keys())
                for ca in fa_chars:
                    for cb in fb_chars:
                        rel_key = tuple(sorted([ca, cb]))
                        char_rel = relation_map.get(rel_key)
                        if char_rel and char_rel.get("type") in ("敌对", "仇敌", "竞争"):
                            cname_a = char_map.get(ca, {}).get("name", ca)
                            cname_b = char_map.get(cb, {}).get("name", cb)
                            fname_a = faction_map.get(fa, {}).get("name", fa)
                            fname_b = faction_map.get(fb, {}).get("name", fb)
                            issues.append(
                                f"角色'{cname_a}'({fname_a})与'{cname_b}'({fname_b})为"
                                f"'{char_rel['type']}'关系，但双方势力为'{rtype}'关系，存在矛盾"
                            )

        return issues, resolved_links

    def _save_links(self, db, novel_id: str, links: list[dict]):
        for link in links:
            db.execute(
                text("""
                    INSERT OR REPLACE INTO char_faction_links
                    (novel_id, char_id, faction_id, membership_type,
                     join_chapter, leave_chapter, role_in_faction,
                     loyalty, notes)
                    VALUES (:novel_id, :char_id, :faction_id, :membership_type,
                            :join_chapter, :leave_chapter, :role_in_faction,
                            :loyalty, :notes)
                """),
                {
                    "novel_id": novel_id,
                    "char_id": link.get("char_id", ""),
                    "faction_id": link.get("faction_id", ""),
                    "membership_type": link.get("membership_type", "无关联"),
                    "join_chapter": link.get("join_chapter", 0),
                    "leave_chapter": link.get("leave_chapter", 0),
                    "role_in_faction": link.get("role_in_faction", ""),
                    "loyalty": link.get("loyalty", 0.0),
                    "notes": link.get("notes", ""),
                },
            )