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
from src.db_manager import save_jobs_to_db, save_feedback


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

    local_ort = work_modes.get("on_site", {}).get("location", "Görlitz")
    local_radius = work_modes.get("on_site", {}).get("radius_km", 30)
    remote_ort = work_modes.get("hybrid", {}).get("location", "Deutschland")
    remote_radius = min(work_modes.get("hybrid", {}).get("radius_km", 500), 200)

    ba = BAJobSource()
    classifier = BAClassification()
    profiles = load_profiles_for_user()
    all_results = []

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

        # Klassifikations-Erweiterung
        expanded_terms = []
        for q in query_list:
            similar = classifier.classify_term(q)
            expanded_terms.extend([s["bezeichnung"] for s in similar if s.get("bezeichnung")])

        all_terms = list({*query_list, *expanded_terms})
        st.write(f"🔍 Suchbegriffe: {', '.join(all_terms)}")

        jobs_collected = []

        # 1️⃣ Lokale Suche
        st.write(f"🏠 **Lokale Suche:** {local_ort} ({local_radius} km)")
        for term in all_terms:
            jobs_local = ba.search(term, local_ort, local_radius, size=5)
            if jobs_local:
                jobs_collected.extend(jobs_local)

        # 2️⃣ Erweiterte Suche
        if not jobs_collected:
            st.write(f"🌍 **Erweiterte Suche:** {remote_ort} ({remote_radius} km)")
            for term in all_terms:
                jobs_remote = ba.search(term, remote_ort, remote_radius, size=5)
                if jobs_remote:
                    jobs_collected.extend(jobs_remote)

        unique_jobs = {job["refnr"]: job for job in jobs_collected}.values()

        if not unique_jobs:
            st.info("Keine Treffer gefunden.")
            continue

        # ------------------------------------------------------------
        # Anzeige: Treffer + Beschreibung + Link + Feedback
        # ------------------------------------------------------------
        st.write("### Gefundene Stellen:")

        for job in unique_jobs:
            refnr = job.get("refnr")
            job_id = job.get("id") or 0

            col1, col2 = st.columns([5, 2])

            with col1:
                st.markdown(f"**{job['titel']}**  \n_{job['arbeitgeber']}_  \n📍 {job['ort']}")

                # 🔎 Beschreibung ein-/ausklappbar
                with st.expander("🔎 Jobbeschreibung anzeigen / ausblenden", expanded=False):
                    details = ba.get_details(refnr)
                    st.markdown(details.get("beschreibung", "Keine Details verfügbar."))

                    # 🌐 Link zur Originalseite
                    job_url = (
                        details.get("url")
                        or job.get("url")
                        or f"https://www.arbeitsagentur.de/jobsuche/suche?id={refnr}"
                    )
                    if job_url:
                        st.markdown(f"[🌐 Zur Jobseite auf der BA]({job_url})", unsafe_allow_html=True)
                    else:
                        st.caption("Kein externer Link verfügbar.")

            with col2:
                fb_col1, fb_col2 = st.columns(2)
                with fb_col1:
                    if st.button("✅ Interessant", key=f"yes_{p['id']}_{refnr}"):
                        inserted = save_feedback(job_id=job_id, profile_id=p["id"], feedback_value=1)
                        if inserted:
                            st.success("Feedback gespeichert: interessant 👍")

                with fb_col2:
                    if st.button("❌ Nicht interessant", key=f"no_{p['id']}_{refnr}"):
                        inserted = save_feedback(job_id=job_id, profile_id=p["id"], feedback_value=-1)
                        if inserted:
                            st.warning("Feedback gespeichert: nicht passend 👎")

            comment = st.text_input("💬 Kommentar", key=f"comment_{p['id']}_{refnr}")
            if st.button("💾 Speichern Kommentar", key=f"save_comment_{p['id']}_{refnr}"):
                if comment.strip():
                    save_feedback(job_id=job_id, profile_id=p["id"], feedback_value=None, comment=comment)
                    st.info("Kommentar gespeichert.")
                else:
                    st.caption("Bitte Text eingeben, bevor du speicherst.")

            st.divider()

        all_results.append({"profile": profile_title, "jobs": list(unique_jobs)})

    return all_results


# --------------------------------------------------
# Streamlit-UI
# --------------------------------------------------
st.set_page_config(page_title="Job-Recherche", layout="wide")
st.title("🧭 Multi-Profil-Jobrecherche (Bundesagentur für Arbeit)")
st.caption("Sucht zuerst lokal (Görlitz), dann bundesweit. Ermöglicht Sofort-Feedback und Speichern.")

results = search_jobs_for_profiles()
st.success("✅ Suche abgeschlossen.")