#!/usr/bin/env python3
import asyncio
import json
import gzip
from io import BytesIO
from playwright.async_api import async_playwright


async def fetch_ba_jobdetails(external_id: str) -> dict | None:
    """
    Öffnet die Arbeitsagentur-Seite im Browser, zeichnet alle Netzwerkrequests auf
    und gibt die JSON-Daten des /jobdetails/ Requests zurück.
    """
    base_url = f"https://www.arbeitsagentur.de/jobsuche/suche?id={external_id}&angebotsart=1"
    api_data = None

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()

        print(f"🌐 Lade: {base_url}")

        # --- Listener: fängt alle Antworten ab ---
        async def handle_response(response):
            nonlocal api_data
            url = response.url

            if "/jobdetails/" in url and response.status == 200:
                print(f"✅ Gefundene API-Antwort: {url}")
                try:
                    # Erst versuchen, als JSON zu lesen
                    api_data = await response.json()
                except Exception:
                    # Wenn das fehlschlägt, versuchen wir es manuell
                    try:
                        body = await response.body()
                        headers = response.headers
                        if headers.get("content-encoding") == "gzip":
                            print("📦 Antwort ist gzip-komprimiert, entpacke ...")
                            buf = BytesIO(body)
                            with gzip.GzipFile(fileobj=buf) as gz:
                                decoded = gz.read().decode("utf-8")
                        else:
                            decoded = body.decode("utf-8", errors="ignore")

                        if decoded.strip().startswith("{"):
                            api_data = json.loads(decoded)
                        else:
                            print("⚠️ Keine JSON-Struktur erkannt.")
                            api_data = {"raw": decoded[:500]}
                    except Exception as e:
                        print("❌ Fehler beim Verarbeiten der API-Antwort:", e)
                        api_data = None

        page.on("response", handle_response)

        # Seite laden und kurz warten, bis Requests durch sind
        await page.goto(base_url, timeout=60000)
        await page.wait_for_timeout(8000)

        await browser.close()

    return api_data


# --- Testlauf ---
if __name__ == "__main__":
    test_id = "12964-JOBSOL40873-S"
    result = asyncio.run(fetch_ba_jobdetails(test_id))

    if result:
        print("\n--- Felder ---")
        print(f"Titel: {result.get('titel')}")
        print(f"Arbeitgeber: {result.get('arbeitgeber')}")
        print(f"Ort: {result.get('arbeitsort')}")
        print("\nBeschreibung (gekürzt):\n")
        print(result.get('stellenbeschreibung', '')[:1000])
    else:
        print("❌ Keine API-Antwort erhalten.")