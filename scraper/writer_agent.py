#!/usr/bin/env python3
from datetime import datetime
from docx import Document
from pathlib import Path
from openai import OpenAI

client = OpenAI()


# -----------------------------------------------------
# 1. Bewerbungsschreiben generieren
# -----------------------------------------------------
def generate_cover_letter(job_title: str, company: str, job_description: str,
                          profile_data: str, cv_text: str) -> str:
    """
    Nutzt GPT, um ein vollständiges Bewerbungsschreiben zu erstellen.
    """
    prompt = f"""
    Schreibe ein vollständiges, professionelles Bewerbungsschreiben
    für die ausgeschriebene Position:

    Titel: {job_title}
    Unternehmen: {company}

    >>> Jobbeschreibung:
    {job_description}

    >>> Bewerberprofil:
    {profile_data}

    >>> Lebenslauf-Auszug:
    {cv_text}

    Anforderungen:
    - höflicher, kompetenter Ton
    - Einleitung, Motivation, Bezug zu Fähigkeiten, Schluss
    - ca 400-600 Wörter
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Du bist ein Experte für Bewerbungsanschreiben."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1200,
        temperature=0.3
    )

    return response.choices[0].message.content.strip()


# -----------------------------------------------------
# 2. Word-Datei speichern
# -----------------------------------------------------
def save_as_word(text: str, job_title: str, company: str,
                 save_folder="documents/applications"):
    """
    Speichert das erzeugte Anschreiben als Word-Dokument.
    """
    Path(save_folder).mkdir(parents=True, exist_ok=True)

    safe_company = company.lower().replace(" ", "_")
    safe_title = job_title.lower().replace(" ", "_")
    date_str = datetime.now().strftime("%Y-%m-%d")

    filename = f"bewerbung_{safe_company}_{safe_title}_{date_str}.docx"
    filepath = Path(save_folder) / filename

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line.strip())

    doc.save(filepath)

    return filepath