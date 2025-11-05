import streamlit as st
import sqlite3
from pathlib import Path
from datetime import datetime
import pandas as pd

DB_PATH = Path(__file__).resolve().parents[1] / "data" / "career_agent.db"
UPLOAD_DIR = Path(__file__).resolve().parents[1] / "reports" / "outputs"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def get_connection():
    return sqlite3.connect(DB_PATH)

def save_application(job_id, file_path):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO applications (job_id, filename, file_path, date_created)
        VALUES (?, ?, ?, ?)
    """, (
        job_id,
        Path(file_path).name,
        str(file_path),
        datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ))
    conn.commit()
    conn.close()

# === Streamlit ===
st.set_page_config(page_title="Job Tracker", page_icon="💼", layout="wide")
st.title("💼 Persönliche Job-Datenbank")

tab1, tab2 = st.tabs(["➕ Neue Jobs", "📂 Bewerbungsdateien"])

# --- Tab 1: Neue Jobs ---
with tab1:
    st.subheader("📝 Job hinzufügen")
    title = st.text_input("Jobtitel")
    company = st.text_input("Unternehmen")
    location = st.text_input("Ort")
    app_type = st.radio("Art der Bewerbung", ["Ausschreibung", "Initiativbewerbung"], horizontal=True)
    description = st.text_area("Kurzbeschreibung")
    url = st.text_input("Job-URL (optional)")

    if st.button("💾 Job speichern"):
        if title and company:
            conn = get_connection()
            conn.execute("""
                INSERT INTO jobs (title, company, location, description, source, url, date_posted, application_type)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (title, company, location, description, "manual", url, datetime.now().strftime("%Y-%m-%d"), app_type))
            conn.commit()
            conn.close()
            st.success(f"✅ {app_type} '{title}' bei {company} gespeichert.")
        else:
            st.error("Titel und Unternehmen erforderlich.")

    st.divider()

    st.subheader("📋 Bestehende Einträge")
    conn = get_connection()
    jobs_df = pd.read_sql_query("""
        SELECT id AS ID, title AS Titel, company AS Unternehmen, application_type AS Art, date_posted AS Datum
        FROM jobs ORDER BY date_posted DESC
    """, conn)
    conn.close()
    st.dataframe(jobs_df, use_container_width=True)

# --- Tab 2: Bewerbungsdateien ---
with tab2:
    st.subheader("📎 Bewerbung zu bestehendem Job hinzufügen")
    conn = get_connection()
    jobs = conn.execute("SELECT id, title, company FROM jobs ORDER BY date_posted DESC").fetchall()
    conn.close()

    if jobs:
        job_options = {f"{j[1]} – {j[2]}": j[0] for j in jobs}
        selected_job = st.selectbox("Job auswählen", list(job_options.keys()))
        uploaded_file = st.file_uploader("Bewerbung (PDF oder DOCX)", type=["pdf", "docx"])

        if uploaded_file and st.button("📤 Datei speichern"):
            job_id = job_options[selected_job]
            save_path = UPLOAD_DIR / uploaded_file.name
            with open(save_path, "wb") as f:
                f.write(uploaded_file.getbuffer())
            save_application(job_id, save_path)
            st.success(f"✅ Datei gespeichert und mit Job '{selected_job}' verknüpft.")
    else:
        st.info("Noch keine Jobs in der Datenbank – bitte zuerst im Tab 'Neue Jobs' anlegen.")