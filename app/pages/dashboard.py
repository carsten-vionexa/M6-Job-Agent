import streamlit as st
import pandas as pd
import plotly.express as px
import sqlite3
from datetime import datetime, timedelta

# --------------------------------------------------
# DB Helper
# --------------------------------------------------
def load_feedback_data(db_path="data/career_agent.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT f.timestamp, f.feedback_value, f.match_score,
               f.comment, j.title, j.company, j.location
        FROM feedback f
        LEFT JOIN jobs j ON f.job_id = j.id
        ORDER BY f.timestamp DESC
    """, conn)
    conn.close()
    return df


# --------------------------------------------------
# Dashboard Render
# --------------------------------------------------
def render():
    st.title("📊 Dashboard – Lernstatus & Feedbackanalyse")
    st.caption("Überblick über deine bisherigen Bewertungen, Scores und den Lernverlauf.")

    df = load_feedback_data()
    if df.empty:
        st.info("Noch keine Feedbackdaten vorhanden.")
        return

    # --------------------------------------------------
    # Kennzahlen
    # --------------------------------------------------
    total = len(df)
    likes = len(df[df["feedback_value"] == 1])
    dislikes = len(df[df["feedback_value"] == -1])
    comments = df["comment"].notna().sum()

    avg_score = df["match_score"].dropna().mean() if "match_score" in df else 0
    avg_score_likes = df.loc[df["feedback_value"] == 1, "match_score"].mean()

    # Feedbacks der letzten 7 Tage
    df["timestamp"] = pd.to_datetime(df["timestamp"], errors="coerce")
    last_week = df[df["timestamp"] > datetime.now() - timedelta(days=7)]
    last_week_count = len(last_week)

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Gesamt-Feedbacks", total)
    col2.metric("👍 Interessant", likes)
    col3.metric("👎 Nicht passend", dislikes)
    col4.metric("💬 Mit Kommentar", comments)
    col5.metric("Ø Match-Score", f"{avg_score:.2f}")
    col6.metric("Ø Score (Likes)", f"{avg_score_likes:.2f}")

    st.markdown("---")

    # --------------------------------------------------
    # Feedback-Verteilung
    # --------------------------------------------------
    st.subheader("🎯 Feedback-Verteilung & Score-Entwicklung")

    fig_pie = px.pie(
        names=["Interessant", "Nicht passend"],
        values=[likes, dislikes],
        color=["Interessant", "Nicht passend"],
        color_discrete_map={"Interessant": "green", "Nicht passend": "red"},
        hole=0.3,
        title="Verhältnis Likes zu Dislikes"
    )
    st.plotly_chart(fig_pie, use_container_width=True)

    # --------------------------------------------------
    # Score-Trends
    # --------------------------------------------------
    st.subheader("📈 Verlauf der vergebenen Scores")

    df_trend = df.dropna(subset=["match_score"])
    df_trend = df_trend.sort_values("timestamp")

    if not df_trend.empty:
        df_trend["color"] = df_trend["feedback_value"].map({
            1: "Interessant",
            -1: "Nicht passend"
        })
        fig_line = px.line(
            df_trend,
            x="timestamp",
            y="match_score",
            color="color",
            markers=True,
            title="Match-Score Verlauf",
            labels={"timestamp": "Datum", "match_score": "Match-Score", "color": "Feedback"}
        )
        st.plotly_chart(fig_line, use_container_width=True)
    else:
        st.caption("Noch keine Scores vorhanden.")

    # --------------------------------------------------
    # Top Rollen / Skills (erste Version)
    # --------------------------------------------------
    st.subheader("💡 Rollen mit besten Scores")
    top_roles = (
        df.groupby("title")["match_score"]
        .mean()
        .sort_values(ascending=False)
        .reset_index()
        .head(10)
    )
    fig_roles = px.bar(
        top_roles,
        x="match_score",
        y="title",
        orientation="h",
        color="match_score",
        color_continuous_scale="Blues",
        title="Durchschnittlicher Score pro Jobtitel"
    )
    st.plotly_chart(fig_roles, use_container_width=True)

    # --------------------------------------------------
    # Detailtabelle
    # --------------------------------------------------
    st.subheader("📋 Detaillierte Feedbacks")
    st.dataframe(df[["timestamp", "title", "company", "feedback_value", "match_score", "comment"]],
                 use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("© 2025 KI Job & Karriere Assistent – Lernstatus & Scoreentwicklung.")