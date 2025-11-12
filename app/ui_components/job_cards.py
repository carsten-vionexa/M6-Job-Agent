import streamlit as st

def render_job_card(job, profile, ba, existing_feedback=None, on_save=None):
    """
    Zeigt eine Jobkarte mit Feedback-Steuerung.
    - existing_feedback: dict mit {'value': 1/-1/None, 'comment': '...'}
    - on_save: Callback-Funktion (job, feedback_value, comment) -> None
    """

    refnr = job.get("refnr")
    job_key = f"{profile['id']}_{refnr}"

    # --- Kopfbereich ---
    st.markdown(f"**{job.get('titel','')}**  \n_{job.get('arbeitgeber','')}_  \n📍 {job.get('ort','')}")
    color = "🟢" if job.get("fit_score", 0) >= 0.7 else ("🟡" if job.get("fit_score", 0) >= 0.5 else "⚪️")
    st.caption(f"{color} Fit-Score: {job.get('fit_score',0):.2f} – {job.get('why_base','')}")

    # --- Beschreibung ---
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

    # --- Feedback-Auswahl ---
    st.markdown("#### 💬 Feedback")

    # Vorbelegung
    default_value = 1 if existing_feedback and existing_feedback.get("value") == 1 else \
                    -1 if existing_feedback and existing_feedback.get("value") == -1 else 0

    feedback_choice = st.radio(
        "Bewertung:",
        options=[0, 1, -1],
        format_func=lambda x: "Keine Auswahl" if x == 0 else ("✅ Interessant" if x == 1 else "❌ Nicht passend"),
        index=[0, 1, 2].index([0, 1, -1].index(default_value)) if default_value else 0,
        key=f"feedback_radio_{job_key}"
    )

    comment_key = f"comment_{job_key}"
    comment_text = st.text_area("Kommentar (optional):", key=comment_key, height=80,
                                value=(existing_feedback.get("comment") if existing_feedback else ""))

    # --- Speichern ---
    if st.button("💾 Speichern", key=f"save_feedback_{job_key}"):
        feedback_val = feedback_choice if feedback_choice != 0 else None
        comment = (st.session_state.get(comment_key) or "").strip() or None
        if on_save:
            on_save(job, feedback_val, comment)
        st.toast("💾 Feedback gespeichert.", icon="✅")
        st.rerun()

    # --- Markierung: bereits verarbeitet ---
    if existing_feedback:
        val = existing_feedback.get("value")
        emoji = "✅" if val == 1 else "❌" if val == -1 else "💬"
        st.caption(f"{emoji} Bereits bewertet am {existing_feedback.get('timestamp','(unbekannt)')}")