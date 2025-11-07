import sqlite3
from pathlib import Path

# Pfad zur Datenbank (anpassen falls nötig)
DB_PATH = Path("data/career_agent.db")
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

def create_tables():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # 1️⃣ Jobs
    cur.execute("""
    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        company TEXT,
        location TEXT,
        description TEXT,
        url TEXT,
        source TEXT,
        fit_score REAL DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2️⃣ Applications
    cur.execute("""
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER REFERENCES jobs(id),
        profile_id INTEGER REFERENCES user_profile(id),
        resume_id INTEGER REFERENCES resumes(id),
        date_created DATETIME DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'offen',
        notes TEXT,
        letter_path TEXT
    );
    """)

    # 3️⃣ Feedback
    cur.execute("""
    CREATE TABLE IF NOT EXISTS feedback (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER REFERENCES jobs(id),
        rating INTEGER,
        comment TEXT,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 4️⃣ User Profile
    cur.execute("""
    CREATE TABLE IF NOT EXISTS user_profile (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        profession TEXT,
        skills TEXT,
        experience TEXT,
        summary TEXT,
        region TEXT,
        preferences_json TEXT,
        embedding BLOB,
        is_active INTEGER DEFAULT 0,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5️⃣ Resumes
    cur.execute("""
    CREATE TABLE IF NOT EXISTS resumes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        file_path TEXT,
        content_text TEXT,
        embedding BLOB,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    """)

    conn.commit()
    conn.close()
    print("✅ Datenbanktabellen erfolgreich erstellt oder aktualisiert.")


if __name__ == "__main__":
    create_tables()