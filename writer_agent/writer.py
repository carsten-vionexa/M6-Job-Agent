#!/usr/bin/env python3
from openai import OpenAI
from pathlib import Path
from docx import Document
from datetime import datetime

client = OpenAI()


def generate_cover_letter(job_title, company, job_description, profile_summary, cv_text):
    """
    Erstellt ein vollständiges Bewerbungsschreiben mit GPT.
    """

    prompt = f"""
    Erstelle ein professionelles Bewerbungsschreiben für folgende Stelle:

    Jobtitel: {job_title}
    Unternehmen: {company}

    >>> Stellenbeschreibung:
    {job_description}

    >>> Profil:
    {profile_summary}

    >>> Lebenslauf:
    {cv_text}

    Anforderungen:
    - Klare Struktur
    - Höflicher, professioneller Ton
    - Bezug zur Jobbeschreibung
    - 400 bis 600 Wörter
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Du schreibst professionelle Bewerbungsanschreiben."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1400,
        temperature=0.4,
    )

    return response.choices[0].message.content.strip()


def save_as_word(text, job_title, company, folder="documents/applications"):
    """
    Speichert das Anschreiben als Word (.docx)
    """

    Path(folder).mkdir(parents=True, exist_ok=True)

    safe_company = company.lower().replace(" ", "_")
    safe_title = job_title.lower().replace(" ", "_")
    date = datetime.now().strftime("%Y-%m-%d")

    filename = f"bewerbung_{safe_company}_{safe_title}_{date}.docx"
    path = Path(folder) / filename

    doc = Document()
    for line in text.split("\n"):
        doc.add_paragraph(line.strip())
    doc.save(path)

    return path