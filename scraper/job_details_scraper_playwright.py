#!/usr/bin/env python3

#job_details_scraper_playwright.py


import asyncio
from urllib.parse import urljoin, urlparse
from playwright.async_api import async_playwright


async def extract_job_description_playwright(job_url: str) -> str:
    """
    Öffnet eine Arbeitsagentur-Stellenseite, findet den externen Detail-Link
    (z. B. jobs-oberlausitz.de/stelle/detail/...) und extrahiert von dort den Beschreibungstext.
    """
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(job_url, timeout=60000)
        await page.wait_for_timeout(4000)

        # --- Externen Anbieter-Link mit Detailseite finden ---
        external_link = None
        anchors = await page.query_selector_all("a[href]")
        for a in anchors:
            href = await a.get_attribute("href")
            if not href:
                continue
            abs_href = urljoin(page.url, href)

            # Wir suchen gezielt nach externen Detailseiten
            if (
                abs_href.startswith("http")
                and "arbeitsagentur.de" not in abs_href
                and "/stelle/detail/" in abs_href
            ):
                external_link = abs_href
                break

        if not external_link:
            print("⚠️ Kein externer Detail-Link gefunden.")
            await browser.close()
            return "Keine externe Beschreibung gefunden."

        print(f"🌐 Externer Detail-Link gefunden: {external_link}")

        # --- Anbieter-Seite laden ---
        await page.goto(external_link, timeout=60000)
        await page.wait_for_timeout(4000)

        try:
            # Beschreibungstext holen
            text = await page.inner_text("body")
        except Exception as e:
            print("Fehler beim Lesen der externen Seite:", e)
            text = "Keine Beschreibung gefunden."

        await browser.close()
        return text.strip() or "Keine Beschreibung gefunden."


# --- manueller Test ---
if __name__ == "__main__":
    test_url = "https://www.arbeitsagentur.de/jobsuche/suche?id=12964-JOBSOL40873-S&angebotsart=1"
    try:
        text = asyncio.run(extract_job_description_playwright(test_url))
        print("\n--- AUSZUG ---\n")
        print(text[:2000])  # ersten 2000 Zeichen anzeigen
    except Exception as e:
        print("Fehler:", e)