# -*- coding: utf-8 -*-
"""手动触发完整同步并验证output目录"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from config import Config
from src.storage.database.engine import get_session
from src.core.sync.engine import SyncEngine

NOVEL_ID = "NOV-001"

with get_session() as session:
    engine = SyncEngine(session, Config.USER_VIEW_DIR, Config.SYSTEM_DATA_DIR)
    report = engine.sync_json_to_md(NOVEL_ID)
    print(f"同步完成: {report.files_updated} 个文件已更新")
    if report.errors:
        for e in report.errors:
            print(f"  错误: {e}")

# 验证关键文件内容
output_dir = Path(Config.USER_VIEW_DIR) / "神豪：从零开始的无限财富"

print(f"\n=== Output目录结构 ===")
for item in sorted(output_dir.rglob("*.md")):
    rel = item.relative_to(output_dir)
    size = item.stat().st_size
    print(f"  {rel} ({size:,} 字节)")

# 检查关键内容
print(f"\n=== 关键内容验证 ===")

# 检查人物文件是否包含记忆点
char_file = output_dir / "05 人物" / "05_人物.md"
if char_file.exists():
    content = char_file.read_text(encoding="utf-8")
    checks = {
        "记忆点": "memory_points" in content or "记忆点" in content,
        "口头禅": "catchphrase" in content or "口头禅" in content,
        "陈锋": "陈锋" in content,
        "沈婉清": "沈婉清" in content,
        "詹姆斯·洛克": "詹姆斯" in content,
        "张铁军": "张铁军" in content,
    }
    for name, found in checks.items():
        print(f"  人物文件含{name}: {'✅' if found else '❌'}")

# 检查伏笔文件
fs_file = output_dir / "09 伏笔管理" / "09_伏笔管理.md"
if fs_file.exists():
    content = fs_file.read_text(encoding="utf-8")
    fs_count = content.count("FS-")
    print(f"  伏笔文件含FS-标记: {fs_count}次 {'✅' if fs_count >= 20 else '❌'}")

# 检查结构文件
struct_file = output_dir / "10 大纲" / "10_大纲.md"
if struct_file.exists():
    content = struct_file.read_text(encoding="utf-8")
    checks = {
        "大纲": "大纲" in content or "崛起篇" in content,
        "分卷": "分卷" in content or "卷" in content,
        "1500章": "1500" in content,
    }
    for name, found in checks.items():
        print(f"  结构文件含{name}: {'✅' if found else '❌'}")

# 检查概览文件
overview_file = output_dir / "小说概览.md"
if overview_file.exists():
    content = overview_file.read_text(encoding="utf-8")
    print(f"  概览文件大小: {len(content):,} 字符 {'✅' if len(content) > 500 else '❌'}")

print(f"\n验证完成！")
