# Jobright Daily Job Fetcher

Automated daily pipeline that pulls your personalized job recommendations from the Jobright API and stores them as date-organized CSVs.

## What was built

- **[fetch_jobs.py](fetch_jobs.py)** — Python script that calls `https://jobright.ai/swan/recommend/list/jobs`, paginates up to 100 jobs, parses the response, and writes a CSV.
- **[cookies.json](cookies.json)** — Your Jobright session cookies (used for authentication). Gitignored-worthy.
- **[cookies.json.example](cookies.json.example)** — Template for anyone else setting this up.
- **[setup_cron.sh](setup_cron.sh)** — One-shot installer that registers a daily cron job at 9 AM.
- **[cron.log](cron.log)** — stdout/stderr from scheduled runs (created on first cron execution).

## How it works

1. **Auth** — Script loads cookies from `cookies.json` and sends them with each request. The important one is `SESSION_ID`.
2. **Paginate** — Loops through `position=0, 10, 20, ...` with `count=10` per call (API rejects `count > 10` with HTTP 400).
3. **Dedupe** — Tracks `jobId` in a set and stops when a page returns only duplicates or no new jobs.
4. **Parse** — Pulls from `result.jobList[*].jobResult` (job fields) and `result.jobList[*].companyResult` (company name).
5. **Save** — Writes to `jobs/YYYY-MM-DD/YYYY-MM-DD_jobright_recommendations.csv`. Overwrites if the script is re-run on the same day.

## CSV schema

| Column | Source |
|---|---|
| Company | `companyResult.companyName` |
| Title | `jobResult.jobTitle` |
| Location | `jobResult.jobLocation` |
| Publish Time | `jobResult.publishTimeDesc` |
| Salary | `jobResult.salaryDesc` |
| Work Model | `jobResult.workModel` (Remote / Hybrid / Onsite) |
| Match Score | `displayScore` (top-level on each entry) |
| Applicants | `jobResult.applicantsCount` |
| Min YOE | `jobResult.minYearsOfExperience` |
| H1B Sponsor | `jobResult.isH1bSponsor` |
| Matched Skills | `skillMatchingScores` with `score > 0.5` |
| Missing Skills | `skillMatchingScores` with `score <= 0.5` |
| URL | `applyLink` (fallback: `originalUrl`) |

## Daily scheduling

Cron was installed via `setup_cron.sh`. Current entry:

```
0 9 * * * /opt/homebrew/opt/python@3.14/Frameworks/Python.framework/Versions/3.14/bin/python3 /Users/ajayvenkatesh/Desktop/Resume\ Job\ Roles/jobs/fetch_jobs.py >> /Users/ajayvenkatesh/Desktop/Resume\ Job\ Roles/jobs/cron.log 2>&1
```

Check the cron list with:

```bash
crontab -l
```

## Running manually

```bash
cd "/Users/ajayvenkatesh/Desktop/Resume Job Roles/jobs"
python3 fetch_jobs.py
```

Expected output: `Successfully found N recommended jobs in total.` followed by a sample of 5 jobs.

## When the session expires

Symptom: cron.log shows `Error at position 0: HTTP 401` (or 400/403), and no CSV is produced.

Fix:
1. Log into [jobright.ai](https://jobright.ai/jobs/recommend) in your browser.
2. Open DevTools → Network tab → refresh the page.
3. Find any request to `jobright.ai/swan/...` → Headers → Cookie.
4. Copy the value of `SESSION_ID=...`.
5. Paste it into `cookies.json` (replacing the old `SESSION_ID`).
6. Re-run `python3 fetch_jobs.py` to confirm it works.

## Folder layout after a few days

```
jobs/
├── fetch_jobs.py
├── cookies.json                 (gitignore this)
├── cookies.json.example
├── setup_cron.sh
├── cron.log
├── README.md
├── 2026-04-22/
│   └── 2026-04-22_jobright_recommendations.csv
├── 2026-04-23/
│   └── 2026-04-23_jobright_recommendations.csv
└── ...
```

## Configuration knobs

Edit these constants at the top of `fetch_jobs.py`:

- `COUNT` — jobs per API call (max 10, API-enforced).
- `MAX_JOBS` — pagination cap (default 100).
- `HEADERS` — swap User-Agent between desktop and mobile-web if needed.
