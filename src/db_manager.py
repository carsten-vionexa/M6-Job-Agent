import sqlite3
from datetime import datetime

# --------------------------------------------------
# Schema-Migration (führt sich beim App-Start einmal aus)
# --------------------------------------------------
def migrate_schema(db_path="data/career_agent.db"):
    """Stellt sicher, dass alle benötigten Spalten existieren."""
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    def col_exists(table, col):
        cur.execute(f"PRAGMA table_info({table});")
        return any(r[1] == col for r in cur.fetchall())

    # --- Tabelle jobs ---
    if not col_exists("jobs", "match_score"):
        cur.execute("ALTER TABLE jobs ADD COLUMN match_score REAL;")
    if not col_exists("jobs", "matched_profile_id"):
        cur.execute("ALTER TABLE jobs ADD COLUMN matched_profile_id INTEGER REFERENCES profiles(id);")
    if not col_exists("jobs", "obsolete_user_profile_id"):
        cur.execute("ALTER TABLE jobs ADD COLUMN obsolete_user_profile_id INTEGER;")
    if not col_exists("jobs", "refnr"):
        cur.execute("ALTER TABLE jobs ADD COLUMN refnr TEXT;")
    if not col_exists("jobs", "date_posted"):
        cur.execute("ALTER TABLE jobs ADD COLUMN date_posted TEXT;")

    # --- Tabelle feedback ---
    if not col_exists("feedback", "match_score"):
        cur.execute("ALTER TABLE feedback ADD COLUMN match_score REAL;")
    if not col_exists("feedback", "comment"):
        cur.execute("ALTER TABLE feedback ADD COLUMN comment TEXT;")

    conn.commit()
    conn.close()


# --------------------------------------------------
# Jobverwaltung
# --------------------------------------------------
def ensure_job_exists(job, matched_profile_id=None, match_score=None, db_path="data/career_agent.db"):
    """
    Legt einen Job an oder aktualisiert ihn.
    Schreibt refnr und date_posted mit.
    Gibt job_id zurück.
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    title = (job.get("titel") or "").strip()
    company = (job.get("arbeitgeber") or "").strip()
    location = (job.get("ort") or "").strip()
    description = job.get("beschreibung") or ""
    source = job.get("source") or ""
    url = job.get("url") or ""
    refnr = (job.get("refnr") or None)
    # Falls BA kein Datum liefert, auf „heute“ fallen
    date_posted = job.get("date_posted") or datetime.now().strftime("%Y-%m-%d")

    # 1) Existenzprüfung – bevorzugt über refnr, sonst über (title, company, location)
    row = None
    if refnr:
        cur.execute("SELECT id FROM jobs WHERE refnr = ?", (refnr,))
        row = cur.fetchone()
    if not row:
        cur.execute(
            "SELECT id FROM jobs WHERE title = ? AND company = ? AND location = ?",
            (title, company, location),
        )
        row = cur.fetchone()

    # 2) Update / Insert
    if row:
        job_id = row[0]
        cur.execute(
            """
            UPDATE jobs SET
                title = COALESCE(?, title),
                company = COALESCE(?, company),
                location = COALESCE(?, location),
                description = COALESCE(?, description),
                source = COALESCE(?, source),
                url = COALESCE(?, url),
                refnr = COALESCE(?, refnr),
                date_posted = COALESCE(?, date_posted),
                matched_profile_id = COALESCE(?, matched_profile_id),
                match_score = CASE WHEN ? IS NOT NULL THEN ? ELSE match_score END
            WHERE id = ?
            """,
            (
                title, company, location, description, source, url,
                refnr, date_posted, matched_profile_id,
                match_score, match_score,
                job_id,
            ),
        )
    else:
        cur.execute(
            """
            INSERT INTO jobs
                (title, company, location, description, source, url, refnr, date_posted, matched_profile_id, match_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title, company, location, description, source, url,
                refnr, date_posted, matched_profile_id, match_score,
            ),
        )
        job_id = cur.lastrowid

    conn.commit()
    conn.close()
    return job_id


# --------------------------------------------------
# Feedbackverwaltung
# --------------------------------------------------
def save_feedback(job_id, profile_id, feedback_value=None, comment=None, match_score=None, db_path="data/career_agent.db"):
    """
    Speichert Feedback mit optionalem Kommentar und Score.
    Falls für (job_id, profile_id) bereits Feedback existiert, wird es aktualisiert.
    - feedback_value: 1 (Like), -1 (Dislike), None (Kommentar)
    - match_score: aktueller Score des Jobs beim Speichern
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Prüfen, ob schon Feedback existiert (gleicher Job + Profil)
        cur.execute(
            "SELECT id, feedback_value, comment FROM feedback WHERE job_id=? AND profile_id=? ORDER BY timestamp DESC LIMIT 1",
            (job_id, profile_id),
        )
        row = cur.fetchone()

        if row:
            feedback_id = row[0]
            existing_value, existing_comment = row[1], row[2]

            # Falls noch kein Like/Dislike gesetzt wurde, aber jetzt eins kommt → übernehmen
            new_value = feedback_value if feedback_value is not None else existing_value
            # Falls bereits Kommentar vorhanden → erweitern oder ersetzen
            new_comment = comment if comment else existing_comment

            cur.execute(
                """
                UPDATE feedback
                SET feedback_value = ?, comment = ?, match_score = ?, timestamp = ?
                WHERE id = ?
                """,
                (new_value, new_comment, match_score, ts, feedback_id),
            )
        else:
            # Kein bestehendes Feedback → neuer Eintrag
            cur.execute(
                """
                INSERT INTO feedback (job_id, profile_id, feedback_value, comment, match_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (job_id, profile_id, feedback_value, comment, match_score, ts),
            )

        conn.commit()
        conn.close()
        return True

    except Exception as e:
        print("⚠️ Fehler beim Speichern des Feedbacks:", e)
        return False


# --------------------------------------------------
# Hilfsfunktionen zum Laden (optional für Analysen)
# --------------------------------------------------
def load_feedback_for_profile(profile_id, db_path="data/career_agent.db"):
    """Lädt Feedback-Einträge für ein Profil."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM feedback WHERE profile_id = ? ORDER BY timestamp DESC;", (profile_id,))
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


def load_jobs_with_feedback(db_path="data/career_agent.db"):
    """Lädt Jobs mit Feedback-Zusammenhang (Join)."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        """
        SELECT j.id AS job_id, j.title, j.company, j.location, j.match_score,
               f.feedback_value, f.match_score AS feedback_score, f.comment, f.timestamp
        FROM jobs j
        LEFT JOIN feedback f ON j.id = f.job_id
        ORDER BY f.timestamp DESC
        """
    )
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]