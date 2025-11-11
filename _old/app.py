import sys, os, json, sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd
from datetime import datetime

# --------------------------------------------------
# Pfadkorrektur
# --------------------------------------------------
ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from src.ba_source import BAJobSource
from src.ba_classification import BAClassification
from src.db_manager import save_feedback, ensure_job_exists, migrate_schema
from src.research_agent import compute_basescore
from src.learning_engine import store_feedback, predict_fit_score


# --------------------------------------------------
# Session-State initialisieren
# --------------------------------------------------
if "selected_profile" not in st.session_state:
    st.session_state["selected_profile"] = None
if "feedback_done" not in st.session_state:
    st.session_state["feedback_done"] = set()
if "search_started" not in st.session_state:
    st.session_state["search_started"] = False

# DB-Schema prüfen
migrate_schema()

# --------------------------------------------------
# Hilfsfunktionen
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


def _map_job_fields(job: dict) -> dict:
    job["title"] = job.get("titel", job.get("title", "")) or ""
    job["company"] = job.get("arbeitgeber", job.get("company", "")) or ""
    job["location"] = job.get("ort", job.get("location", "")) or ""
    return job


def _build_profile_for_scoring(selected_profile: dict, all_terms: list, region_from_user_profile: str) -> dict:
    p = dict(selected_profile)
    p["skills"] = selected_profile.get("skills") or ", ".join(all_terms)
    p["summary"] = selected_profile.get("description_text", "") or selected_profile.get("name", "")
    p["region"] = region_from_user_profile or selected_profile.get("region", "")
    return p


def _persist_feedback_and_job(ba, job, profile, refnr, fit_score, feedback_value, comment=None):
    """Schreibt Feedback + Job in DB + Chroma."""
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

    job_id_db = ensure_job_exists(
        job_for_db,
        matched_profile_id=profile["id"],
        match_score=fit_score
    )

    ok = save_feedback(
        job_id=job_id_db,
        profile_id=profile["id"],
        feedback_value=feedback_value,
        comment=comment,
        match_score=fit_score
    )

    # In Chroma einfügen
    store_feedback(job_for_db, profile["id"], feedback_value, fit_score, comment)
    return ok


# --------------------------------------------------
# Streamlit UI
# --------------------------------------------------
st.set_page_config(page_title="Job-Recherche", layout="wide")
st.title("🧭 KI-Job- & Karriere-Assistent (Bundesagentur für Arbeit)")
st.caption("Wähle ein Profil, starte die Suche und bewerte die Treffer – dein System lernt mit.")

profiles = load_profiles_for_user()
if not profiles:
    st.error("❌ Keine Profile gefunden.")
    st.stop()

profile_names = [p["name"] for p in profiles]
selected_profile_name = st.selectbox("👤 Profil auswählen:", profile_names)
selected_profile = next((p for p in profiles if p["name"] == selected_profile_name), None)
st.session_state["selected_profile"] = selected_profile

if not selected_profile:
    st.warning("Kein gültiges Profil ausgewählt.")
    st.stop()

if st.button("🔍 Jobsuche starten"):
    st.session_state["search_started"] = True

# --------------------------------------------------
# Hauptanzeige, wenn Suche aktiv
# --------------------------------------------------
if st.session_state["search_started"] and selected_profile:

    profile = st.session_state["selected_profile"]
    profile_title = profile["name"].split("–")[-1].strip()
    desc = (profile.get("description_text") or "")[:150]

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

    # --- BA API Suche ---
    ba = BAJobSource()
    jobs_collected = []
    profile_for_scoring = _build_profile_for_scoring(profile, all_terms, region)

    st.write(f"🔍 **Jobsuche in {region or 'Deutschland'} ({radius} km)**")
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

    # --- Ergebnisse sortieren ---
    unique_jobs = {job["refnr"]: job for job in jobs_collected}.values()
    unique_jobs = sorted(unique_jobs, key=lambda j: j.get("fit_score", 0), reverse=True)

    if not unique_jobs:
        st.info("Keine Treffer gefunden.")
        st.stop()

    # --------------------------------------------------
    # Anzeige + Feedback
    # --------------------------------------------------
    st.write("### Gefundene Stellen:")

    for idx, job in enumerate(unique_jobs):
        refnr = job.get("refnr")
        job_key = f"{profile['id']}_{refnr}_{idx}"

        col1, col2 = st.columns([5, 2])

        with col1:
            st.markdown(f"**{job.get('titel','')}**  \n_{job.get('arbeitgeber','')}_  \n📍 {job.get('ort','')}")
            color = "🟢" if job.get("fit_score", 0) >= 0.7 else ("🟡" if job.get("fit_score", 0) >= 0.5 else "⚪️")
            st.caption(f"{color} Fit-Score: {job.get('fit_score',0):.2f} (Base: {job.get('base_score',0):.2f}) – {job.get('why_base','')}")

            with st.expander("🔎 Jobbeschreibung anzeigen / ausblenden", expanded=False):
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
                    st.markdown(f"[🌐 Zur Jobseite auf der BA]({job_url})", unsafe_allow_html=True)

        with col2:
            ta_key = f"comment_field_{job_key}"
            st.text_area("💬 Kommentar (optional)", key=ta_key, height=80)

            c1, c2 = st.columns(2)

            # ✅ Interessant speichern
            if c1.button("✅ Interessant speichern", key=f"like_save_{job_key}"):
                text = (st.session_state.get(ta_key) or "").strip() or None
                ok = _persist_feedback_and_job(
                    ba, job, profile, refnr,
                    job.get("fit_score", 0),
                    1,  # 👍
                    text
                )
                if ok:
                    st.toast("✅ Interessant + Kommentar gespeichert.", icon="✅")
                    st.rerun()

            # ❌ Nicht passend speichern
            if c2.button("❌ Nicht passend speichern", key=f"dislike_save_{job_key}"):
                text = (st.session_state.get(ta_key) or "").strip() or None
                ok = _persist_feedback_and_job(
                    ba, job, profile, refnr,
                    job.get("fit_score", 0),
                    -1,  # 👎
                    text
                )
                if ok:
                    st.toast("👎 Nicht passend + Kommentar gespeichert.", icon="⚠️")
                    st.rerun()

        st.divider()

    # Optional: Zurück-Button
    if st.button("🔄 Neue Suche starten"):
        st.session_state["search_started"] = False
        st.session_state["feedback_done"] = set()
        st.rerun()