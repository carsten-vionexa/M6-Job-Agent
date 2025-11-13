#!/usr/bin/env python3
import asyncio
import sqlite3
from urllib.parse import urljoin
from pathlib import Path
from playwright.async_api import async_playwright
from openai import OpenAI

# ---------------------------------------------------------------------
# 🔧 Setup
# ---------------------------------------------------------------------
client = OpenAI()
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "career_agent.db"

print(f"📁 Datenbankpfad: {DB_PATH}")


# ---------------------------------------------------------------------
# 🧱 Hilfsfunktionen
# ---------------------------------------------------------------------
async def fetch_html(url: str) -> str:
    """
    Öffnet eine Arbeitsagentur- oder externe Jobseite und gibt den HTML-Quelltext zurück.
    Erkennt automatisch, ob ein externer Link existiert.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(4000)

        # 1️⃣ Externen Detail-Link finden
        anchors = await page.query_selector_all("a[href]")
        external_link = None
        for a in anchors:
            href = await a.get_attribute("href")
            if not href:
                continue
            abs_href = urljoin(page.url, href)
            if (
                abs_href.startswith("http")
                and "arbeitsagentur.de" not in abs_href
                and "/stelle/detail/" in abs_href
            ):
                external_link = abs_href
                break

        # 2️⃣ Wenn externer Link existiert → dorthin wechseln
        if external_link:
            print(f"🌐 Externer Detail-Link gefunden: {external_link}")
            await page.goto(external_link, timeout=60000)
            await page.wait_for_timeout(4000)
            html = await page.content()
            await browser.close()
            return html

        # 3️⃣ Kein externer Link → Text auf Arbeitsagentur-Seite selbst holen
        print("📄 Verwende Arbeitsagentur-Detailseite als Quelle.")
        try:
            desc_div = await page.query_selector("div[data-cy='job-detail-description']")
            if not desc_div:
                desc_div = await page.query_selector("div.ba-jobad-section")

            if desc_div:
                inner_html = await desc_div.inner_html()
            else:
                inner_html = await page.content()

        except Exception:
            inner_html = await page.content()

        await browser.close()
        return inner_html


def summarize_job_html(raw_html: str) -> str:
    """
    Übergibt den HTML-Text an GPT, um die eigentliche Stellenbeschreibung
    (Titel, Aufgaben, Profil etc.) zu extrahieren.
    """
    prompt = f"""
    Extrahiere aus dem folgenden HTML die eigentliche Stellenbeschreibung.
    Gib sie in klarer, gegliederter Form zurück:

    - Jobtitel
    - Aufgaben / Tätigkeiten
    - Anforderungen / Qualifikationen
    - ggf. Vorteile oder Benefits

    Entferne Navigation, Cookies, Werbung, Footer usw.

    HTML:
    {raw_html[:15000]}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Du bist ein präziser Extraktionsagent für Jobbeschreibungen."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.2,
    )
    return response.choices[0].message.content.strip()


def update_job_description(job_id: int, description: str):
    """Überschreibt das description-Feld für einen Job."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE jobs SET description = ? WHERE id = ?", (description, job_id))
    conn.commit()
    conn.close()


def get_faulty_jobs(limit: int = 10):
    """
    Liefert alle Jobs, deren Beschreibung fehlerhafte Platzhaltertexte enthält.
    """
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        SELECT id, url FROM jobs
        WHERE description LIKE 'Es scheint%%'
           OR description LIKE 'Keine Detailbeschreibung%%'
        LIMIT ?;
    """, (limit,))
    jobs = cur.fetchall()
    conn.close()
    return jobs


# ---------------------------------------------------------------------
# 🚀 Hauptprozess
# ---------------------------------------------------------------------
async def process_faulty_jobs(limit: int = 10):
    jobs = get_faulty_jobs(limit)
    if not jobs:
        print("🎉 Keine fehlerhaften Einträge gefunden.")
        return

    total = len(jobs)
    print(f"\n🔧 Starte Korrekturlauf ({total} fehlerhafte Jobs)...\n")

    for i, (job_id, url) in enumerate(jobs, start=1):
        print(f"({i}/{total}) Korrigiere Job {job_id} ...")
        try:
            html = await fetch_html(url)
            desc = summarize_job_html(html)
            update_job_description(job_id, desc)
            print(f"✅ Beschreibung für Job {job_id} aktualisiert.")
        except Exception as e:
            print(f"❌ Fehler bei Job {job_id}: {e}")

    print("\n🎯 Korrekturlauf abgeschlossen.")


# ---------------------------------------------------------------------
# 🧭 Main
# ---------------------------------------------------------------------
if __name__ == "__main__":
    asyncio.run(process_faulty_jobs(limit=10))