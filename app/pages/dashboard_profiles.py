import streamlit as st
import pandas as pd
import sqlite3
from pathlib import Path
import plotly.express as px

DB_PATH = Path(__file__).resolve().parents[2] / "data" / "career_agent.db"

# --------------------------------------------------
# Daten laden
# --------------------------------------------------
def load_profile_feedback():
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT 
            p.id AS profile_id,
            p.name AS profile_name,
            f.feedback_value,
            f.match_score,
            f.comment,
            f.timestamp,
            j.title,
            j.company,
            j.location
        FROM profiles p
        LEFT JOIN feedback f ON f.profile_id = p.id
        LEFT JOIN jobs j ON f.job_id = j.id
        ORDER BY f.timestamp DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


def summarize_by_profile(df):
    """Aggregiert Likes, Dislikes und Durchschnitts-Scores je Profil."""
    agg = (
        df.groupby(["profile_id", "profile_name"], dropna=False)
        .agg(
            feedbacks=("feedback_value", "count"),
            likes=("feedback_value", lambda x: (x == 1).sum()),
            dislikes=("feedback_value", lambda x: (x == -1).sum()),
            avg_score=("match_score", "mean"),
        )
        .reset_index()
        .sort_values("avg_score", ascending=False)
    )
    agg["avg_score"] = agg["avg_score"].round(2)
    return agg


# --------------------------------------------------
# Hauptanzeige
# --------------------------------------------------
def render():
    st.title("👤 Profil-Übersicht & Job-Portfolio")
    st.caption("Vergleicht deine Profile nach Erfolg, Bewertung und Lernstatus.")

    df = load_profile_feedback()
    if df.empty:
        st.info("Noch keine Feedbackdaten vorhanden.")
        return

    agg = summarize_by_profile(df)

    # --------------------------------------------------
    # 1️⃣ Überblick pro Profil
    # --------------------------------------------------
    st.subheader("📈 Übersicht je Profil")
    st.dataframe(
        agg.rename(
            columns={
                "profile_name": "Profilname",
                "feedbacks": "Bewertungen",
                "likes": "👍",
                "dislikes": "👎",
                "avg_score": "Ø Match-Score",
            }
        ),
        use_container_width=True,
        hide_index=True,
    )

    # Balkendiagramm
    st.subheader("🔹 Durchschnittliche Match-Scores pro Profil")
    fig = px.bar(
        agg,
        x="profile_name",
        y="avg_score",
        text="avg_score",
        color="avg_score",
        color_continuous_scale=["red", "yellow", "green"],
        title="Ø Score-Vergleich deiner Profile",
        labels={"profile_name": "Profil", "avg_score": "Ø Match-Score"},
    )
    fig.update_traces(textposition="outside")
    st.plotly_chart(fig, use_container_width=True)

    # --------------------------------------------------
    # 2️⃣ Detailansicht: Jobs je Profil
    # --------------------------------------------------
    st.subheader("🗂️ Details zu einzelnen Profilen")
    selected_profile = st.selectbox(
        "Profil auswählen:", agg["profile_name"].tolist()
    )

    df_sel = df[df["profile_name"] == selected_profile]

    if df_sel.empty:
        st.warning("Keine Jobs für dieses Profil gefunden.")
        return

    # Filter nach Feedbacktyp
    feedback_filter = st.radio(
        "Filter:",
        ["Alle", "Nur Interessant", "Nur Nicht passend"],
        horizontal=True,
    )
    if feedback_filter == "Nur Interessant":
        df_sel = df_sel[df_sel["feedback_value"] == 1]
    elif feedback_filter == "Nur Nicht passend":
        df_sel = df_sel[df_sel["feedback_value"] == -1]

    st.dataframe(
        df_sel[
            ["timestamp", "title", "company", "location", "match_score", "comment"]
        ].sort_values("timestamp", ascending=False),
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------
    # 3️⃣ Kleine Insights
    # --------------------------------------------------
    st.markdown("---")
    avg_profile_score = df_sel["match_score"].mean().round(2)
    st.metric(f"Ø Score für '{selected_profile}'", f"{avg_profile_score:.2f}")

    top_company = (
        df_sel[df_sel["feedback_value"] == 1]["company"]
        .value_counts()
        .head(1)
        .index.tolist()
    )
    if top_company:
        st.caption(f"🏢 Top-Arbeitgeber (nach Likes): **{top_company[0]}**")

    st.caption("💡 Tipp: Dieses Profil kannst du im Writer-Agent gezielt für Bewerbungen nutzen.")