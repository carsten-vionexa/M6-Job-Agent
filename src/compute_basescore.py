#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# compute_basescore.py — Lightweight "BaseScore" computation without full job descriptions.
# Usage:
#   python compute_basescore.py --db data/career_agent.db
#
# What it does:
# 1) Detects active profile (user_profile or profiles).
# 2) Parses profile skills and (optionally) region.
# 3) Scores each job using title/keywords/location only.
# 4) Writes jobs.base_score, jobs.fit_score (if NULL), and jobs.why_base (short explanation).
#
# Safe to run multiple times.

import argparse
import re
import sqlite3
from datetime import datetime

STOPWORDS = {
    "und","oder","mit","für","der","die","das","den","dem","ein","eine",
    "in","von","an","im","am","auf","bei","zu","aus","per","the","of","to",
}

NEGATIVE_LEVEL = {"werkstudent","praktikum","trainee"}
POSITIVE_LEVEL = {"senior","lead","principal","head"}
ROLE_SYNONYMS = {
    "berater":"consultant",
    "daten":"data",
    "wissenschaftler":"scientist",
    "ingenieur":"engineer",
    "entwickler":"developer",
    "analyse":"analytics",
    "analyst":"analyst",
    "architekt":"architect",
}
REMOTE_TOKENS = {"remote","homeoffice","home-office","home", "hybrid"}

def table_exists(conn, name):
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,))
    return cur.fetchone() is not None

def get_columns(conn, table):
    cur = conn.cursor()
    cur.execute(f"PRAGMA table_info({table})")
    return [row[1] for row in cur.fetchall()]

