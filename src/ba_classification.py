import requests
from typing import List, Dict, Any

class BAClassification:
    """
    Zugriff auf die Klassifikations-API der Bundesagentur für Arbeit.
    Dient zur Ermittlung offizieller Berufsbezeichnungen (KldB2010).
    """

    BASE_URL = "https://rest.arbeitsagentur.de/klassifikationen/berufe/v1/berufe"
    HEADERS = {"X-API-Key": "jobboerse-jobsuche"}

    def classify_term(self, suchbegriff: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Liefert bis zu `limit` ähnliche/zugeordnete Berufseinträge."""
        try:
            params = {"suchbegriff": suchbegriff, "page": 1, "size": limit}
            r = requests.get(self.BASE_URL, headers=self.HEADERS, params=params, timeout=15)
            if r.status_code != 200:
                print(f"[Klassifikation] Fehler {r.status_code} bei '{suchbegriff}'")
                return []

            data = r.json()
            berufe = data.get("berufe", [])
            result = []
            for b in berufe:
                result.append({
                    "bezeichnung": b.get("bezeichnung"),
                    "berufsId": b.get("berufsId"),
                    "kldb2010": b.get("kldb2010"),
                    "berufsgruppe": b.get("berufsgruppe"),
                })
            return result

        except Exception as e:
            print(f"[Klassifikation] Fehler bei '{suchbegriff}': {e}")
            return []