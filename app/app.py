import sys, os, json, sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd

# --------------------------------------------------
# Pfadkorrektur
# --------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ba_source import BAJobSource
from src.ba_classification import BAClassification
from src.db_manager import save_jobs_to_db, save_feedback, ensure_job_exists
from src.research_agent import compute_basescore


# --------------------------------------------------
# DB-Ladefunktionen
# --------------------------------------------------
def load_active_user_profile(db_path=None):
    if db_path is None:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "career_agent.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profile WHERE is_active = 1;")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def load_profiles_for_user(db_path=None):
    if db_path is None:
        db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "data", "career_agent.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles;")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
def _map_job_fields(job: dict) -> dict:
    """BA-Felder auf neutrale Keys mappen."""
    job["title"] = job.get("titel", job.get("title", "")) or ""
    job["company"] = job.get("arbeitgeber", job.get("company", "")) or ""
    job["location"] = job.get("ort", job.get("location", "")) or ""
    return job


def _build_profile_for_scoring(selected_profile: dict, all_terms: list, region_from_user_profile: str) -> dict:
    """Profil ergänzen, falls Skills/Summary fehlen."""
    p = dict(selected_profile)
    p["skills"] = selected_profile.get("skills") or ", ".join(all_terms)
    p["summary"] = selected_profile.get("description_text", "") or selected_profile.get("name", "")
    p["region"] = region_from_user_profile or selected_profile.get("region", "")
    return p


# --------------------------------------------------
# Streamlit-UI
# --------------------------------------------------
st.set_page_config(page_title="Job-Recherche", layout="wide")
st.title("🧭 KI-Job- & Karriere-Assistent (Bundesagentur für Arbeit)")
st.caption("Wähle ein Profil, starte die Suche und sieh die passendsten Stellen zuerst.")

# 1️⃣ Profil wählen
profiles = load_profiles_for_user()
if not profiles:
    st.error("❌ Keine Profile gefunden.")
    st.stop()

profile_names = [p["name"] for p in profiles]
selected_profile_name = st.selectbox("👤 Profil auswählen:", profile_names)
selected_profile = next((p for p in profiles if p["name"] == selected_profile_name), None)
if not selected_profile:
    st.warning("Kein gültiges Profil ausgewählt.")
    st.stop()

