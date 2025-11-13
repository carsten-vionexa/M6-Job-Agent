#!/usr/bin/env python3
import asyncio
import sqlite3
from urllib.parse import urljoin
from playwright.async_api import async_playwright

from pathlib import Path
from openai import OpenAI

from pathlib import Path
from openai import OpenAI

client = OpenAI()

# 🔹 Absoluter Pfad zur SQLite-Datenbank (eine Ebene über /scraper)
BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "data" / "career_agent.db"

print(f"📁 Datenbankpfad: {DB_PATH}")



# --- Core: Seite abrufen -------------------------------------------------------
async def fetch_html(url: str) -> str:
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(4000)

        # Suche nach externem Detail-Link
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

        if external_link:
            print(f"🌐 Externer Detail-Link gefunden: {external_link}")
            await page.goto(external_link, timeout=60000)
            await page.wait_for_timeout(4000)

        html = await page.content()
        await browser.close()
        return html


# --- Core: LLM-Extraktion ------------------------------------------------------
def summarize_job_html(raw_html: str) -> str:
    prompt = f"""
    Extrahiere aus dem folgenden HTML die eigentliche Stellenbeschreibung.
    Gib sie in strukturiertem Klartext zurück:

    - Jobtitel
    - Aufgaben / Tätigkeiten
    - Anforderungen / Qualifikationen
    - ggf. Vorteile oder Benefits

    Entferne Navigation, Footer, Cookies, Werbung.

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


# --- DB-Update -----------------------------------------------------------------
def update_job_description(job_id: int, description: str):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("UPDATE jobs SET description = ? WHERE id = ?", (description, job_id))
    conn.commit()
    conn.close()


def get_jobs_without_description(limit: int = 10):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, url FROM jobs WHERE description IS NULL LIMIT ?", (limit,))
    jobs = cur.fetchall()
    conn.close()
    return jobs


# --- Pipeline -----------------------------------------------------------------
async def process_single_job(job_id: int, url: str):
    print(f"\n🔍 Verarbeite Job {job_id} ...")
    try:
        html = await fetch_html(url)
        desc = summarize_job_html(html)
        update_job_description(job_id, desc)
        print(f"✅ Beschreibung gespeichert ({len(desc)} Zeichen).")
    except Exception as e:
        print(f"❌ Fehler bei Job {job_id}: {e}")


async def process_batch_jobs(limit: int = 10):
    jobs = get_jobs_without_description(limit)
    if not jobs:
        print("Keine offenen Jobs ohne Beschreibung gefunden.")
        return

    total = len(jobs)
    print(f"\n🚀 Starte Batch-Verarbeitung ({total} Jobs)...\n")

    for i, (job_id, url) in enumerate(jobs, start=1):
        print(f"({i}/{total})")
        await process_single_job(job_id, url)

    print("\n🎯 Batch abgeschlossen.")


# --- Main ---------------------------------------------------------------------
if __name__ == "__main__":
    # 🔹 Option A: Einzeltest (kommentieren, falls Batchlauf gewünscht)
    # test_url = "https://www.arbeitsagentur.de/jobsuche/suche?id=12964-JOBSOL40873-S&angebotsart=1"
    # asyncio.run(process_single_job(999, test_url))

    # 🔹 Option B: Batchlauf
    asyncio.run(process_batch_jobs(limit=10))