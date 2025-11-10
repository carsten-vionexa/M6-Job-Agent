import requests

url = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/jobs"
headers = {"X-API-Key": "jobboerse-jobsuche"}
params = {
    "was": "Bürokaufmann",
    "wo": "Görlitz",
    "umkreis": 30,
    "page": 1,
    "size": 5
}

r = requests.get(url, headers=headers, params=params)
print("Status:", r.status_code)
print("URL:", r.url)
print(r.text[:400])