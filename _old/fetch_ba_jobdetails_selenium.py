#!/usr/bin/env python3
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

def fetch_job_text(external_id: str) -> str | None:
    """
    Öffnet die Arbeitsagentur-Detailseite mit Selenium
    und liest den sichtbaren Text aus dem Shadow-DOM der Komponente jb-job-details.
    """
    url = f"https://www.arbeitsagentur.de/jobsuche/suche?id={external_id}&angebotsart=1"

    # Browseroptionen
    opts = Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=opts)
    print(f"🌐 Lade {url}")
    driver.get(url)

    # Angular braucht etwas Zeit, um das DOM zu rendern
    time.sleep(8)

    try:
        # Zugriff auf Shadow-DOM über JavaScript
        script = """
        const jobDetails = document.querySelector('jb-job-details');
        if (!jobDetails) return null;
        const shadow = jobDetails.shadowRoot;
        if (!shadow) return jobDetails.innerText;
        return shadow.innerText;
        """
        text = driver.execute_script(script)
        driver.quit()

        if text and len(text.strip()) > 200:
            print("✅ Text extrahiert.")
            return text.strip()
        else:
            print("❌ Kein Text gefunden.")
            return None

    except Exception as e:
        print("⚠️ Fehler:", e)
        driver.quit()
        return None


if __name__ == "__main__":
    external_id = "12322-S0QGXPMSC5XCB6G2-S"   # Beispiel
    text = fetch_job_text(external_id)

    if text:
        print("\n🧾 --- Auszug ---\n")
        print(text[:1500])
    else:
        print("❌ Keine Beschreibung extrahiert.")