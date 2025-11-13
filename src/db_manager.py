import sqlite3
import json
from datetime import datetime
from models.embeddings import get_embedding


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
    if not col_exists("jobs", "external_id"):
        cur.execute("ALTER TABLE jobs ADD COLUMN external_id TEXT;")
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
    Gibt job_id zurück (legt Datensatz notfalls neu an).
    """
    conn = sqlite3.connect(db_path)
    cur = conn.cursor()

    # Felder tolerant zuordnen
    title = (job.get("title") or job.get("titel") or "").strip()
    company = (job.get("company") or job.get("arbeitgeber") or "").strip()
    location = (job.get("location") or job.get("ort") or "").strip()
    description = (job.get("description") or job.get("beschreibung") or "").strip()
    source = job.get("source") or ""
    url = job.get("url") or ""
    refnr = job.get("refnr") or job.get("external_id") or None
    external_id = job.get("external_id") or job.get("refnr") or None
    date_posted = job.get("date_posted") or datetime.now().strftime("%Y-%m-%d")

    print("\n=== ENSURE_JOB_EXISTS DEBUG ===")
    print(f"title={title}, company={company}, location={location}, refnr={refnr}, external_id={external_id}")

    # Prüfen, ob Job existiert (nach external_id oder refnr)
    row = None
    if external_id:
        cur.execute("SELECT id FROM jobs WHERE external_id = ?", (external_id,))
        row = cur.fetchone()
    if not row and refnr:
        cur.execute("SELECT id FROM jobs WHERE refnr = ?", (refnr,))
        row = cur.fetchone()
    if not row:
        cur.execute(
            "SELECT id FROM jobs WHERE title=? AND company=? AND location=?",
            (title, company, location),
        )
        row = cur.fetchone()

    if row:
        job_id = row[0]
        cur.execute(
            """
            UPDATE jobs
            SET title=?, company=?, location=?, description=?, source=?, url=?,
                refnr=?, external_id=?, date_posted=?, matched_profile_id=?, match_score=?
            WHERE id=?
            """,
            (
                title, company, location, description, source, url,
                refnr, external_id, date_posted, matched_profile_id, match_score, job_id
            ),
        )
        print(f"→ UPDATE Job-ID {job_id}")
    else:
        cur.execute(
            """
            INSERT INTO jobs
              (title, company, location, description, source, url, refnr, external_id,
               date_posted, matched_profile_id, match_score)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                title, company, location, description, source, url,
                refnr, external_id, date_posted, matched_profile_id, match_score
            ),
        )
        job_id = cur.lastrowid
        print(f"→ INSERT Job-ID {job_id}")

    conn.commit()

    # --------------------------------------------------
    # Embedding automatisch erzeugen, falls leer
    # --------------------------------------------------
    if description:
        cur.execute("SELECT embedding FROM jobs WHERE id = ?", (job_id,))
        row = cur.fetchone()
        if not row or not row[0]:
            try:
                emb = get_embedding(description)
                emb_json = json.dumps(emb.tolist())
                cur.execute("UPDATE jobs SET embedding=? WHERE id=?", (emb_json, job_id))
                conn.commit()
                print(f"🧠 Embedding erzeugt für Job-ID {job_id}")
            except Exception as e:
                print(f"⚠️ Embedding-Fehler bei Job {job_id}: {e}")
    else:
        print("⚠️ Kein Beschreibungstext – kein Embedding erzeugt.")

    conn.close()
    print("✅ Job gespeichert\n")
    return job_id


# --------------------------------------------------
# Feedbackverwaltung
# --------------------------------------------------
def save_feedback(
    job_id,
    profile_id,
    feedback_value=None,
    comment=None,
    match_score=None,
    base_score=None,
    feedback_score=None,
    db_path="data/career_agent.db"
):
    """
    Speichert Feedback mit optionalem Kommentar und Score.
    Falls für (job_id, profile_id) bereits Feedback existiert, wird es aktualisiert.
    - feedback_value: 1 (Like), -1 (Dislike), None (Kommentar)
    - match_score: aktueller Fit-Score
    - base_score: ursprünglicher Basisscore
    - feedback_score: tatsächliche Bewertung nach Feedback
    """
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        cur.execute(
            "SELECT id FROM feedback WHERE job_id=? AND profile_id=? ORDER BY timestamp DESC LIMIT 1",
            (job_id, profile_id),
        )
        row = cur.fetchone()

        if row:
            feedback_id = row[0]
            cur.execute(
                """
                UPDATE feedback
                SET feedback_value = ?,
                    comment = ?,
                    match_score = ?,
                    base_score = ?,
                    feedback_score = ?,
                    timestamp = ?
                WHERE id = ?
                """,
                (feedback_value, comment, match_score, base_score, feedback_score, ts, feedback_id),
            )
        else:
            cur.execute(
                """
                INSERT INTO feedback
                    (job_id, profile_id, feedback_value, comment,
                     match_score, base_score, feedback_score, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (job_id, profile_id, feedback_value, comment,
                 match_score, base_score, feedback_score, ts),
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