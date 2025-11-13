#!/usr/bin/env python3
from datetime import datetime
from docx import Document
from pathlib import Path
from openai import OpenAI

client = OpenAI()

# -----------------------------------------------------
# Writer-Agent: erzeugt ein vollständiges Anschreiben
# -----------------------------------------------------

def generate_cover_letter(job_title: str, company: str, job_description: str, profile_data: str, cv_text: str) -> str:
    """
    Nutzt das LLM, um ein vollständiges Bewerbungsschreiben zu erzeugen.
    """

    prompt = f"""
    Du bist ein professioneller Bewerbungsschreiber.

    Erstelle ein vollständiges, präzises, individuelles Bewerbungsschreiben 
    auf Grundlage folgender Informationen:

    Jobtitel: {job_title}
    Unternehmen: {company}

    >>> Jobbeschreibung:
    {job_description}

    >>> Bewerber-Profil:
    {profile_data}

    >>> Lebenslauf-Auszug:
    {cv_text}

    Anforderungen:
    - professioneller Ton
    - klare Struktur: Einleitung, Motivation, Fähigkeiten, Bezug zur Stelle, Schluss
    - maximal 500-600 Wörter
    - kein Marketing-Sprech, sondern authentisch und kompetent
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role":"system","content":"Du bist ein Experte für Bewerbungen."},
            {"role":"user","content":prompt}
        ],
        max_tokens=1200,
        temperature=0.4
    )

    return response.choices[0].message.content.strip()


# -----------------------------------------------------
# DOCX Export
# -----------------------------------------------------

def save_as_word(text: str, job_title: str, company: str, save_folder="documents/applications"):
    """
    Speichert das Anschreiben als Word-Dokument.
    """

    Path(save_folder).mkdir(parents=True, exist_ok=True)

    safe_company = company.lower().replace(" ", "_")
    safe_title   = job_title.lower().replace(" ", "_")
    date_str     = datetime.now().strftime("%Y-%m-%d")

    filename = f"bewerbung_{safe_company}_{safe_title}_{date_str}.docx"
    filepath = Path(save_folder) / filename

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)

    doc.save(filepath)

    return filepath


# -----------------------------------------------------
# Main-Funktion für manuelles Testen
# -----------------------------------------------------

if __name__ == "__main__":
    job_title = "Backoffice Mitarbeiter"
    company = "Bildungswerk Beispiel GmbH"
    job_desc = input("Jobbeschreibung einfügen:\n")
    profile  = "Erfahrener Büro- und Verwaltungsmitarbeiter mit Schwerpunkt Digitalisierung."
    cv_text  = "10 Jahre Erfahrung im Büro, CRM, Dokumentenmanagement etc."

    print("Generiere Anschreiben...")
    letter = generate_cover_letter(job_title, company, job_desc, profile, cv_text)

    file = save_as_word(letter, job_title, company)
    print("Gespeichert unter:", file)