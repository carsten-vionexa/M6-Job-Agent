#!/usr/bin/env python3
from dataclasses import dataclass
from datetime import datetime
from typing import Optional

@dataclass
class Job:
    id: int
    title: str
    company: str
    location: Optional[str] = None
    description: Optional[str] = None
    source: Optional[str] = None
    url: Optional[str] = None
    date_posted: Optional[str] = None
    application_type: str = "Ausschreibung"
    matched_profile_id: Optional[int] = None
    match_score: Optional[float] = None

    def __post_init__(self):
        # ISO-String zu Datetime umwandeln, wenn vorhanden
        if isinstance(self.date_posted, str):
            try:
                self.date_posted = datetime.fromisoformat(self.date_posted)
            except ValueError:
                pass

    def short(self):
        return f"{self.title} @ {self.company} ({self.location or 'n/a'})"


@dataclass
class ApplicantProfile:
    id: int
    name: str
    file_path: str
    description_text: str
    resume_id: int
    created_at: Optional[str] = None

    def summary(self, n: int = 160) -> str:
        """Kurze Textvorschau des Profils"""
        return (self.description_text[:n] + "…") if len(self.description_text) > n else self.description_text


@dataclass
class Feedback:
    id: Optional[int]
    job_id: int
    feedback_value: int
    timestamp: str = datetime.now().isoformat(timespec="seconds")
    profile_id: Optional[int] = None
    match_score: Optional[float] = None
    comment: Optional[str] = None

    def label(self) -> str:
        """Einfache verbale Einschätzung zum Feedback-Wert"""
        if self.feedback_value >= 8:
            return "Sehr positiv"
        elif self.feedback_value >= 5:
            return "Neutral bis positiv"
        elif self.feedback_value >= 3:
            return "Verbesserungswürdig"
        else:
            return "Negativ"