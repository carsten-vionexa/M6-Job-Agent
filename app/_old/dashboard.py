import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta, timezone

# --------------------------------------------------
# DB Helper
# --------------------------------------------------
def load_feedback_data(db_path="data/career_agent.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT 
            f.timestamp,
            f.feedback_value,
            f.comment,
            f.base_score,
            f.feedback_score,
            j.title AS job_title,
            j.company,
            j.location,
            p.name AS profile_name
        FROM feedback f
        LEFT JOIN jobs j ON f.job_id = j.id
        LEFT JOIN profiles p ON f.profile_id = p.id
        WHERE f.timestamp IS NOT NULL
        ORDER BY f.timestamp DESC
    """, conn)
    conn.close()

    # Zeit und Deltas bereinigen
    df["timestamp"] = pd.to_datetime(df["timestamp"], utc=True, errors="coerce")
    df["delta_score"] = df["feedback_score"].fillna(0) - df["base_score"].fillna(0)

    return df


# --------------------------------------------------
# Dashboard Render
# --------------------------------------------------
def render():
    st.title("📊 Dashboard – Lernstatus & Feedbackanalyse")
    st.caption("Hier siehst du, wie dein Feedback das System verändert hat – "
               "je größer die Differenz, desto stärker der Lerneffekt.")

    # 🔁 Daten immer frisch laden
    if st.button("🔄 Daten neu laden"):
        st.cache_data.clear()

    @st.cache_data(ttl=0)
    def get_feedback_data():
        return load_feedback_data()

    df = get_feedback_data()

    # --------------------------------------------------
    # Kennzahlen
    # --------------------------------------------------
    total = len(df)
    improved = (df["delta_score"] > 0).sum()
    worsened = (df["delta_score"] < 0).sum()
    avg_delta = df["delta_score"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gesamtbewertungen", total)
    col2.metric("Verbesserte Scores", improved)
    col3.metric("Verschlechterte Scores", worsened)
    col4.metric("Ø Delta", f"{avg_delta:.3f}")

    st.markdown("---")

    # --------------------------------------------------
    # Vergleich BaseScore vs FeedbackScore
    # --------------------------------------------------
    st.subheader("🎯 Vergleich: BaseScore vs. FeedbackScore")

    fig_scatter = px.scatter(
        df,
        x="base_score",
        y="feedback_score",
        color="delta_score",
        color_continuous_scale="RdYlGn",
        labels={"base_score": "Systembewertung", "feedback_score": "Deine Bewertung"},
        title="BaseScore (System) vs. FeedbackScore (dein Urteil)"
    )
    fig_scatter.add_shape(
        type="line", x0=0, y0=0, x1=1, y1=1,
        line=dict(color="black", dash="dot")
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --------------------------------------------------
    # Entwicklung über Zeit
    # --------------------------------------------------
    st.subheader("⏱️ Lernentwicklung über Zeit")

    df_time = (
        df.groupby(["profile_name"])
        .resample("1D", on="timestamp")["delta_score"]
        .mean()
        .reset_index()
    )

    fig_time = px.line(
        df_time,
        x="timestamp",
        y="delta_score",
        color="profile_name",
        title="Ø Delta Score pro Tag (gleitend)",
        labels={"delta_score": "Ø Delta (Veränderung)", "timestamp": "Datum"},
        markers=True
    )
    st.plotly_chart(fig_time, use_container_width=True)

    # --------------------------------------------------
    # Detailtabelle
    # --------------------------------------------------
  
    st.subheader("📋 Detaillierte Feedbacks (letzte Bewertungen)")

    # Null-Werte aufbereiten
    df["timestamp"] = df["timestamp"].fillna("–")
    df["job_title"] = df["job_title"].fillna("(kein Titel)")
    df["company"] = df["company"].fillna("(unbekannt)")
    df["profile_name"] = df["profile_name"].fillna("(unbekannt)")
    df["base_score"] = df["base_score"].fillna(0)
    df["feedback_score"] = df["feedback_score"].fillna(0)
    df["delta_score"] = df["feedback_score"] - df["base_score"]

    # Sortieren nach Datum (neueste zuerst)
    df = df.sort_values("timestamp", ascending=False)

    # Relevante Spalten
    df_display = df[[
        "timestamp",
        "profile_name",
        "job_title",
        "company",
        "feedback_value",
        "base_score",
        "feedback_score",
        "delta_score",
        "comment"
    ]]

    # Spaltenbeschriftungen anpassen
    df_display = df_display.rename(columns={
        "timestamp": "Datum",
        "profile_name": "Profil",
        "job_title": "Jobtitel",
        "company": "Unternehmen",
        "feedback_value": "Feedback",
        "base_score": "Score (System)",
        "feedback_score": "Score (Bewertung)",
        "delta_score": "Δ",
        "comment": "Kommentar"
    })

    # Δ farblich hervorheben (positiv = grün, negativ = rot)
    def color_delta(val):
        color = "green" if val > 0 else "red" if val < 0 else "black"
        return f"color: {color};"

    st.dataframe(
        df_display.style.applymap(color_delta, subset=["Δ"]),
        use_container_width=True,
        hide_index=True
    )

    st.caption("Zeigt nur Feedbacks mit vorhandenen Scores – je größer Δ, desto stärker der Lerneffekt.")