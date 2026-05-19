#!/usr/bin/env python3
"""Audit language additions across a batch folder.

For each resume that added a language not in the base template, fetches the JD,
analyzes the context around the language mention, classifies as MANDATORY /
PREFERRED / ALTERNATIVE, and reverts when ALTERNATIVE.

Usage:
    python3 jobs/audit_languages.py <date_folder>
    e.g. python3 jobs/audit_languages.py 18052026
"""

import json
import re
import subprocess
import sys
from pathlib import Path

import requests

ROOT = Path("/Users/ajayvenkatesh/Desktop/Resume Job Roles")
COOKIES = json.loads((ROOT / "jobs" / "cookies.json").read_text())
HEADERS = {
    "accept": "text/html",
    "user-agent": "Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36",
}

# Languages Ajay already has (won't be in MissingSkills, used to detect alternatives)
EXISTING_LANGUAGES = {"python", "java", "c++", "c#", "javascript", "typescript", "sql", "c", "r"}

# Languages we might add via MissingSkills
NEW_LANGUAGES = {"go", "golang", "kotlin", "rust", "scala", "swift", "ruby", "php",
                 "vb.net", "cobol", "objective-c", "dart", "haskell", "groovy",
                 "matlab", "lua", "perl"}


def fetch_jd(joblink: str) -> str:
    try:
        r = requests.get(joblink, headers=HEADERS, cookies=COOKIES, timeout=15)
        m = re.search(r'"description":"([^"\\]+)', r.text)
        if m:
            return m.group(1)[:6000]
    except Exception:
        pass
    return ""


def classify_language_usage(jd_text: str, language: str) -> tuple[str, str]:
    """Return (classification, evidence). Classification ∈ {MANDATORY, PREFERRED, ALTERNATIVE, UNKNOWN}."""
    jd = jd_text.lower()
    lang = language.lower()
    # Find contexts around the language mention
    contexts = [m.group(0) for m in re.finditer(
        rf"[^.<>]{{0,120}}\b{re.escape(lang)}\b[^.<>]{{0,120}}", jd
    )]
    if not contexts:
        return ("UNKNOWN", "no JD mention found")

    # Check ALL contexts for the strongest signal. Priority:
    # MANDATORY > ALTERNATIVE > PREFERRED > UNKNOWN.
    # MANDATORY wins even when an alternative-list also appears elsewhere in the JD.

    # Pass 1 — any MANDATORY anywhere?
    for ctx in contexts:
        # "<existing-lang> and <target>" / "<target> and <existing-lang>" → AND-required
        and_pattern_1 = rf"\b(python|java|c\+\+|c#|typescript|javascript|node)\s+and\s+{re.escape(lang)}\b"
        and_pattern_2 = rf"\b{re.escape(lang)}\s+and\s+(python|java|c\+\+|c#|typescript|javascript|node)\b"
        if re.search(and_pattern_1, ctx) or re.search(and_pattern_2, ctx):
            return ("MANDATORY", ctx)
        if re.search(rf"(required|must have|need[s]? to have|strong (?:knowledge|proficiency))[^.]{{0,80}}\b{re.escape(lang)}\b", ctx):
            return ("MANDATORY", ctx)
        if re.search(rf"\b{re.escape(lang)}\b[^.]{{0,80}}(required|mandatory)", ctx):
            return ("MANDATORY", ctx)

    # Pass 2 — any ALTERNATIVE anywhere?
    for ctx in contexts:
        if re.search(rf"(one of|such as|like|including|e\.g\.|languages?\s*[:\(])[^.]{{0,200}}\b{re.escape(lang)}\b", ctx):
            return ("ALTERNATIVE", ctx)
        existing_in_ctx = sum(1 for el in EXISTING_LANGUAGES
                              if re.search(rf"\b{re.escape(el)}\b", ctx))
        if " or " in ctx and existing_in_ctx >= 1:
            return ("ALTERNATIVE", ctx)
        if existing_in_ctx >= 2:
            return ("ALTERNATIVE", ctx)

    # Pass 3 — any PREFERRED anywhere?
    for ctx in contexts:
        if re.search(rf"(preferred|nice to have|plus|asset|bonus|familiarity|exposure)[^.]{{0,80}}\b{re.escape(lang)}\b", ctx):
            return ("PREFERRED", ctx)
        if re.search(rf"\b{re.escape(lang)}\b[^.]{{0,80}}(is a plus|is an asset|preferred|bonus)", ctx):
            return ("PREFERRED", ctx)

    return ("UNKNOWN", contexts[0][:200])


