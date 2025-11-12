

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


# 📁 Projektübersicht – Job und Karriere Agent (Module 1 & 2)

## 🧩 Strukturübersicht
**Projektpfad:** `/Users/carsten/Documents/Projekt-DataScience/Projekt-M6-Job-Agent/`

---

## 📂 1. /app

### `app.py`
**Status:** vollständig überarbeitet  
**Zweck:** Haupt-Streamlit-Anwendung zur Multi-Profil-Jobrecherche  
**Änderungen & Inhalte:**
- Integration der Bundesagentur-API (BAJobSource)  
- Automatische Mehrprofil-Suche (Profile aus DB)  
- Anzeige von Jobdetails mit Beschreibung und BA-Link  
- **Neu:** Feedback-Logik (✅ Interessant / ❌ Nicht interessant)  
- **Neu:** Kommentarfeld pro Job → Speicherung in `feedback`  
- Direkte Speicherung neuer Jobs in `jobs`-Tabelle (via `ensure_job_exists()`)  
- Aufbau modular für spätere Integration weiterer Quellen (Google Jobs etc.)

---

## 📂 2. /src

### `ba_source.py`
**Status:** überarbeitet  
**Zweck:** Zugriff auf API der Bundesagentur für Arbeit  
**Änderungen & Inhalte:**
- Klasse `BAJobSource` implementiert  
- `search()` liefert strukturierte Jobdaten (`titel`, `arbeitgeber`, `ort`, `refnr`)  
- `get_details()` ruft Detailinformationen über `/jobdetails/{refnr}` ab  
- **Neu:** Korrekte URL-Generierung zur öffentlichen BA-Seite  
- Rückgabe von Beschreibung + vollständiger Job-URL  

---

### `ba_classification.py`
**Status:** optionales Modul  
**Zweck:** Vorbereitung für Klassifikations-API (BA Berufe)  
**Änderung:** Platzhalter für optionale Begriffsanreicherung durch API  
→ Integration in `app.py`, aber derzeit nur rudimentär genutzt  

---

### `db_manager.py`
**Status:** stark erweitert  
**Zweck:** Verwaltung aller DB-Operationen (Jobs, Feedback, Struktur)  
**Änderungen & Inhalte:**
- **Neu:** `ensure_job_exists(job)` → legt Jobs an, falls nicht vorhanden  
- **Neu:** `save_feedback()` → Feedback + Kommentar speichern  
- `setup_jobs_table()` & `setup_feedback_table()` prüfen Tabellenexistenz  
- `save_jobs_to_db()` angepasst (Referenzen: `profile_id`, `user_profile_id`)  
- Einheitliche DB-Verbindung via `DB_PATH`  
- Konsolenlogs für Nachvollziehbarkeit (`[DB]`, `[Feedback]`, `[Jobs]`)  

---

### `ba_utils.py`
**Status:** Hilfsmodul (bestehender Code, teils erweitert)  
**Zweck:** Enthält `resolve_job_title_to_code()` und weitere Mapping-Funktionen  
**Anpassung:** Unterstützung für Begriffsnormalisierung (z. B. „Bürokaufmann“)  

---

## 📂 3. /data

### `career_agent.db`
**Status:** erweitert  
**Neue Tabellen / Felder:**
- `feedback` → Speicherung von Bewertungen & Kommentaren  
- `jobs` → ergänzt um `user_profile_id`, `matched_profile_id`, `match_score`  
**Zweck:** zentrale Datenbasis für alle Agenten (Research, Feedback, Writer)

---

## 📂 4. /Dokumentation

### `NvS-Job-und-Karriere-Agent.docx`
**Zweck:** Nachvollziehbarkeitsstruktur für Module 1 & 2  
**Inhalt:**  
- Zielsetzung, Methodik, Umsetzung, Ergebnisse, Ausblick  

### `CAT-Job-und-Karriere-Agent.docx`
**Zweck:** Kritische Reflexion (Critical Appraisal Template)  
**Inhalt:**  
- Bewertung der Zielerreichung, Herausforderungen, Lerneffekte  

---

## 🧱 Zusammenfassung – Erreichte Meilensteine

| Bereich | Ergebnis |
|----------|-----------|
| **Modul 1 – Datenbasis** | DB-Struktur, Basisklassen, Importfunktionen fertiggestellt |
| **Modul 2 – Research Agent** | Multi-Profil-Suche, Streamlit-Interface, Feedback-Mechanik implementiert |
| **Feedback-Verknüpfung** | Jobs + Feedback verlinkt über `job_id` |
| **Dokumentation** | NvS und CAT erstellt (konzeptuelle Ebene) |

---

## 🚀 Nächster Schritt
**Start Modul 3: Feedback-Logik**  
Ziel: Auswertung der Feedback-Daten, Visualisierung (z. B. in Streamlit) und Vorbereitung auf Lernkomponenten.

---