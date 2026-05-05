#!/usr/bin/env python3
"""
Fetch Jobright recommendations and save to a dated CSV.
Loads cookies from cookies.json (next to this script). Update SESSION_ID there when it expires.
"""

import csv
import json
import os
import sys
from datetime import datetime
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).parent
COOKIES_FILE = SCRIPT_DIR / "cookies.json"

COUNT = 10  # API rejects larger values with 400
MAX_JOBS = 200

HEADERS = {
    "accept": "application/json, text/plain, */*",
    "user-agent": (
        "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Mobile Safari/537.36"
    ),
    "referer": "https://jobright.ai/jobs/recommend",
    "x-client-type": "mobile_web",
}

CSV_FIELDS = [
    "Company", "Title", "Location", "Publish Time", "Salary", "Work Model",
    "Match Score", "Applicants", "Min YOE", "H1B Sponsor",
    "Matched Skills", "Missing Skills", "URL", "Apply Link",
]


def load_cookies() -> dict:
    if not COOKIES_FILE.exists():
        print(f"ERROR: {COOKIES_FILE} not found. Copy cookies.json.example and fill in your session cookies.")
        sys.exit(1)
    with open(COOKIES_FILE) as f:
        return json.load(f)


def fetch_all(cookies: dict) -> list[dict]:
    parsed = []
    seen = set()
    position = 0

    print("Fetching recommended jobs from Jobright...")

    while position < MAX_JOBS:
        refresh = "true" if position == 0 else "false"
        url = (
            f"https://jobright.ai/swan/recommend/list/jobs"
            f"?refresh={refresh}&sortCondition=0&position={position}&count={COUNT}&syncRerank=false"
        )
        resp = requests.get(url, headers=HEADERS, cookies=cookies, timeout=30)
        if resp.status_code != 200:
            print(f"Error at position {position}: HTTP {resp.status_code} — {resp.text[:200]}")
            break

        try:
            data = resp.json()
        except json.JSONDecodeError:
            print("Failed to parse JSON response. Stopping.")
            break

        jobs = data.get("result", {}).get("jobList", [])
        if not jobs:
            print("No more jobs found, stopping pagination.")
            break

        added = 0
        for job in jobs:
            j = job.get("jobResult", {})
            c = job.get("companyResult", {})
            job_id = j.get("jobId")

            if job_id and job_id in seen:
                continue
            seen.add(job_id)
            added += 1

            skill_scores = j.get("skillMatchingScores", [])
            matched = [s.get("displayName") for s in skill_scores if s.get("score", 0) > 0.5]
            missing = [s.get("displayName") for s in skill_scores if s.get("score", 0) <= 0.5]

            parsed.append({
                "Company": c.get("companyName", "Unknown"),
                "Title": j.get("jobTitle", "Unknown"),
                "Location": j.get("jobLocation", "Unknown"),
                "Publish Time": j.get("publishTimeDesc", "Unknown"),
                "Salary": j.get("salaryDesc", "N/A"),
                "Work Model": j.get("workModel", "N/A"),
                "Match Score": job.get("displayScore", "N/A"),
                "Applicants": j.get("applicantsCount", "N/A"),
                "Min YOE": j.get("minYearsOfExperience", "N/A"),
                "H1B Sponsor": j.get("isH1bSponsor", False),
                "Matched Skills": ", ".join(matched),
                "Missing Skills": ", ".join(missing),
                "URL": f"https://jobright.ai/jobs/info/{job_id}" if job_id else "",
                "Apply Link": j.get("applyLink") or j.get("originalUrl", ""),
            })

        if added == 0:
            print("Only duplicate jobs on this page. Stopping pagination.")
            break

        position += COUNT

    return parsed


def save_csv(jobs: list[dict]) -> Path:
    today = datetime.now().strftime("%Y-%m-%d")
    out_dir = SCRIPT_DIR / today
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / f"{today}_jobright_recommendations.csv"

    with open(out_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_FIELDS)
        writer.writeheader()
        writer.writerows(jobs)

    return out_path


def main():
    cookies = load_cookies()
    jobs = fetch_all(cookies)

    print(f"Successfully found {len(jobs)} recommended jobs in total.")

    if not jobs:
        sys.exit(1)

    out_path = save_csv(jobs)
    print(f"Saved all jobs to {out_path}")

    print("\n--- SAMPLE JOBS ---")
    for j in jobs[:5]:
        print(f"- {j['Company']}: {j['Title']} ({j['Location']} | {j['Work Model']})")
        print(f"  Score: {j['Match Score']} | Salary: {j['Salary']}")
        print(f"  URL: {j['URL']}\n")


if __name__ == "__main__":
    main()