def normalize_txt(s):
    if not s:
        return ""
    s = s.lower()
    # normalize german umlauts very lightly (optional)
    s = s.replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
    # keep letters, digits, +, #
    s = re.sub(r"[^a-z0-9+#]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def tokenize(s):
    toks = [t for t in normalize_txt(s).split(" ") if t and t not in STOPWORDS]
    # map synonyms
    mapped = []
    for t in toks:
        mapped.append(ROLE_SYNONYMS.get(t, t))
    return set(mapped)

def jaccard(a, b):
    if not a or not b:
        return 0.0
    inter = len(a & b)
    union = len(a | b)
    return inter / union if union else 0.0

def clamp01(x):
    return max(0.0, min(1.0, float(x)))

def detect_remote(tokens, location_txt):
    loc_tokens = tokenize(location_txt or "")
    if REMOTE_TOKENS & tokens or REMOTE_TOKENS & loc_tokens:
        return True
    return False

def pick_active_profile(conn):
    # prefer 'user_profile', else 'profiles'
    profile_table = None
    for cand in ("user_profile","profiles"):
        if table_exists(conn, cand):
            profile_table = cand
            break
    if not profile_table:
        raise RuntimeError("Weder 'user_profile' noch 'profiles' Tabelle gefunden.")
    cols = get_columns(conn, profile_table)
    cur = conn.cursor()
    if "is_active" in cols:
        cur.execute(f"SELECT * FROM {profile_table} WHERE is_active=1 LIMIT 1")
        row = cur.fetchone()
        if not row:
            cur.execute(f"SELECT * FROM {profile_table} LIMIT 1")
            row = cur.fetchone()
    else:
        cur.execute(f"SELECT * FROM {profile_table} LIMIT 1")
        row = cur.fetchone()
    if not row:
        raise RuntimeError(f"Keine Profileinträge in Tabelle '{profile_table}'.")
    # map row to dict using column names
    colnames = [d[0] for d in cur.description]
    prof = dict(zip(colnames, row))
    prof["_table"] = profile_table
    return prof

def ensure_job_columns(conn):
    cur = conn.cursor()
    cols = get_columns(conn, "jobs")
    if "base_score" not in cols:
        cur.execute("ALTER TABLE jobs ADD COLUMN base_score REAL")
    if "fit_score" not in cols:
        cur.execute("ALTER TABLE jobs ADD COLUMN fit_score REAL")
    if "why_base" not in cols:
        cur.execute("ALTER TABLE jobs ADD COLUMN why_base TEXT")
    conn.commit()

def fetch_jobs(conn):
    cur = conn.cursor()
    # guess available columns
    cols = get_columns(conn, "jobs")
    fields = ["id"]
    for f in ("title","location","company","description","keywords","source","url"):
        if f in cols:
            fields.append(f)
    cur.execute(f"SELECT {', '.join(fields)} FROM jobs")
    colnames = [d[0] for d in cur.description]
    rows = [dict(zip(colnames, r)) for r in cur.fetchall()]
    return rows

def compute_base_score(job, profile):
    title = job.get("title","") or ""
    location = job.get("location","") or ""
    # profile fields (best-effort)
    skills_txt = profile.get("skills","") or ""
    summary = profile.get("summary","") or ""
    region = profile.get("region","") or profile.get("preferred_region","") or ""

    title_tokens = tokenize(title)
    profile_skills = set([s.strip().lower() for s in re.split(r"[;,/|]", skills_txt)]) if skills_txt else set()
    profile_skills = {normalize_txt(s) for s in profile_skills if s}
    profile_skills = {ROLE_SYNONYMS.get(s, s) for s in profile_skills if s}
    # add summary tokens lightly (acts as weak prior)
    summary_tokens = tokenize(summary) if summary else set()

    # 1) Skill overlap (title vs profile skills/summary)
    ref_tokens = (profile_skills | summary_tokens)
    skill_overlap = jaccard(title_tokens, ref_tokens)

    # 2) Role match (any role-like token overlap; ensure consultant/analyst/architect etc. count)
    role_match = 1.0 if ({"consultant","analyst","architect","engineer","scientist","developer"} & title_tokens) else 0.0
    # If profile contains a role tag, this boosts role_match when aligned
    prof_role_tokens = set()
    for k in ("role","target_role","title","name"):
        if profile.get(k):
            prof_role_tokens |= tokenize(str(profile[k]))
    if prof_role_tokens & title_tokens:
        role_match = 1.0

    # 3) Location match
    location_match = 0.0
    if region:
        region_norm = normalize_txt(region)
        if region_norm and region_norm in normalize_txt(location):
            location_match = 1.0
    if detect_remote(title_tokens, location):
        location_match = max(location_match, 0.5)

    # 4) Seniority / level nudges
    level_bonus = 0.0
    if NEGATIVE_LEVEL & title_tokens:
        level_bonus -= 0.25
    if POSITIVE_LEVEL & title_tokens:
        level_bonus += 0.05

    # Weighted combination
    score = 0.55 * skill_overlap + 0.25 * role_match + 0.15 * location_match + 0.05 * (level_bonus + 0.5)
    # Note: adding 0.5 inside last term keeps the small nudge centered; then clamp.
    score = clamp01(score)

    # Build why text (one-liner)
    why_bits = []
    if skill_overlap >= 0.25:
        # list up to 2 overlapping tokens (human-friendly)
        overlap = list((title_tokens & ref_tokens) - STOPWORDS)
        overlap = [o for o in overlap if o and o not in NEGATIVE_LEVEL][:2]
        if overlap:
            why_bits.append("Skills: " + ", ".join(overlap))
        else:
            why_bits.append("Skills passen")
    if role_match >= 1.0:
        why_bits.append("Rolle passt")
    if location_match >= 1.0:
        why_bits.append("Region passt")
    elif location_match >= 0.5:
        why_bits.append("Remote/Hybrid möglich")
    if level_bonus < 0:
        why_bits.append("⚠️ Einstiegs-/Studierenden-Rolle")
    elif level_bonus > 0.01:
        why_bits.append("Senior/Lead möglich")

    if not why_bits:
        why_bits = ["Basis-Match aus Titel/Ort"]

    why = " · ".join(why_bits)
    return score, why

def update_job_scores(conn, jobs, profile):
    cur = conn.cursor()
    updated = 0
    for job in jobs:
        score, why = compute_base_score(job, profile)
        cur.execute("UPDATE jobs SET base_score=?, why_base=?, fit_score=COALESCE(fit_score, ?) WHERE id=?",
                    (score, why, score, job["id"]))
        updated += 1
    conn.commit()
    return updated

def main():
    ap = argparse.ArgumentParser(description="Compute lightweight BaseScore for jobs using profile & title/loc only.")
    ap.add_argument("--db", default="data/career_agent.db", help="Path to SQLite DB (default: data/career_agent.db)")
    args = ap.parse_args()

    conn = sqlite3.connect(args.db)
    try:
        # ensure jobs table and required cols
        if not table_exists(conn, "jobs"):
            raise RuntimeError("Tabelle 'jobs' fehlt in der Datenbank.")
        ensure_job_columns(conn)

        # pick active profile
        profile = pick_active_profile(conn)

        # fetch jobs
        jobs = fetch_jobs(conn)
        if not jobs:
            print("Keine Jobs gefunden – bitte zuerst den Research-Prozess ausführen.")
            return

        # compute & update
        n = update_job_scores(conn, jobs, profile)

        # Show preview Top-20
        cur = conn.cursor()
        cur.execute(\"""
            SELECT id, title, location, base_score, why_base
            FROM jobs
            ORDER BY base_score DESC, id ASC
            LIMIT 20
        \""")
        rows = cur.fetchall()
        print("\\nTop 20 nach BaseScore:")
        print("-"*80)
        for r in rows:
            jid, title, location, score, why = r
            print(f"[{jid:>4}] {score:0.3f}  {title} — {location or '-'}")
            print(f"      {why}")
        print("-"*80)
        print(f"Aktualisiert: {n} Jobs  •  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    finally:
        conn.close()

if __name__ == "__main__":
    main()
