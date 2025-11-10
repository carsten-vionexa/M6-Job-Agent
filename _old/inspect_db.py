import sqlite3
from pathlib import Path

# Pfad zur Datenbank
DB_PATH = Path("data/career_agent.db")

def inspect_database(db_path):
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Alle Tabellen abfragen
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name;")
    tables = [row[0] for row in cur.fetchall()]

    print(f"\n📊 Datenbank: {db_path.name}")
    print(f"Gefundene Tabellen: {len(tables)}\n{'-'*60}")

    for table in tables:
        print(f"📋 Tabelle: {table}")
        print("-" * 60)

        # Spalteninformationen abrufen
        cur.execute(f"PRAGMA table_info({table});")
        columns = cur.fetchall()

        if not columns:
            print("⚠️  Keine Spalteninformationen gefunden.\n")
            continue

        print(f"{'ID':<5} {'Name':<25} {'Typ':<15} {'NotNull':<8} {'Default':<20} {'PK':<3}")
        print("-" * 80)
        for col in columns:
            cid, name, col_type, notnull, dflt_value, pk = col
            print(f"{cid:<5} {name:<25} {col_type:<15} {notnull:<8} {str(dflt_value)[:18]:<20} {pk:<3}")
        print("\n")

    conn.close()


if __name__ == "__main__":
    if not DB_PATH.exists():
        print(f"❌ Datenbank nicht gefunden: {DB_PATH}")
    else:
        inspect_database(DB_PATH)