#!/usr/bin/env python3
import asyncio
import sqlite3
from urllib.parse import urljoin
from playwright.async_api import async_playwright
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


def get_jobs_for_overwrite(limit: int = 10):
    """Holt beliebige Jobs aus der DB, um deren description-Feld zu überschreiben."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, url FROM jobs LIMIT ?", (limit,))
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

        # 1️⃣ Versuche externen Detail-Link zu finden
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

        # 2️⃣ Wenn externer Link gefunden → dorthin wechseln
        if external_link:
            print(f"🌐 Externer Detail-Link gefunden: {external_link}")
            await page.goto(external_link, timeout=60000)
            await page.wait_for_timeout(4000)
            html = await page.content()
            await browser.close()
            return html

        # 3️⃣ Kein externer Link → Beschreibung direkt auf der Arbeitsagentur-Seite suchen
        print("📄 Verwende Arbeitsagentur-Detailseite als Quelle.")
        try:
            # Typische Container für den Beschreibungstext
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

