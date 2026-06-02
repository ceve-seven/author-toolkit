"""AI 小说创作系统 — 项目管理入口

支持多部小说并行管理：
1. 创建新小说项目
2. 查看所有小说列表
3. 选择小说进入创作流程
4. 删除小说项目
"""
from __future__ import annotations

import os
import sys
from typing import List, Optional

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import Config
from src.config.settings import _load_yaml_configs
from src.core.manager import NovelManager, NovelInfo
from src.core.quality.orchestrator import QualityOrchestrator
from src.core.sync.engine import SyncEngine
from src.core.workflow.engine import WorkflowOrchestrator
from src.storage.database.engine import init_schema, create_session, check_integrity, backup_database
from src.storage.vector_store.chroma_client import get_chroma_client
from src.utils.logger_config import setup_logging

logger = setup_logging()

STEP_NAMES = [
    "灵感启动", "小说主题", "世界观设定", "人物设定",
    "势力设定", "物品库", "人物关系", "势力关系", "人物-势力关联", "角色弧线",
    "伏笔追踪", "拟定大纲", "分卷配置", "章节细纲",
    "小说档案", "小说简介", "正文初稿",
    "正文审核", "正文修正", "导出发布",
]


def print_banner():
    print()
    print("  ╔══════════════════════════════════════════════╗")
    print("  ║       AI 小说创作系统  v3.0                  ║")
    print("  ║       项目管理器                              ║")
    print("  ╚══════════════════════════════════════════════╝")
    print()


def print_novel_card(novel: NovelInfo, idx: int):
    step_str = f"{novel.current_step:02d}/20 {novel.step_name}"
    status_icon = "🟢" if novel.status == "创作中" else ("✅" if novel.status == "已完成" else "⏸")
    print(f"  [{idx}] {status_icon} {novel.title}")
    print(f"      ID: {novel.id}  |  进度: {step_str}")
    print(f"      章节: {novel.chapter_count}  角色: {novel.character_count}")
    print(f"      创建: {novel.created_at[:19]}")
    print()


def print_menu():
    print("  ─── 主菜单 ───")
    print("  [1]  创建新小说")
    print("  [2]  查看小说列表")
    print("  [3]  选择小说进入创作")
    print("  [4]  删除小说")
    print("  [0]  退出系统")
    print()


def create_novel_interactive(manager: NovelManager) -> Optional[str]:
    print("\n  ─── 创建新小说 ───")
    title = input("  请输入小说标题 > ").strip()
    if not title:
        print("  取消创建\n")
        return None
    author = input("  请输入作者名（可选）> ").strip()
    novel_id = manager.create_novel(title, author)
    if novel_id:
        print(f"  ✅ 小说《{title}》创建成功！ID: {novel_id}\n")
        return novel_id
    else:
        print(f"  ❌ 创建失败，请检查数据库连接\n")
        return None


def list_novels(manager: NovelManager) -> List[NovelInfo]:
    novels = manager.list_novels()
    if not novels:
        print("  📭 暂无小说项目，请先创建\n")
        return []
    print(f"\n  📚 共 {len(novels)} 部小说\n")
    for i, novel in enumerate(novels, 1):
        print_novel_card(novel, i)
    return novels


def select_novel_interactive(manager: NovelManager) -> Optional[str]:
    novels = manager.list_novels()
    if not novels:
        print("  📭 暂无小说项目，请先创建\n")
        return None
    print(f"\n  ─── 选择小说 ───\n")
    for i, novel in enumerate(novels, 1):
        print_novel_card(novel, i)
    print(f"  [0]  返回主菜单\n")
    try:
        choice = int(input("  请输入编号 > ").strip())
        if choice == 0:
            return None
        if 1 <= choice <= len(novels):
            return novels[choice - 1].id
        print("  无效编号\n")
        return None
    except (ValueError, IndexError):
        print("  无效输入\n")
        return None


def delete_novel_interactive(manager: NovelManager) -> bool:
    novels = manager.list_novels()
    if not novels:
        print("  📭 暂无小说项目\n")
        return False
    print(f"\n  ─── 删除小说 ───\n")
    for i, novel in enumerate(novels, 1):
        print_novel_card(novel, i)
    print(f"  [0]  返回主菜单\n")
    try:
        choice = int(input("  请输入要删除的编号 > ").strip())
        if choice == 0:
            return False
        if 1 <= choice <= len(novels):
            target = novels[choice - 1]
            confirm = input(f"  确认删除《{target.title}》？(y/N) > ").strip().lower()
            if confirm == "y":
                if manager.delete_novel(target.id):
                    print(f"  ✅ 已删除《{target.title}》\n")
                    return True
                else:
                    print(f"  ❌ 删除失败\n")
                    return False
            else:
                print("  已取消\n")
                return False
        print("  无效编号\n")
        return False
    except (ValueError, IndexError):
        print("  无效输入\n")
        return False


def launch_workflow(novel_id: str):
    """启动创作工作流"""
    novel_title = ""
    with create_session() as session:
        row = session.execute(
            __import__("sqlalchemy").text("SELECT title FROM novels WHERE id = :novel_id"),
            {"novel_id": novel_id},
        ).fetchone()
        novel_title = row[0] if row else novel_id

    print(f"\n  {'='*60}")
    print(f"  📖 开始创作: {novel_title}")
    print(f"  ID: {novel_id}")
    print(f"  {'='*60}\n")

    with create_session() as session:
        chroma = get_chroma_client()
        quality = QualityOrchestrator(session)
        quality.load_rules()
        sync = SyncEngine(
            db_session=session,
            user_view_dir=Config.USER_VIEW_DIR,
            system_data_dir=Config.SYSTEM_DATA_DIR,
        )
        workflow = WorkflowOrchestrator(
            db_session=session,
            chroma_client=chroma,
            quality_orchestrator=quality,
            sync_engine=sync,
        )
        workflow.run(novel_id)


def main():
    print_banner()

    print("  📦 初始化系统...")
    init_schema()
    ok, msg = check_integrity()
    if not ok:
        print(f"  ⚠️ 数据库完整性检查异常: {msg}")
        logger.warning("db_integrity_check_failed", error=msg)
    else:
        print(f"  ✅ 数据库完整性检查通过")
    backup_path = backup_database()
    if backup_path:
        print(f"  ✅ 数据库备份: {backup_path}")
    print(f"  ✅ 数据库: {Config.SQLITE_PATH}")
    print(f"  ✅ 输出目录: {Config.USER_VIEW_DIR}")
    print(f"  ✅ ChromaDB: {Config.CHROMADB_PATH}")

    _load_yaml_configs(Config.CONFIG_DIR)

    while True:
        with create_session() as session:
            manager = NovelManager(session)
            print_menu()
            cmd = input("  请输入命令 > ").strip()

            if cmd == "0":
                print("\n  👋 再见！\n")
                break
            elif cmd == "1":
                novel_id = create_novel_interactive(manager)
                if novel_id:
                    launch = input("  是否立即开始创作？(Y/n) > ").strip().lower()
                    if launch != "n":
                        launch_workflow(novel_id)
            elif cmd == "2":
                list_novels(manager)
                input("  按 Enter 返回主菜单...")
            elif cmd == "3":
                novel_id = select_novel_interactive(manager)
                if novel_id:
                    launch_workflow(novel_id)
            elif cmd == "4":
                delete_novel_interactive(manager)
                input("  按 Enter 返回主菜单...")
            else:
                print("  无效命令，请重新输入\n")


if __name__ == "__main__":
    main()