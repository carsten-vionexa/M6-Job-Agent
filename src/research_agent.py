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

        # --- Jobs von der Arbeitsagentur holen ---
        jobs = ba.search(query, ort, radius, size=10)

        # --- NEU: Leichtgewicht-Scoring für jedes Job-Angebot ---
        for job in jobs:
            score, why = compute_basescore(job, p)
            job["base_score"] = score
            job["why_base"] = why

        # Optional: gleich sortieren
        jobs.sort(key=lambda j: j.get("base_score", 0), reverse=True)

        results.append({
            "profile_name": query,
            "description": desc,
            "jobs": jobs
        })
    return results

# research_agent.py – Ausschnitt: Leichtgewicht-Scoring nach Job-Fetch
import re

STOPWORDS = {"und","oder","mit","für","der","die","das","den","dem","ein","eine","in","von","an","im","am","auf","bei","zu","aus","per","the","of","to"}
ROLE_SYNONYMS = {
    "berater":"consultant","daten":"data","wissenschaftler":"scientist",
    "ingenieur":"engineer","entwickler":"developer","analyse":"analytics",
    "architekt":"architect"
}
REMOTE_TOKENS = {"remote","homeoffice","home-office","hybrid"}

def _norm(txt: str) -> str:
    if not txt:
        return ""
    txt = txt.lower()
    txt = txt.replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
    txt = re.sub(r"[^a-z0-9+#]+"," ", txt)
    return txt.strip()

def _toks(txt: str) -> set:
    return {ROLE_SYNONYMS.get(t, t) for t in _norm(txt).split() if t and t not in STOPWORDS}

def _jaccard(a: set, b: set) -> float:
    return 0.0 if not a or not b else len(a & b) / len(a | b)

def compute_basescore(job: dict, profile: dict):
    """Berechnet Basis-Score aus Jobtitel/Ort und Profilfeldern."""
    title = job.get("title", "") or ""
    location = job.get("location", "") or ""
    skills_txt = profile.get("skills", "") or ""
    summary = profile.get("summary", "") or ""
    region = profile.get("region", "") or profile.get("preferred_region", "") or ""

    t = _toks(title)
    prof_skills = {s.strip().lower() for s in re.split(r"[;,/|]", skills_txt) if s.strip()}
    prof_skills = {_norm(s) for s in prof_skills if s}
    prof_skills = {ROLE_SYNONYMS.get(s, s) for s in prof_skills}
    summary_toks = _toks(summary)

    skill_overlap = _jaccard(t, prof_skills | summary_toks)
    role_match = 1.0 if {"consultant","analyst","architect","engineer","scientist","developer"} & t else 0.0
    location_match = 1.0 if (region and _norm(region) in _norm(location)) else (0.5 if REMOTE_TOKENS & (t | _toks(location)) else 0.0)

    score = 0.55 * skill_overlap + 0.25 * role_match + 0.20 * location_match
    score = max(0.0, min(1.0, score))

    why = []
    if skill_overlap >= 0.25:
        overlap = list((t & (prof_skills | summary_toks)) - STOPWORDS)[:2]
        why.append("Skills: " + ", ".join(overlap) if overlap else "Skills passen")
    if role_match: why.append("Rolle passt")
    if location_match == 1.0: why.append("Region passt")
    elif location_match == 0.5: why.append("Remote/Hybrid möglich")
    if not why: why = ["Basis-Match aus Titel/Ort"]

    return round(score,3), " · ".join(why)