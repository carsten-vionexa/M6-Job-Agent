import requests

# Die ID aus Ihrem Link
hash_id = "12964-JOBSOL40873-S"

# Der Endpunkt für Jobdetails
url = f"https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4/app/jobs/{hash_id}"

# Der öffentliche API-Schlüssel als Header
headers = {
    "X-API-Key": "jobboerse-jobsuche"
}

# Die Anfrage senden
response = requests.get(url, headers=headers)

# Überprüfen, ob die Anfrage erfolgreich war
if response.status_code == 200:
    # Die Daten als JSON erhalten
    job_details = response.json()
    
    # Jetzt haben Sie alle Details in einem sauberen Objekt
    # print(job_details) 
    
    # --- HIER KOMMT IHRE LLM INS SPIEL ---
    # z.B. nur die Stellenbeschreibung an die LLM senden
    if "stellenbeschreibung" in job_details:
        beschreibung_text = job_details["stellenbeschreibung"]
        
        # (Hier würden Sie die 'beschreibung_text' an Ihre LLM-API 
        #  senden, um sie zu analysieren, zusammenzufassen oder 
        #  Skills zu extrahieren)
        
        print("Stellenbeschreibung erfolgreich extrahiert.")
        
    # Sie können nun beliebige Daten in Ihre DB speichern
    # z.B. job_details["titel"], job_details["arbeitsort"]["ort"], etc.

else:
    print(f"Fehler bei der API-Anfrage: Status Code {response.status_code}")