def remove_language_from_tex(tex_path: Path, language: str) -> bool:
    """Remove `, <language>` from Programming Languages line (both template flavors)."""
    text = tex_path.read_text(encoding="utf-8")
    original = text
    # Flavor A: \textbf{Programming Languages:} ..., <lang>
    text = re.sub(
        rf"(\\textbf\{{Programming Languages:\}}[^\n]*?), {re.escape(language)}([ \\])",
        r"\1\2", text, flags=re.IGNORECASE
    )
    # Flavor B: \resumeSubItem{Programming Languages:}{... , <lang>}
    text = re.sub(
        rf"(\\resumeSubItem\{{Programming Languages:\}}\{{[^}}]*?), {re.escape(language)}(\}})",
        r"\1\2", text, flags=re.IGNORECASE
    )
    if text == original:
        return False
    tex_path.write_text(text, encoding="utf-8")
    return True


def recompile(folder: Path) -> bool:
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "Ajay_Venkatesh_Resume.tex"],
                   cwd=folder, capture_output=True, timeout=60)
    for ext in (".aux", ".log", ".out"):
        (folder / f"Ajay_Venkatesh_Resume{ext}").unlink(missing_ok=True)
    return (folder / "Ajay_Venkatesh_Resume.pdf").exists()


def main():
    date = sys.argv[1] if len(sys.argv) > 1 else "18052026"
    out_dir = ROOT / date
    results_file = out_dir / "batch_results.json"
    if not results_file.exists():
        print(f"No batch_results.json at {results_file}", file=sys.stderr)
        sys.exit(1)

    results = json.loads(results_file.read_text())
    affected = [r for r in results if any(s.lower() in NEW_LANGUAGES for s in r.get("SkillsAdded", []))]
    print(f"Resumes with language additions to audit: {len(affected)}\n")

    actions = []
    for r in affected:
        langs_in_resume = [s for s in r.get("SkillsAdded", []) if s.lower() in NEW_LANGUAGES]
        jd = fetch_jd(r["JobLink"])
        for lang in langs_in_resume:
            classification, evidence = classify_language_usage(jd, lang)
            verdict = {
                "MANDATORY": "KEEP",
                "PREFERRED": "KEEP",
                "ALTERNATIVE": "REVERT",
                "UNKNOWN": "KEEP (default — review manually)",
            }[classification]
            print(f"  {r['Company'][:25]:25} | {lang:8} | {classification:11} → {verdict}")
            print(f"    evidence: {evidence[:160].strip()}")
            actions.append((r, lang, verdict))

    print(f"\nApplying reverts...")
    reverts = 0
    for r, lang, verdict in actions:
        if verdict != "REVERT":
            continue
        slug = re.sub(r"[^\w\-]+", "_", r["Company"]).strip("_")[:60]
        tex = out_dir / slug / "Ajay_Venkatesh_Resume.tex"
        if not tex.exists():
            print(f"  MISS: {tex}")
            continue
        if remove_language_from_tex(tex, lang):
            recompile(tex.parent)
            reverts += 1
            print(f"  ✓ Reverted {lang} in {r['Company']}")

    print(f"\nTotal reverts: {reverts}")


if __name__ == "__main__":
    main()
