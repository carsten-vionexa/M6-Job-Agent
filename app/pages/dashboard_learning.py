import streamlit as st
import sqlite3
import pandas as pd
import plotly.express as px
from datetime import datetime

# --------------------------------------------------
# Daten laden
# --------------------------------------------------
def load_learning_data(db_path="data/career_agent.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("""
        SELECT 
            f.id AS feedback_id,
            f.profile_id,
            f.feedback_value,
            f.match_score,
            f.base_score,
            f.feedback_score,
            f.comment,
            f.timestamp,
            p.name AS profile_name,
            j.title AS job_title,
            j.company AS company
        FROM feedback f
        LEFT JOIN profiles p ON f.profile_id = p.id
        LEFT JOIN jobs j ON f.job_id = j.id
        ORDER BY f.timestamp DESC
    """, conn)
    conn.close()

    # NaN-Werte ersetzen
    for col in ["base_score", "feedback_score", "match_score"]:
        if col in df.columns:
            df[col] = df[col].fillna(0.0)

    # Delta berechnen
    df["delta_score"] = df["feedback_score"] - df["base_score"]
    df = df[df["timestamp"].notna()]
    return df


# --------------------------------------------------
# Render
# --------------------------------------------------
def render():
    st.title("🧠 Lernanalyse & Score-Anpassung")
    st.caption("Hier siehst du, wie dein Feedback das System verändert hat – "
               "je größer die Differenz, desto stärker der Lerneffekt.")

    df = load_learning_data()

    if df.empty:
        st.info("Noch keine Feedbackdaten vorhanden.")
        return

    # --------------------------------------------------
    # Kennzahlen
    # --------------------------------------------------
    st.subheader("📊 Überblick")

    total = len(df)
    improved = len(df[df["delta_score"] > 0.05])
    worsened = len(df[df["delta_score"] < -0.05])
    neutral = total - improved - worsened
    avg_delta = df["delta_score"].mean()

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Gesamtbewertungen", total)
    col2.metric("📈 Verbesserte Scores", improved)
    col3.metric("📉 Verschlechterte Scores", worsened)
    col4.metric("Ø Delta", f"{avg_delta:.3f}")

    st.markdown("---")

    # --------------------------------------------------
    # Scatterplot: BaseScore vs FeedbackScore
    # --------------------------------------------------
    st.subheader("🎯 Vergleich: BaseScore vs. FeedbackScore")

    fig_scatter = px.scatter(
        df,
        x="base_score",
        y="feedback_score",
        color="delta_score",
        hover_data=["job_title", "company", "profile_name", "comment"],
        color_continuous_scale=["red", "grey", "green"],
        title="BaseScore (System) vs. FeedbackScore (dein Urteil)",
        labels={
            "base_score": "Systembewertung",
            "feedback_score": "Deine Bewertung",
            "delta_score": "Abweichung"
        }
    )
    fig_scatter.add_shape(
        type="line",
        x0=0, y0=0, x1=1, y1=1,
        line=dict(color="black", dash="dot")
    )
    st.plotly_chart(fig_scatter, use_container_width=True)

    # --------------------------------------------------
    # Lernentwicklung über Zeit
    # --------------------------------------------------
    st.subheader("⏱️ Lernentwicklung über Zeit")

    df_sorted = df.sort_values("timestamp")
    if not df_sorted.empty:
        df_sorted["rolling_delta"] = df_sorted["delta_score"].rolling(window=5, min_periods=1).mean()

        fig_trend = px.line(
            df_sorted,
            x="timestamp",
            y="rolling_delta",
            color="profile_name",
            markers=True,
            title="Verlauf der durchschnittlichen Score-Abweichung (gleitend)",
            labels={"rolling_delta": "Ø Delta (5 Werte)"}
        )
        st.plotly_chart(fig_trend, use_container_width=True)
    else:
        st.caption("Noch keine Zeitreihe verfügbar.")

    # --------------------------------------------------
    # Tabelle
    # --------------------------------------------------
    st.subheader("📋 Detailtabelle (letzte Bewertungen)")
    show_cols = ["timestamp", "profile_name", "job_title", "base_score", "feedback_score", "delta_score", "feedback_value", "comment"]
    st.dataframe(df[show_cols], use_container_width=True, hide_index=True)

    st.markdown("---")
    st.caption("Grün = du hast höher bewertet als das System. Rot = du hast niedriger bewertet. "
               "Grau = kaum Unterschied → System schätzt dich bereits gut ein.")