#!/usr/bin/env python3
import asyncio
from playwright.async_api import async_playwright

async def fetch_rendered_jobdetails(external_id: str) -> str | None:
    """
    Lädt eine BA-Jobseite vollständig, wartet auf Angular und extrahiert Text aus Shadow-DOM.
    """
    url = f"https://www.arbeitsagentur.de/jobsuche/suche?id={external_id}&angebotsart=1"
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"🌐 Lade Seite: {url}")

        await page.goto(url, timeout=60000)
        await page.wait_for_timeout(8000)

        # Versuch: den sichtbaren Text über JS abrufen
        text = await page.evaluate(
            """() => {
                const details = document.querySelector('jb-job-details');
                if (!details) return null;
                const shadow = details.shadowRoot || details.attachShadow?.({mode:'open'});
                if (!shadow) return details.innerText || null;
                return shadow.innerText || null;
            }"""
        )

        await browser.close()
        if text and len(text.strip()) > 200:
            print("✅ Beschreibung aus Shadow-DOM extrahiert.")
            return text.strip()
        else:
            return None


# --- Testlauf ---
if __name__ == "__main__":
    test_id = "12964-JOBSOL40873-S"
    result = asyncio.run(fetch_rendered_jobdetails(test_id))
    if result:
        print("\n🧾 --- Auszug ---\n")
        print(result[:1500])
    else:
        print("❌ Kein Beschreibungstext extrahiert.")