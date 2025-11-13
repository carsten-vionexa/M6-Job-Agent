#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

def extract_job_description(job_url: str) -> str:
    """
    Extrahiert den Beschreibungstext einer einzelnen Jobdetailseite
    der Arbeitsagentur.
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    response = requests.get(job_url, headers=headers)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    # Versuch 1: Hauptbereich mit Text
    desc_div = soup.find("div", {"data-cy": "job-detail-description"})
    if not desc_div:
        # Fallback: alle Absätze im Inhaltsbereich
        desc_div = soup.find("div", class_="ba-jobad-section")

    if desc_div:
        text = " ".join(p.get_text(strip=True, separator=" ") for p in desc_div.find_all("p"))
        return text
    else:
        return "Keine Beschreibung gefunden."


if __name__ == "__main__":
    test_url = "https://www.arbeitsagentur.de/jobsuche/suche?id=12964-JOBSOL40873-S&angebotsart=1"
    print(extract_job_description(test_url))