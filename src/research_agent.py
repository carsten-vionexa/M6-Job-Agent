import sqlite3, json
from src.ba_source import BAJobSource

def load_active_user_profile(db_path="data/career_agent.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profile WHERE is_active = 1;")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None

def load_profiles_for_user(db_path="data/career_agent.db"):
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles;")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]

def search_jobs_for_profiles():
    user_profile = load_active_user_profile()
    if not user_profile:
        print("Kein aktives User-Profil gefunden.")
        return []

    prefs = json.loads(user_profile.get("preferences_json") or "{}")
    work_modes = prefs.get("work_modes", {})

    # Basiseinstellungen (Ort, Radius)
    if prefs.get("remote_option"):
        ort = work_modes.get("hybrid", {}).get("location", "Deutschland")
        radius = work_modes.get("hybrid", {}).get("radius_km", 500)
    else:
        ort = work_modes.get("on_site", {}).get("location", "Görlitz")
        radius = work_modes.get("on_site", {}).get("radius_km", 30)

    profiles = load_profiles_for_user()
    ba = BAJobSource()

    results = []
    for p in profiles:
        query = p["name"] or "Data Analyst"
        desc = (p.get("description_text") or "")[:120]
        print(f"🔍 Suche für {query} ({ort}, {radius} km) ...")
        jobs = ba.search(query, ort, radius, size=10)
        results.append({
            "profile_name": query,
            "description": desc,
            "jobs": jobs
        })
    return results