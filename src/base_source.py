from abc import ABC, abstractmethod
from typing import List, Dict, Any

class JobSource(ABC):
    """Abstrakte Basis-Klasse für Jobportale."""

    name: str = "Generic Source"

    @abstractmethod
    def search(self, query: str, ort: str, umkreis: int, size: int = 10) -> List[Dict[str, Any]]:
        """Führt die Jobsuche durch und gibt eine Liste von Jobdicts zurück."""
        pass

    @abstractmethod
    def get_details(self, job_id: str) -> Dict[str, Any]:
        """Lädt Detaildaten für eine konkrete Stelle."""
        pass