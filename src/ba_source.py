import requests
from typing import List, Dict, Any, Optional
from urllib.parse import urlencode, quote_plus
from .base_source import JobSource


class BAJobSource(JobSource):
    """
    Quelle: Bundesagentur für Arbeit (API)
    Suche (Freitext) + Details (Fallback-fähig) mit stabiler Link-Erzeugung.
    """

    name = "Bundesagentur für Arbeit"
    BASE_URL = "https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc/v4"
    HEADERS = {"X-API-Key": "jobboerse-jobsuche"}

    # -------------------------------------------------------------
    # ID/Link-Hilfen
    # -------------------------------------------------------------
    @staticmethod
    def _extract_id(job: Dict[str, Any]) -> Optional[str]:
        """
        Holt eine gültige ID für den Link. Fällt auf refnr zurück,
        falls kein hashId oder id vorhanden ist.
        """
        return (
            job.get("hashId")
            or job.get("id")
            or job.get("kennnummer")
            or job.get("refnr")
        )

    @staticmethod
    def _build_jobsuche_url(job_id: Optional[str],
                            was: Optional[str] = None,
                            wo: Optional[str] = None,
                            umkreis: Optional[int] = None) -> Optional[str]:
        """Baut einen stabilen URL-Link zur öffentlichen Jobseite."""
        if not job_id:
            return None
        base = "https://www.arbeitsagentur.de/jobsuche/suche"
        params = {"id": str(job_id).strip()}
        # optionale Suchparameter für Kontext
        if was:
            params["angebotsart"] = "1"
            params["was"] = was
        if wo:
            params["wo"] = wo
        if isinstance(umkreis, int):
            params["umkreis"] = min(umkreis, 200)
        return f"{base}?{urlencode(params, quote_via=quote_plus)}"

    @staticmethod
    def _build_jobsuche_url(job_id: Optional[str], was: Optional[str] = None,
                            wo: Optional[str] = None, umkreis: Optional[int] = None) -> Optional[str]:
        if not job_id:
            return None
        base = "https://www.arbeitsagentur.de/jobsuche/suche"
        params = {"id": str(job_id).strip()}
        # optional: Suchkontext anhängen (nicht zwingend, hilft bei Reproduzierbarkeit im Browser)
        if was:
            params["angebotsart"] = "1"
            params["was"] = was
        if wo:
            params["wo"] = wo
        if isinstance(umkreis, int):
            params["umkreis"] = min(umkreis, 200)
        return f"{base}?{urlencode(params, quote_via=quote_plus)}"

    # -------------------------------------------------------------
    # Suche (Freitext)
    # -------------------------------------------------------------
    def search(self, query: str, ort: str, umkreis: int, size: int = 10) -> List[Dict[str, Any]]:
        url = f"{self.BASE_URL}/jobs"
        params = {
            "was": query,
            "wo": ort,
            "umkreis": min(umkreis, 200),
            "page": 1,
            "size": size,
        }

        try:
            r = requests.get(url, headers=self.HEADERS, params=params, timeout=30)
            if r.status_code != 200:
                print(f"[BA] Fehler {r.status_code}: {r.text[:200]}")
                return []

            data = r.json()
            jobs: List[Dict[str, Any]] = []

            for j in data.get("stellenangebote", []) or []:
                titel = j.get("titel") or "Kein Titel"
                arbeitgeber = (
                    j.get("arbeitgeber", {}).get("name")
                    if isinstance(j.get("arbeitgeber"), dict)
                    else j.get("arbeitgeber", "Unbekannt")
                )
                ort_name = (
                    j.get("arbeitsort", {}).get("ort")
                    if isinstance(j.get("arbeitsort"), dict)
                    else j.get("arbeitsort", "n/a")
                )

                job_id = self._extract_id(j)
                link = j.get("link") or self._build_jobsuche_url(job_id, query, ort, umkreis)

                jobs.append({
                    "titel": titel,
                    "arbeitgeber": arbeitgeber,
                    "ort": ort_name,
                    "refnr": j.get("refnr"),     # behalten wir informativ
                    "id": job_id,               # die „richtige“ ID für den Link
                    "source": self.name,
                    "url": link,
                })

            print(f"[BA] {len(jobs)} Treffer für '{query}' in {ort} (+{umkreis} km)")
            return jobs

        except Exception as e:
            print(f"[BA] Fehler bei Suche ({query}): {e}")
            return []

    # -------------------------------------------------------------
    # Details (mit Fallback)
    # -------------------------------------------------------------
    def get_details(self, job_id_or_ref: str) -> Dict[str, Any]:
        """
        Lädt Stellenbeschreibung über /jobdetails/{id_or_ref}.
        Wenn das fehlschlägt, liefern wir einen stabilen Link zur Jobsuche mit ?id=<...>.
        """
        try:
            if not job_id_or_ref:
                return {"beschreibung": "Keine Referenznummer/ID vorhanden.", "url": None}

            detail_url = f"{self.BASE_URL}/jobdetails/{job_id_or_ref}"
            r = requests.get(detail_url, headers=self.HEADERS, timeout=15)

            if r.status_code != 200 or not r.text.strip():
                print(f"[BA] Keine Details für {job_id_or_ref} – Fallback-Link.")
                return {
                    "beschreibung": "Keine Detailbeschreibung verfügbar.",
                    "url": self._build_jobsuche_url(job_id_or_ref),
                }

            d = r.json()
            beschr = (
                (d.get("stellenbeschreibung") or {}).get("beschreibung")
                or d.get("beschreibung")
                or "Keine Beschreibung verfügbar."
            )
            # beste ID für Link ableiten
            best_id = d.get("hashId") or d.get("id") or d.get("kennnummer") or d.get("refnr") or job_id_or_ref
            link = d.get("link") or self._build_jobsuche_url(best_id)

            arbeitgeber = (
                (d.get("arbeitgeber") or {}).get("name")
                if isinstance(d.get("arbeitgeber"), dict)
                else d.get("arbeitgeber", "Unbekannt")
            )

            return {
                "titel": d.get("titel", "n/a"),
                "arbeitgeber": arbeitgeber,
                "beschreibung": beschr,
                "refnr": d.get("refnr", job_id_or_ref),
                "id": best_id,
                "url": link,
                "source": self.name,
            }

        except Exception as e:
            print(f"[BA] Fehler bei Details ({job_id_or_ref}): {e}")
            return {
                "beschreibung": "Fehler beim Laden der Beschreibung.",
                "url": self._build_jobsuche_url(job_id_or_ref),
            }