import sqlite3, json

conn = sqlite3.connect("data/career_agent.db")
cur = conn.cursor()

cur.execute("SELECT * FROM user_profile WHERE is_active = 1;")
row = cur.fetchone()

# Spaltennamen holen
cols = [c[0] for c in cur.description]
profile = dict(zip(cols, row))

# JSON aus preferences_json laden
prefs = json.loads(profile["preferences_json"])
print(json.dumps(prefs, indent=2))