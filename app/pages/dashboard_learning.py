import streamlit as st
import pandas as pd
import sqlite3
import plotly.express as px
from pathlib import Path

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "career_agent.db"

# --------------------------------------------------
# Hilfsfunktionen
# --------------------------------------------------
def load_joined_data():
    """Lädt Jobs + Feedback mit Scores aus SQLite."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT f.id, f.job_id, f.profile_id, f.feedback_value, f.comment, f.match_score AS feedback_score, f.timestamp,
               j.title, j.company, j.location, j.match_score AS job_score
        FROM feedback f
        LEFT JOIN jobs j ON f.job_id = j.id
        ORDER BY f.timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()

    if not df.empty:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
        df["delta_score"] = df["feedback_score"] - df["job_score"]
    return df


# --------------------------------------------------
# Hauptanzeige
# --------------------------------------------------
def render():
    """Zeigt den Lernfortschritt und Score-Entwicklung."""
    st.title("🧠 Lernfortschritt & Score-Anpassung")
    st.caption("Analysiert, wie gut das System deine Präferenzen lernt – Vergleich von BaseScore, Feedback und Anpassung.")

    df = load_joined_data()
    if df.empty:
        st.info("Noch keine Daten für Lernanalyse vorhanden.")
        return

    # --------------------------------------------------
    # 1️⃣ Übersicht
    # --------------------------------------------------
    avg_delta = df["delta_score"].mean().round(3)
    pos_learning = (df["delta_score"] > 0).sum()
    neg_learning = (df["delta_score"] < 0).sum()

    c1, c2, c3 = st.columns(3)
    c1.metric("Ø Lernverschiebung (FitScore - BaseScore)", f"{avg_delta:+.3f}")
    c2.metric("Verbesserte Scores", pos_learning)
    c3.metric("Verschlechterte Scores", neg_learning)

    st.markdown("---")

    # --------------------------------------------------
    # 2️⃣ Verteilung BaseScore vs FeedbackScore
    # --------------------------------------------------
    st.subheader("📊 Vergleich: BaseScore vs FeedbackScore")
    fig_scatter = px.scatter(
        df,
        x="job_score",
        y="feedback_score",
        color=df["feedback_value"].map({1: "Interessant", -1: "Nicht passend"}),
        hover_data=["title", "company"],
        labels={"job_score": "BaseScore (System)", "feedback_score": "Dein Feedback"},
        title="Wie unterscheiden sich Systembewertung und dein Feedback?",
        trendline="ols"
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --------------------------------------------------
    # 3️⃣ Lernverlauf über Zeit
    # --------------------------------------------------
    st.subheader("📈 Lernverlauf (Score-Differenz über Zeit)")
    fig_line = px.line(
        df.sort_values("timestamp"),
        x="timestamp",
        y="delta_score",
        color=df["feedback_value"].map({1: "Interessant", -1: "Nicht passend"}),
        markers=True,
        labels={"timestamp": "Datum", "delta_score": "Δ Score (Feedback - System)"},
        title="Entwicklung der Score-Abweichung über Zeit"
    )
    st.plotly_chart(fig_line, use_container_width=True)

    # --------------------------------------------------
    # 4️⃣ Profil-Lerneffekt (pro Berufsprofil)
    # --------------------------------------------------
    st.subheader("🎯 Lernentwicklung pro Profil")
    prof_df = (
        df.groupby("profile_id")
        .agg(
            feedbacks=("feedback_value", "count"),
            avg_feedback=("feedback_score", "mean"),
            avg_jobscore=("job_score", "mean"),
            delta=("delta_score", "mean"),
        )
        .reset_index()
    )

    fig_prof = px.bar(
        prof_df,
        x="profile_id",
        y="delta",
        color="delta",
        color_continuous_scale=["red", "yellow", "green"],
        title="Durchschnittliche Lernverschiebung pro Profil",
        labels={"profile_id": "Profil-ID", "delta": "Ø Δ Score"}
    )
    st.plotly_chart(fig_prof, use_container_width=True)

    # --------------------------------------------------
    # 5️⃣ Tabelle mit Details
    # --------------------------------------------------
    st.subheader("📋 Details zu einzelnen Feedbacks")
    st.dataframe(
        df[["timestamp", "title", "company", "job_score", "feedback_score", "delta_score", "feedback_value", "comment"]],
        hide_index=True,
        use_container_width=True,
    )

    st.markdown("---")
    st.caption("💡 Positiver Δ-Score bedeutet: Das System hat durch dein Feedback gelernt, den Job stärker zu gewichten.")