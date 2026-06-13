#!/usr/bin/env python3
"""Fetch Jobright job info URLs and build jobs.json with template routing."""

import json
import re
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "jobs"))

from keyword_router import pick_template, load_templates  # noqa: E402

COOKIES_FILE = ROOT / "jobs" / "cookies.json"
HEADERS = {
    "accept": "application/json, text/plain, */*",
    "accept-language": "en-US,en;q=0.9",
    "user-agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.0.0 Safari/537.36"
    ),
    "referer": "https://jobright.ai/jobs/recommend",
    "x-client-type": "web",
}

JOB_URLS = [
    "https://jobright.ai/jobs/info/6a2711932056260dd6e84ec3",
    "https://jobright.ai/jobs/info/6a27117d7d827633afff866d",
    "https://jobright.ai/jobs/info/6a2734a32056260dd6e85f67",
    "https://jobright.ai/jobs/info/6a26f1197d827633afff78c9",
    "https://jobright.ai/jobs/info/6a26d60aca77fd3096d237c9",
    "https://jobright.ai/jobs/info/6a2712044ec8d737d6dfda6a",
    "https://jobright.ai/jobs/info/6a27257aca77fd3096d25af6",
    "https://jobright.ai/jobs/info/6a2744ac4ec8d737d6dfef3b",
    "https://jobright.ai/jobs/info/6a26e87e2056260dd6e83cde",
    "https://jobright.ai/jobs/info/6a27311a2056260dd6e85e1a",
]

API_CANDIDATES = [
    "https://jobright.ai/swan/job/detail?jobId={job_id}",
    "https://jobright.ai/swan/job/info?jobId={job_id}",
    "https://jobright.ai/swan/jobs/detail?jobId={job_id}",
]


def load_cookies() -> dict:
    if COOKIES_FILE.exists():
        return json.loads(COOKIES_FILE.read_text(encoding="utf-8"))
    return {}


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", " ", (s or "").lower()).strip()


def extract_job_id(url: str) -> str:
    return url.rstrip("/").split("/")[-1]


def parse_embedded_job(html: str) -> dict | None:
    """Parse job payload embedded in Jobright HTML (__NEXT_DATA__ or inline JSON)."""
    patterns = [
        r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
        r'"jobResult"\s*:\s*(\{.*?"jobId".*?\})\s*,\s*"companyResult"',
        r'window\.__INITIAL_STATE__\s*=\s*(\{.*?\});',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.DOTALL)
        if not m:
            continue
        try:
            data = json.loads(m.group(1))
        except json.JSONDecodeError:
            continue
        # __NEXT_DATA__ shape (authenticated pages use pageProps.dataSource)
        if isinstance(data, dict) and "props" in data:
            page_props = data.get("props", {}).get("pageProps", {})
            source = page_props.get("dataSource") or page_props
            job = source.get("jobResult") or page_props.get("jobResult", {})
            company = source.get("companyResult") or page_props.get("companyResult", {})
            if job or company:
                return {
                    "jobResult": job,
                    "companyResult": company,
                    "skillMatchingScores": (
                        source.get("skillMatchingScores")
                        or job.get("skillMatchingScores", [])
                        or page_props.get("skillMatchingScores", [])
                    ),
                    "displayScore": (
                        source.get("displayScore")
                        or page_props.get("displayScore")
                        or job.get("displayScore")
                    ),
                }
        if isinstance(data, dict) and "jobResult" in data:
            return data
    # Fallback: regex fields from HTML/JSON blob
    desc_m = re.search(r'"description":"((?:[^"\\]|\\.)*?)"', html)
    title_m = re.search(r'"jobTitle":"((?:[^"\\]|\\.)*?)"', html)
    company_m = re.search(r'"companyName":"((?:[^"\\]|\\.)*?)"', html)
    location_m = re.search(r'"jobLocation":"((?:[^"\\]|\\.)*?)"', html)
    if not (desc_m or title_m):
        return None
    desc = desc_m.group(1).encode("utf-8").decode("unicode_escape") if desc_m else ""
    return {
        "jobResult": {
            "jobId": None,
            "jobTitle": title_m.group(1) if title_m else "Unknown",
            "jobLocation": location_m.group(1) if location_m else "Unknown",
            "description": desc,
            "skillMatchingScores": [],
        },
        "companyResult": {"companyName": company_m.group(1) if company_m else "Unknown"},
    }


def fetch_via_api(job_id: str, cookies: dict) -> dict | None:
    for tmpl in API_CANDIDATES:
        url = tmpl.format(job_id=job_id)
        try:
            r = requests.get(url, headers=HEADERS, cookies=cookies, timeout=20)
            if r.status_code != 200:
                continue
            data = r.json()
            result = data.get("result") or data
            if isinstance(result, dict) and ("jobResult" in result or "jobTitle" in result):
                if "jobResult" not in result and "jobTitle" in result:
                    result = {"jobResult": result, "companyResult": result.get("companyResult", {})}
                return result
        except Exception:
            continue
    return None


