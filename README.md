

## Übersicht Dateien

# src/ingest_resumes.py
Das Skript importiert alle vorhandenen Profilbeschreibungen und Lebensläufe (DOCX-Dateien) in die SQLite-Datenbank career_agent.db und verknüpft sie miteinander.
Damit bildet es die Datenbasis für das Profil-Matching im Projekt (Modul 1).#


# src/models/base_classes.py
	•	Diese Klassen spiegeln deine Tabellen 1:1 wider → leichter für RAG-, CrewAI- und Streamlit-Module.
	•	Später können wir aus ihnen leicht ein ORM-ähnliches Layer oder Pydantic-Schemas für APIs ableiten.
	•	In Modul 2 brauchst du sie für:
	•	Matching-Agent (Job ↔ ApplicantProfile)
	•	Writer-Agent (verwendet ApplicantProfile.resume_id)
	•	Feedback-Agent (schreibt Bewertungen in Feedback-Tabelle)

# src/models/load_from_db.py
Dieses Modul stellt schlanke Loader-Funktionen bereit, die aus der SQLite-DB Datensätze lesen und als Python-Objekte (Job, ApplicantProfile, Feedback) zurückgeben.

# Dateien: models (bestehend aus base_classes.Feedback & load_from_db.save_feedback)
Diese Komponente verwaltet alle Rückmeldungen (Feedback) zu Job-Profil-Zuordnungen.
Sie dient sowohl der manuellen Bewertung (z. B. nach einer Jobprüfung) als auch der automatischen Rückmeldung aus dem Matching- oder Writer-Agent.
Feedback-Einträge dokumentieren, wie gut ein Profil oder Lebenslauf zu einer Stellenausschreibung passt.

Klassendefinition:
Feedback (in models/base_classes.py)
repräsentiert einen einzelnen Feedback-Eintrag mit Hilfsmethode label(),
die eine einfache verbale Einschätzung basierend auf dem numerischen Wert liefert.

Funktion:
save_feedback() (in models/load_from_db.py)
speichert neue Feedback-Einträge in der SQLite-Datenbank

Ergebnis:
Nach Ausführung sind alle Rückmeldungen in der Tabelle feedback gespeichert und können
– über Streamlit, Agenten oder direkt per SQL – ausgewertet oder angezeigt werden.