# --------------------------------------------------
# Jobsuche starten
# --------------------------------------------------
if st.button("🔍 Jobsuche starten"):

    profile_title = selected_profile["name"].split("–")[-1].strip()
    desc = (selected_profile.get("description_text") or "")[:150]

    st.markdown(f"## 👤 {profile_title}")
    st.caption(desc)

    # --- Query-Mapping ---
    title_map = {
        "KI-Enablement Manager": ["Datenanalyst", "Projektleiter KI", "Data Scientist"],
        "Office & CRM Coordinator": ["Bürokaufmann", "Verwaltung", "Sachbearbeiter"],
        "Marketing Operations & Content Manager": ["Marketing Manager", "Online-Marketing", "Kommunikation"]
    }
    query_list = title_map.get(profile_title, [profile_title])

    # --- Klassifikations-Erweiterung ---
    classifier = BAClassification()
    expanded_terms = []
    for q in query_list:
        similar = classifier.classify_term(q)
        expanded_terms.extend([s["bezeichnung"] for s in similar if s.get("bezeichnung")])
    all_terms = list({*query_list, *expanded_terms})
    st.write(f"🔎 Suchbegriffe: {', '.join(all_terms)}")

    # --- Region & Radius aus user_profile ---
    user_profile = load_active_user_profile()
    region = (user_profile.get("region") or "").strip()
    radius = 30
    try:
        if user_profile.get("preferences_json"):
            pj = json.loads(user_profile["preferences_json"])
            if isinstance(pj, dict):
                radius = pj.get("radius_km") or pj.get("radius") or radius
    except Exception:
        pass

    st.write(f"📍 Region: {region or '–'}  |  🔁 Radius: {radius} km")

    # --- Arbeitsagentur-API initialisieren ---
    ba = BAJobSource()
    jobs_collected = []

    # --- Profil für Scoring vorbereiten ---
    profile_for_scoring = _build_profile_for_scoring(selected_profile, all_terms, region)

    # --- Jobsuche ---
    st.write(f"🔍 **Jobsuche in {region or 'Deutschland'} ({radius} km)**")
    for term in all_terms:
        jobs_found = ba.search(term, region or "Deutschland", radius, size=10)
        for job in jobs_found:
            _map_job_fields(job)
            score, why = compute_basescore(job, profile_for_scoring)
            job["base_score"] = score
            job["why_base"] = why
        jobs_collected.extend(jobs_found)

    # --- Ergebnisse vorbereiten ---
    unique_jobs = {job["refnr"]: job for job in jobs_collected}.values()
    unique_jobs = sorted(unique_jobs, key=lambda j: j.get("base_score", 0), reverse=True)

    if not unique_jobs:
        st.info("Keine Treffer gefunden.")
        st.stop()

    # --------------------------------------------------
    # Anzeige + Feedback
    # --------------------------------------------------
    st.write("### Gefundene Stellen:")

    for job in unique_jobs:
        refnr = job.get("refnr")
        col1, col2 = st.columns([5, 2])

        with col1:
            st.markdown(f"**{job.get('titel','')}**  \n_{job.get('arbeitgeber','')}_  \n📍 {job.get('ort','')}")
            color = "🟢" if job.get("base_score", 0) >= 0.7 else ("🟡" if job.get("base_score", 0) >= 0.5 else "⚪️")
            st.caption(f"{color} Score: {job.get('base_score',0):.2f} – {job.get('why_base','Basis-Match aus Titel/Ort')}")

            with st.expander("🔎 Jobbeschreibung anzeigen / ausblenden", expanded=False):
                details = ba.get_details(refnr) if refnr else {}
                beschreibung = (details.get("beschreibung") or "").strip()
                if beschreibung and beschreibung.lower() != "keine details verfügbar.":
                    st.markdown(beschreibung)
                else:
                    st.caption("Keine Details verfügbar.")
                job_url = details.get("url") or job.get("url") or (f"https://www.arbeitsagentur.de/jobsuche/suche?id={refnr}" if refnr else None)
                if job_url:
                    st.markdown(f"[🌐 Zur Jobseite auf der BA]({job_url})", unsafe_allow_html=True)

        with col2:
            fb_col1, fb_col2 = st.columns(2)

            # ✅ Interessant
            if fb_col1.button("✅ Interessant", key=f"yes_{selected_profile['id']}_{refnr}"):
                details = ba.get_details(refnr) if refnr else {}
                job_for_db = {
                    "titel": job.get("titel"),
                    "arbeitgeber": job.get("arbeitgeber"),
                    "ort": job.get("ort"),
                    "beschreibung": details.get("beschreibung", ""),
                    "source": job.get("source", "Bundesagentur für Arbeit"),
                    "refnr": refnr,
                    "url": details.get("url") or job.get("url")
                }
                job_id_db = ensure_job_exists(job_for_db)
                ok = save_feedback(job_id=job_id_db, profile_id=selected_profile["id"], feedback_value=1, comment=None)
                if ok:
                    st.success("Feedback gespeichert: interessant 👍")

            # ❌ Nicht interessant
            if fb_col2.button("❌ Nicht interessant", key=f"no_{selected_profile['id']}_{refnr}"):
                details = ba.get_details(refnr) if refnr else {}
                job_for_db = {
                    "titel": job.get("titel"),
                    "arbeitgeber": job.get("arbeitgeber"),
                    "ort": job.get("ort"),
                    "beschreibung": details.get("beschreibung", ""),
                    "source": job.get("source", "Bundesagentur für Arbeit"),
                    "refnr": refnr,
                    "url": details.get("url") or job.get("url")
                }
                job_id_db = ensure_job_exists(job_for_db)
                ok = save_feedback(job_id=job_id_db, profile_id=selected_profile["id"], feedback_value=0, comment=None)
                if ok:
                    st.warning("Feedback gespeichert: nicht passend 👎")

        # 💬 Kommentar unter den Spalten
        comment = st.text_area("💬 Kommentar eingeben", key=f"comment_{selected_profile['id']}_{refnr}", height=80)
        if st.button("💾 Kommentar speichern", key=f"save_comment_{selected_profile['id']}_{refnr}"):
            if comment.strip():
                details = ba.get_details(refnr) if refnr else {}
                job_for_db = {
                    "titel": job.get("titel"),
                    "arbeitgeber": job.get("arbeitgeber"),
                    "ort": job.get("ort"),
                    "beschreibung": details.get("beschreibung", ""),
                    "source": job.get("source", "Bundesagentur für Arbeit"),
                    "refnr": refnr,
                    "url": details.get("url") or job.get("url")
                }
                job_id_db = ensure_job_exists(job_for_db)
                ok = save_feedback(job_id=job_id_db, profile_id=selected_profile["id"], feedback_value=None, comment=comment)
                if ok:
                    st.info("💾 Kommentar gespeichert.")
            else:
                st.caption("Bitte Text eingeben, bevor du speicherst.")

        st.divider()

st.stop()