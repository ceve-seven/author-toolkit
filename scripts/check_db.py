import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.storage.database.engine import get_engine, init_schema
from sqlalchemy import text

init_schema()
engine = get_engine()
conn = engine.connect()
tables = ["novels","inspirations","themes","outlines","world_building","characters",
          "relations","character_arcs","factions","faction_relations","items",
          "foreshadows","archives","synopses","volumes","detail_outlines",
          "manuscripts","review_results","fix_logs"]
total = 0
print(f"{'Table':<22} Records")
print("-"*32)
for t in tables:
    c = conn.execute(text(f"SELECT COUNT(*) FROM {t}")).scalar() or 0
    total += c
    print(f"{t:<22} {c}")
print("-"*32)
print(f"TOTAL: {total}")

# Also list novels
print("\nExisting novels:")
rows = conn.execute(text("SELECT id, title, status, current_step FROM novels")).fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]} | {r[2]} | Step {r[3]}/20")
conn.close()