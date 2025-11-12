import streamlit as st
from pathlib import Path
import sys

# --------------------------------------------------
# Pfadkorrektur (damit src & pages importierbar sind)
# --------------------------------------------------
ROOT_DIR = Path(__file__).resolve().parents[1]
PROJECT_ROOT = ROOT_DIR.parents[0]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

# --------------------------------------------------
# Seitenimporte
# --------------------------------------------------
from app.pages import (
    job_search,
    dashboard,
    dashboard_learning,
    dashboard_profiles
)

# Writer Agent ist optional (noch nicht implementiert)
try:
    from pages import writer_agent
except ImportError:
    writer_agent = None


# --------------------------------------------------
# Seitensetup
# --------------------------------------------------
st.set_page_config(
    page_title="KI Job & Karriere Assistent",
    page_icon="🧭",
    layout="wide",
    initial_sidebar_state="expanded"
)

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    print("🔄 App neu geladen")

# --------------------------------------------------
# Sidebar Navigation
# --------------------------------------------------
st.sidebar.title("🧭 Navigation")
st.sidebar.caption("Wähle eine Funktion des Assistenten:")

page = st.sidebar.radio(
    "Ansicht wählen:",
    ("Job-Suche", "Dashboard", "Lernanalyse", "Profile", "Writer Agent"),
    index=0
)

st.sidebar.markdown("---")
st.sidebar.info(
    "💡 Tipp: Im Dashboard siehst du Lernfortschritt und "
    "Feedback-Auswertungen deiner Job-Interaktionen."
)

# --------------------------------------------------
# Hauptbereich
# --------------------------------------------------
if page == "Job-Suche":
    job_search.render()

elif page == "Dashboard":
    dashboard.render()

elif page == "Lernanalyse":
    dashboard_learning.render()

elif page == "Profile":
    dashboard_profiles.render()

elif page == "Writer Agent":
    if writer_agent:
        writer_agent.render()
    else:
        st.info("Der Writer Agent ist noch nicht aktiviert.")

else:
    st.warning("Seite nicht gefunden.")

# --------------------------------------------------
# Fußbereich / Branding
# --------------------------------------------------
st.markdown("---")
st.caption("© 2025 KI Job & Karriere Assistent – entwickelt mit ❤️ in Python / Streamlit")