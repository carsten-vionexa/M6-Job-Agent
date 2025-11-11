import streamlit as st
import sqlite3, json, os, sys
from datetime import datetime
from pathlib import Path

# Pfadkorrektur, damit src importiert werden kann
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --------------------------------------------------
# Imports aus src
# --------------------------------------------------
from src.ba_source import BAJobSource
from src.ba_classification import BAClassification
from src.db_manager import save_feedback, ensure_job_exists, migrate_schema
from src.research_agent import compute_basescore
from src.learning_engine import store_feedback, predict_fit_score
from app.ui_components.job_cards import render_job_card
from src.db_manager import load_feedback_for_profile


# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
def load_active_user_profile(db_path=None):
    """Lädt aktives Benutzerprofil aus SQLite."""
    if db_path is None:
        db_path = os.path.abspath(os.path.join(ROOT_DIR, "data", "career_agent.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM user_profile WHERE is_active = 1;")
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None


def load_profiles_for_user(db_path=None):
    """Lädt alle gespeicherten Berufsprofile."""
    if db_path is None:
        db_path = os.path.abspath(os.path.join(ROOT_DIR, "data", "career_agent.db"))
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM profiles;")
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _map_job_fields(job: dict) -> dict:
    job["title"] = job.get("titel", job.get("title", "")) or ""
    job["company"] = job.get("arbeitgeber", job.get("company", "")) or ""
    job["location"] = job.get("ort", job.get("location", "")) or ""
    return job


def _build_profile_for_scoring(selected_profile: dict, all_terms: list, region_from_user_profile: str) -> dict:
    """Bereitet Profiltext für Scoring vor."""
    p = dict(selected_profile)
    p["skills"] = selected_profile.get("skills") or ", ".join(all_terms)
    p["summary"] = selected_profile.get("description_text", "") or selected_profile.get("name", "")
    p["region"] = region_from_user_profile or selected_profile.get("region", "")
    return p


def _persist_feedback_and_job(ba, job, profile, refnr, fit_score, feedback_value, comment=None):
    """Speichert Job + Feedback + Chroma."""
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

    job_id_db = ensure_job_exists(job_for_db, matched_profile_id=profile["id"], match_score=fit_score)
    save_feedback(job_id_db, profile["id"], feedback_value, comment, fit_score)
    store_feedback(job_for_db, profile["id"], feedback_value, fit_score, comment)
    return True


# --------------------------------------------------
# Hauptfunktion: render()
# --------------------------------------------------
def render():
    """Streamlit-UI für die Job-Suche"""
    st.title("🔍 Job- & Karriere-Suche")
    st.caption("Suche passende Stellen über die Bundesagentur für Arbeit und gib direkt Feedback.")

    # DB-Schema prüfen
    migrate_schema()

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

    # Benutzerprofil laden (Region etc.)
    user_profile = load_active_user_profile()
    region = (user_profile.get("region") or "").strip()
    radius = 30
    try:
        if user_profile.get("preferences_json"):
            prefs = json.loads(user_profile["preferences_json"])
            radius = prefs.get("radius_km") or prefs.get("radius") or radius
    except Exception:
        pass

    if st.button("🚀 Jobsuche starten"):
        st.session_state["search_started"] = True

    # --------------------------------------------------
    # Suche starten
    # --------------------------------------------------
    if st.session_state.get("search_started"):

        profile_title = selected_profile["name"].split("–")[-1].strip()
        desc = (selected_profile.get("description_text") or "")[:150]

        st.markdown(f"## 👤 {profile_title}")
        st.caption(desc)

        # Query-Erweiterung
        title_map = {
            "KI-Enablement Manager": ["Datenanalyst", "Projektleiter KI", "Data Scientist"],
            "Office & CRM Coordinator": ["Bürokaufmann", "Verwaltung", "Sachbearbeiter"],
            "Marketing Operations & Content Manager": ["Marketing Manager", "Online-Marketing", "Kommunikation"]
        }
        query_list = title_map.get(profile_title, [profile_title])

        classifier = BAClassification()
        expanded_terms = []
        for q in query_list:
            similar = classifier.classify_term(q)
            expanded_terms.extend([s["bezeichnung"] for s in similar if s.get("bezeichnung")])
        all_terms = list({*query_list, *expanded_terms})

        st.write(f"🔎 Suchbegriffe: {', '.join(all_terms)}")
        st.write(f"📍 Region: {region or '–'} | 🔁 Radius: {radius} km")

        # Jobs abrufen
        ba = BAJobSource()
        profile_for_scoring = _build_profile_for_scoring(selected_profile, all_terms, region)
        jobs_collected = []

        for term in all_terms:
            jobs_found = ba.search(term, region or "Deutschland", radius, size=10)
            for job in jobs_found:
                _map_job_fields(job)
                base_score, why = compute_basescore(job, profile_for_scoring)
                fit_score = predict_fit_score(job, base_score)
                job["base_score"] = base_score
                job["fit_score"] = fit_score
                job["why_base"] = why
            jobs_collected.extend(jobs_found)

        unique_jobs = {job["refnr"]: job for job in jobs_collected}.values()
        unique_jobs = sorted(unique_jobs, key=lambda j: j.get("fit_score", 0), reverse=True)

        if not unique_jobs:
            st.info("Keine Treffer gefunden.")
            return

        # --------------------------------------------------
        # Ergebnisanzeige
        # --------------------------------------------------
        st.subheader("📋 Gefundene Stellen")

        # Lade vorhandenes Feedback
        feedback_entries = load_feedback_for_profile(selected_profile["id"])
        feedback_by_job = {f["job_id"]: f for f in feedback_entries}

        for idx, job in enumerate(unique_jobs):
            refnr = job.get("refnr")
            job_key = f"{selected_profile['id']}_{refnr}_{idx}"

            with st.container():
                st.markdown(f"**{job.get('titel','')}**  \n_{job.get('arbeitgeber','')}_  \n📍 {job.get('ort','')}")
                color = "🟢" if job.get("fit_score", 0) >= 0.7 else ("🟡" if job.get("fit_score", 0) >= 0.5 else "⚪️")
                st.caption(f"{color} Fit-Score: {job.get('fit_score',0):.2f} – {job.get('why_base','')}")

                with st.expander("🔎 Jobbeschreibung anzeigen / ausblenden"):
                    details = ba.get_details(refnr) if refnr else {}
                    beschreibung = (details.get("beschreibung") or "").strip()
                    if beschreibung and beschreibung.lower() != "keine details verfügbar.":
                        st.markdown(beschreibung)
                    else:
                        st.caption("Keine Details verfügbar.")
                    job_url = details.get("url") or job.get("url") or (
                        f"https://www.arbeitsagentur.de/jobsuche/suche?id={refnr}" if refnr else None
                    )
                    if job_url:
                        st.markdown(f"[🌐 Zur Jobseite auf der BA]({job_url})")

                # Kommentar + Feedback
                from app.ui_components.job_cards import render_job_card
                from src.db_manager import load_feedback_for_profile

        if st.button("🔄 Neue Suche starten"):
            st.session_state["search_started"] = False
            st.rerun()