def fetch_via_html(job_id: str, cookies: dict) -> dict | None:
    url = f"https://jobright.ai/jobs/info/{job_id}"
    try:
        r = requests.get(url, headers={**HEADERS, "accept": "text/html"}, cookies=cookies, timeout=25)
        if r.status_code != 200:
            return None
        return parse_embedded_job(r.text)
    except Exception:
        return None


def split_jobright_skills(scores: list) -> tuple[list[str], list[str]]:
    matched, missing = [], []
    for s in scores or []:
        name = s.get("displayName") or s.get("skillName") or ""
        if not name:
            continue
        if s.get("score", 0) > 0.5:
            matched.append(name)
        else:
            missing.append(name)
    return matched, missing


def template_skill_match(jd_text: str, template_code: str) -> tuple[list[str], list[str]]:
    """Match/missing relative to selected base template keyword list."""
    templates = {t["code"]: t for t in load_templates()}
    tpl = templates.get(template_code)
    if not tpl:
        return [], []
    jd_norm = _norm(jd_text)
    matched, missing = [], []
    for kw in tpl["keywords"]:
        kw_norm = _norm(kw)
        if not kw_norm:
            continue
        # word/phrase presence in JD
        if kw_norm in jd_norm or re.search(rf"\b{re.escape(kw_norm)}\b", jd_norm):
            matched.append(kw)
        else:
            missing.append(kw)
    return sorted(set(matched)), sorted(set(missing))


def jd_skill_tokens(jd_text: str) -> list[str]:
    """Extract likely skill tokens from JD for routing when Jobright scores absent."""
    chunks = re.split(r"[,;|\n•]+", jd_text)
    out = []
    for c in chunks:
        c = c.strip()
        if 2 <= len(c) <= 80:
            out.append(c)
    return out[:80]


def build_role(url: str, cookies: dict) -> dict:
    job_id = extract_job_id(url)
    payload = fetch_via_api(job_id, cookies) or fetch_via_html(job_id, cookies)
    if not payload:
        return {
            "Company": "UNKNOWN",
            "Title": "UNKNOWN",
            "JobLink": url,
            "JobId": job_id,
            "Error": "Failed to fetch job data",
        }

    job = payload.get("jobResult", {})
    company = payload.get("companyResult", {})
    title = job.get("jobTitle", "Unknown")
    company_name = company.get("companyName", "Unknown")
    location = job.get("jobLocation", "Unknown")
    description = job.get("description", "") or ""
    if description:
        description = description.encode("utf-8").decode("unicode_escape", errors="replace")

    jr_matched, jr_missing = split_jobright_skills(
        payload.get("skillMatchingScores") or job.get("skillMatchingScores", [])
    )

    # Use Jobright skills for routing when present; else JD tokens
    route_matched = jr_matched if jr_matched else jd_skill_tokens(description)[:30]
    route_missing = jr_missing

    routing = pick_template(
        title=title,
        matched=route_matched,
        missing=route_missing,
        jd_text=description,
        verbose=True,
    )
    base_template = routing["code"]

    # Template-relative matched/missing — disabled until re-enabled by user
    # tpl_matched, tpl_missing = template_skill_match(description, base_template)

    return {
        "Company": company_name,
        "Title": title,
        "Location": location,
        "PublishTime": job.get("publishTimeDesc", ""),
        "MinYOE": job.get("minYearsOfExperience", ""),
        "MatchScore": payload.get("displayScore") or job.get("displayScore"),
        "JobLink": url,
        "JobId": job_id,
        "BaseTemplate": base_template,
        "BaseTemplatePath": next(
            (t["path"] for t in load_templates() if t["code"] == base_template), ""
        ),
        "RoutingDetails": {
            "family": routing.get("family"),
            "is_new_grad": routing.get("is_new_grad"),
            "score": routing.get("score"),
            "matched_keyword_hits": routing.get("matched_hits", []),
            "missing_keyword_hits": routing.get("missing_hits", []),
            "title_keyword_hits": routing.get("title_hits", []),
            "all_scores": routing.get("all_scores", []),
        },
        # "MatchedSkills": tpl_matched,   # re-enable when needed
        # "MissingSkills": tpl_missing,   # re-enable when needed
        "MatchedSkills": [],
        "MissingSkills": [],
        "JobrightMatchedSkills": jr_matched,
        "JobrightMissingSkills": jr_missing,
        "JDText": description[:8000],
        "WorkExpComment": "",
        "ProjectComment": "",
    }


def main():
    out_dir = ROOT / sys.argv[1] if len(sys.argv) > 1 else ROOT / "20260521"
    out_dir.mkdir(parents=True, exist_ok=True)
    cookies = load_cookies()

    roles = []
    for url in JOB_URLS:
        print(f"Fetching {url} ...")
        role = build_role(url, cookies)
        roles.append(role)
        print(f"  -> {role.get('Company')} | {role.get('Title')} | {role.get('BaseTemplate')}")

    out_file = out_dir / "jobs.json"
    out_file.write_text(json.dumps(roles, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {len(roles)} roles to {out_file}")


if __name__ == "__main__":
    main()
