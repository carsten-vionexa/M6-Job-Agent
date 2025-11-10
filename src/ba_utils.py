import requests

def resolve_job_title_to_code(job_title: str) -> dict:
    """
    Sucht über die Klassifikations-API der Bundesagentur für Arbeit
    nach dem passenden Berufscode (berufId) für eine Berufsbezeichnung.

    Gibt ein Dictionary mit 'bezeichnung' und 'berufId' zurück.
    """

    url = "https://rest.arbeitsagentur.de/klassifikationen/berufe/v1/berufe"
    headers = {"X-API-Key": "jobboerse-jobsuche"}
    params = {"suchbegriff": job_title}

    r = requests.get(url, headers=headers, params=params)
    print(f"→ Klassifikation-Abfrage: {r.url}")
    print("→ Status:", r.status_code)

    if r.status_code != 200:
        print(f"⚠️ Fehler {r.status_code}: {r.text[:200]}")
        return {}

    data = r.json()
    if not data.get("berufe"):
        print(f"❌ Kein Treffer für '{job_title}'")
        return {}

    result = data["berufe"][0]
    print(f"✅ '{job_title}' → {result['bezeichnung']} (Code: {result['berufId']})")
    return result