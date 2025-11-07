import sqlite3
from pathlib import Path

# === Datenbankpfad ===
DB_PATH = Path(__file__).resolve().parents[1] / "data" / "career_agent.db"

def create_connection():
    """Erstellt eine Verbindung zur SQLite-Datenbank."""
    conn = sqlite3.connect(DB_PATH)
    return conn

def init_db():
    """Erstellt alle benötigten Tabellen, falls sie noch nicht existieren."""
    conn = create_connection()
    cur = conn.cursor()

    # Tabelle: Jobs (Recherche-Ergebnisse oder API-Importe)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        description TEXT,
        source TEXT,
        url TEXT,
        date_posted TEXT
    );
    """)

    # Tabelle: Bewerbungen (generierte Anschreiben)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        filename TEXT,
        date_created TEXT,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );
    """)

    # Tabelle: Nutzerprofil (z. B. für Anschreibenerstellung)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        profession TEXT,
        skills TEXT,
        experience TEXT,
        preferences TEXT
    );
    """)

    # Tabelle: Feedback (Bewertungen von Vorschlägen)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER,
        feedback_value INTEGER CHECK (feedback_value IN (-1, 1)),
        timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (job_id) REFERENCES jobs(id)
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Datenbank erfolgreich initialisiert:", DB_PATH)

if __name__ == "__main__":
    init_db()