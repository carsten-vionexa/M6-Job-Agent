import requests

url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
headers = {"X-API-Key": "jobboerse-jobsuche"}
params = {
    "suchbegriffe": "Data Scientist",
    "wo": "München",
    "umkreis": 50,
    "arbeitszeit": "vz;ho",
    "angebotsart": 1,
    "size": 10
}

response = requests.get(url, headers=headers, params=params)
data = response.json()

for job in data.get("stellenangebote", []):
    titel = (
        job.get("titel")
        or (isinstance(job.get("stellenbeschreibung"), dict) and job["stellenbeschreibung"].get("titel"))
        or "Kein Titel"
    )

    arbeitgeber_raw = job.get("arbeitgeber")
    arbeitgeber = (
        arbeitgeber_raw.get("name")
        if isinstance(arbeitgeber_raw, dict)
        else arbeitgeber_raw or "Unbekannt"
    )

    ort_raw = job.get("arbeitsort")
    ort = (
        ort_raw.get("ort")
        if isinstance(ort_raw, dict)
        else ort_raw or "n/a"
    )

    refnr = job.get("refnr", "n/a")
    print(f"{titel} | {arbeitgeber} | {ort} | Ref: {refnr}")