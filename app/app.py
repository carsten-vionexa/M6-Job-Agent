import sys, os, json, sqlite3
import streamlit as st
import pandas as pd
from pathlib import Path

# --------------------------------------------------
# Pfadkorrektur
# --------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ba_source import BAJobSource
from src.ba_utils import resolve_job_title_to_code
from src.db_manager import save_jobs_to_db


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
# Hauptfunktion
# --------------------------------------------------
def search_jobs_for_profiles():
    user_profile = load_active_user_profile()
    if not user_profile:
        st.error("❌ Kein aktives Benutzerprofil gefunden.")
        st.stop()

    prefs = json.loads(user_profile.get("preferences_json") or "{}")
    work_modes = prefs.get("work_modes", {})

    # Lokale Basissuche (Görlitz)
    local_ort = work_modes.get("on_site", {}).get("location", "Görlitz")
    local_radius = work_modes.get("on_site", {}).get("radius_km", 30)

    # Erweiterte (hybride) Suche
    remote_ort = work_modes.get("hybrid", {}).get("location", "Deutschland")
    remote_radius = min(work_modes.get("hybrid", {}).get("radius_km", 500), 200)

    ba = BAJobSource()
    profiles = load_profiles_for_user()
    all_results = []

    # Mapping englischer Titel → deutsche Suchbegriffe
    title_map = {
        "KI-Enablement Manager": ["Datenanalyst", "Projektleiter KI", "Data Scientist"],
        "Office & CRM Coordinator": ["Bürokaufmann", "Verwaltung", "Sachbearbeiter"],
        "Marketing Operations & Content Manager": ["Marketing Manager", "Online-Marketing", "Kommunikation"]
    }

    for p in profiles:
        profile_title = p["name"].split("–")[-1].strip()
        desc = (p.get("description_text") or "")[:150]

        st.markdown(f"## 👤 {profile_title}")
        st.caption(desc)

        query_list = title_map.get(profile_title, [profile_title])
        st.write(f"🔍 Suchbegriffe: {', '.join(query_list)}")

        jobs_collected = []

        # 1️⃣ Lokale Suche
        st.write(f"🏠 **Lokale Suche:** {local_ort} ({local_radius} km)")
        for term in query_list:
            jobs_local = ba.search(term, local_ort, local_radius, size=5)
            if jobs_local:
                jobs_collected.extend(jobs_local)

        # 2️⃣ Erweiterte Suche (wenn lokal leer)
        if not jobs_collected:
            st.write(f"🌍 **Erweiterte Suche:** {remote_ort} ({remote_radius} km)")
            for term in query_list:
                jobs_remote = ba.search(term, remote_ort, remote_radius, size=5)
                if jobs_remote:
                    jobs_collected.extend(jobs_remote)

        # Duplikate entfernen
        unique_jobs = {job["refnr"]: job for job in jobs_collected}.values()

        if not unique_jobs:
            st.info("Keine Treffer gefunden.")
            continue

        # ---------------------------------------------
        # Tabelle mit individuellen Speicheroptionen
        # ---------------------------------------------
        st.write("### Gefundene Stellen:")

        for job in unique_jobs:
            col1, col2, col3 = st.columns([5, 1, 1])
            with col1:
                st.markdown(f"**{job['titel']}**  \n_{job['arbeitgeber']}_  \n📍 {job['ort']}")

            with col2:
                # 🔎 Beschreibung ein-/ausklappbar
               with st.expander("🔎 Jobbeschreibung anzeigen / ausblenden", expanded=False):
                    refnr_or_id = job.get("id") or job.get("refnr")
                    details = ba.get_details(refnr_or_id)
                    st.markdown(details.get("beschreibung", "Keine Details verfügbar."))

                    job_url = (
                        job.get("url")
                        or details.get("url")
                        or f"https://www.arbeitsagentur.de/jobsuche/suche?id={refnr_or_id}"
                    )

                    if job_url:
                        st.markdown(f"[🌐 Zur Jobseite auf der BA]({job_url})")
                    else:
                        st.caption("Kein externer Link verfügbar.")
            with col3:
                # 💾 Speichern
                if st.button("💾", key=f"save_{p['id']}_{job.get('refnr','no_ref')}"):
                    inserted = save_jobs_to_db(
                        profile_id=p["id"],
                        user_profile_id=user_profile["id"],
                        jobs=[job]
                    )
                    st.success(f"{inserted} Job gespeichert.")

            st.divider()

        all_results.append({"profile": profile_title, "jobs": list(unique_jobs)})

    return all_results


# --------------------------------------------------
# Streamlit-UI
# --------------------------------------------------
st.set_page_config(page_title="Job-Recherche", layout="wide")
st.title("🧭 Multi-Profil-Jobrecherche (Bundesagentur für Arbeit)")
st.caption("Sucht zuerst lokal (Görlitz), dann bundesweit. Du kannst einzelne Stellen speichern.")

results = search_jobs_for_profiles()

st.success("✅ Suche abgeschlossen.")