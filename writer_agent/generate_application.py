#!/usr/bin/env python3
import sys
from pathlib import Path

# Projekt-Root einbinden → writer_agent als Paket nutzbar
ROOT = Path(__file__).resolve().parents[1]
sys.path.append(str(ROOT))

from writer_agent.db import get_job, get_profile, get_resume_text
from writer_agent.writer import generate_cover_letter, save_as_word


def generate_application(job_id: int):
    print(f"➡️ Starte Bewerbungsgenerierung für Job-ID {job_id}")

    job = get_job(job_id)
    if not job:
        print(f"❌ Job {job_id} nicht gefunden.")
        return

    if not job["profile_id"]:
        print("❌ Keine Profil-ID im Job hinterlegt (obsolete_user_profile_id fehlt).")
        return

    profile = get_profile(job["profile_id"])
    if not profile:
        print(f"❌ Profil {job['profile_id']} nicht gefunden.")
        return

    resume_text = get_resume_text(job["profile_id"])

    if not job["description"]:
        print("⚠️ Job hat keine description. Bitte zuerst manuell oder per Scraper füllen.")
        return

    print(f"🧠 Erzeuge Anschreiben für: {job['title']} bei {job['company']}")

    cover_letter = generate_cover_letter(
        job_title=job["title"],
        company=job["company"],
        job_description=job["description"],
        profile_summary=profile["summary"],
        cv_text=resume_text,
    )

    filepath = save_as_word(cover_letter, job["title"], job["company"])
    print(f"✅ Bewerbung gespeichert unter:\n{filepath}")


if __name__ == "__main__":
    TEST_ID = 1     # <- bitte Job mit gültigem obsolete_user_profile_id angeben
    generate_application(TEST_ID)