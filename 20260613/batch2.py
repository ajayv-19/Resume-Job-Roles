#!/usr/bin/env python3
"""Batch 2 resume generation for jobs2.json."""

import json
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path(__file__).resolve().parent  # 20260613/
PDFLATEX = "/Library/TeX/texbin/pdflatex"

TEMPLATE_PATHS = {
    "SEP_E": ROOT / "SE/P/E/Ajay_Venkatesh_Resume.tex",
    "SEP_NG": ROOT / "SE/P/NG/Ajay_Venkatesh_Resume.tex",
    "SEJ_E": ROOT / "SE/J/E/Ajay_Venkatesh_Resume.tex",
    "AI_E": ROOT / "AI/E/Ajay_Venkatesh_Resume.tex",
    "FS_E": ROOT / "FS/E/Ajay_Venkatesh_Resume.tex",
    "FE_E": ROOT / "FE/E/Ajay_Venkatesh_Resume.tex",
    "CE_E": ROOT / "CE/E/Ajay_Venkatesh_Resume.tex",
    "SE_LLM_E": ROOT / "SE_LLM/E/Ajay_Venkatesh_Resume.tex",
    "DE_E": ROOT / "DE/E/Ajay_Venkatesh_Resume.tex",
}

# SEP_J → SEJ_E mapping
TEMPLATE_ALIAS = {"SEP_J": "SEJ_E"}

def latex_escape(s):
    return s.replace("#", "\\#").replace("&", "\\&").replace("%", "\\%")

def inject_resumeSubItem(tex, category, skills):
    """Append skills to a \\resumeSubItem{category}{...} line."""
    added = []
    lines = tex.split("\n")
    for i, line in enumerate(lines):
        if "resumeSubItem" in line and category in line:
            m = re.match(r'^(.*\\resumeSubItem\{[^}]+\}\{)(.+)(\}.*)$', line)
            if m:
                prefix, content, suffix = m.group(1), m.group(2), m.group(3)
                for raw in skills:
                    s = latex_escape(raw)
                    if s.lower() not in content.lower() and raw.lower() not in content.lower():
                        content += f", {s}"
                        added.append(raw)
                lines[i] = prefix + content + suffix
            break
    return "\n".join(lines), added

def inject_textbf(tex, category, skills):
    """Append skills to a \\textbf{category} content \\\\ line (SEP_NG / FE_E style)."""
    added = []
    lines = tex.split("\n")
    for i, line in enumerate(lines):
        if "textbf" in line and category in line:
            # Try with trailing \\
            m = re.match(r'^(.*\\textbf\{[^}]+\}\s*)(.+?)(\s*\\\\)(.*)$', line)
            if m:
                prefix, content, bs, rest = m.group(1), m.group(2), m.group(3), m.group(4)
                for raw in skills:
                    s = latex_escape(raw)
                    if s.lower() not in content.lower() and raw.lower() not in content.lower():
                        content += f", {s}"
                        added.append(raw)
                lines[i] = prefix + content + bs + rest
                break
            # Try without trailing \\ (last line in skills block)
            m2 = re.match(r'^(.*\\textbf\{[^}]+\}\s*)(.+)$', line)
            if m2:
                prefix, content = m2.group(1), m2.group(2)
                for raw in skills:
                    s = latex_escape(raw)
                    if s.lower() not in content.lower() and raw.lower() not in content.lower():
                        content += f", {s}"
                        added.append(raw)
                lines[i] = prefix + content
                break
    return "\n".join(lines), added

def inject_aws_paren(tex, services):
    """Inject services inside AWS(...) on a skills line."""
    added = []
    lines = tex.split("\n")
    for i, line in enumerate(lines):
        if "AWS (" in line:
            def repl(m, _added=added, _services=services):
                inside = m.group(1)
                for s in _services:
                    if s.lower() not in inside.lower():
                        inside += f", {s}"
                        _added.append(s)
                return "AWS (" + inside + ")"
            new_line = re.sub(r"AWS \(([^)]+)\)", repl, line, count=1)
            lines[i] = new_line
            break
    return "\n".join(lines), added

# --------------------------------------------------------------------------
# Per-company injection plan
# key = company slug, value = list of (inject_fn_name, category, [skills])
# --------------------------------------------------------------------------
# Category string must exactly match text AFTER \resumeSubItem{ or \textbf{
# For resumeSubItem: use "Tools \\& Platforms:" (Python \\& → LaTeX \&)
# For textbf: same escaping

PLAN = {
    "Snap_Inc": [
        ("ri", "Cloud \\& DevOps:", ["Jenkins", "GCP"]),
        ("ri", "Tools \\& Platforms:", ["Gradle", "SonarQube"]),
    ],
    "Gartner": [
        ("aws", None, ["Glue"]),  # AWS Glue → inject inside AWS(...)
    ],
    "Thumbtack": [
        ("ri", "Programming Languages:", ["Go"]),
    ],
    "WHOOP": [],  # missing skills are all concepts
    "WisdomAI": [],  # no missing skills
    "iHeartMedia": [
        ("ri", "Database:", ["Redis"]),
        ("ri", "Web Technologies:", ["Hibernate"]),
    ],
    "Quantifind": [
        ("ri", "Programming Languages:", ["Scala"]),
        ("ri", "Tools:", ["Apache Spark"]),
        ("ri", "Database:", ["Redis", "Memcached"]),
    ],
    "Ascot_Group": [
        ("ri", "Tools \\& Platforms:", ["PySpark"]),
    ],
    "Garmin": [],  # missing are concept/unauthenticated
    "Astronomer": [
        ("ri", "Programming Languages:", ["Go"]),
        ("ri", "Tools \\& Platforms:", ["Apache Airflow"]),
    ],
    "WellSky": [
        ("ri", "Cloud \\& DevOps:", ["GCP"]),
        ("ri", "Web \\& Backend:", [".NET"]),
    ],
    "Block_Tackle": [
        ("ri", "Web \\& Backend:", ["Next.js", "Material UI"]),
    ],
    "Infosys": [
        ("ri", "Web Technologies:", ["Spring Boot", "Spring Security"]),
    ],
    "Goldman_Sachs": [
        ("ri", "Web \\& Backend:", ["Spring", "Hibernate"]),
        ("ri", "Tools \\& Platforms:", ["RabbitMQ"]),
        ("ri", "Databases:", ["Oracle"]),
    ],
    "BAE_Systems_Inc": [
        ("ri", "Programming Languages:", ["C#"]),
        ("ri", "Tools \\& Platforms:", ["Pandas", "Matplotlib"]),
    ],
    "GM_Financial": [
        ("ri", "Cloud \\& DevOps:", ["Jenkins", "Azure DevOps"]),
        ("ri", "Tools \\& Platforms:", ["SonarQube", "YAML"]),
    ],
    "Raytheon": [
        ("ri", "Programming Languages:", ["C#"]),
        ("ri", "Tools:", ["Jenkins", "Ansible"]),
    ],
    "Medpace": [
        ("tb", "Programming Languages:", ["C#"]),
        ("tb", "Web Technologies:", ["Entity Framework"]),
    ],
    "Fitch_Ratings": [
        ("ri", "Web Technologies:", ["Spring Boot"]),
        ("ri", "Tools:", ["SAML"]),
        ("ri", "Database:", ["Oracle"]),
        ("ri", "AI/ML:", ["LlamaIndex"]),
    ],
    "DV_Trading": [],  # domain concepts only
    "Sony_Interactive_Entertainment": [
        ("tb", "Languages:", ["C#"]),  # FE_E uses \textbf{Languages:}
    ],
    "Infosys_2": [
        ("ri", "Web Technologies:", ["Spring Boot", "Spring Security"]),
    ],
    "Kinder_Morgan_Inc": [
        # C# already in CE_E; ASP.NET, .NET Framework → DevOps & Tools
        ("ri", "DevOps \\& Tools:", ["ASP.NET", ".NET Framework"]),
    ],
}

def slug(company: str, idx: int, seen: dict) -> str:
    """Generate a unique folder slug for a company name."""
    base = re.sub(r"[^a-zA-Z0-9]+", "_", company).strip("_")
    # Map known variants
    base = base.replace("Inc_", "Inc").replace("Inc.", "Inc")
    base = base.rstrip("_")
    if base in seen:
        seen[base] += 1
        return f"{base}_{seen[base]}"
    seen[base] = 1
    return base

def compile_pdf(tex_path: Path, out_dir: Path) -> tuple[bool, str]:
    """Run pdflatex twice in out_dir. Returns (success, log_snippet)."""
    for _ in range(2):
        r = subprocess.run(
            [PDFLATEX, "-interaction=nonstopmode", "-output-directory", str(out_dir), str(tex_path)],
            capture_output=True, text=True, timeout=60
        )
    log = r.stdout + r.stderr
    # Check page count
    m = re.search(r'\((\d+) page', log)
    pages = int(m.group(1)) if m else -1
    pdf_exists = (out_dir / "Ajay_Venkatesh_Resume.pdf").exists()
    return pdf_exists and pages == 1, log[-3000:]

def apply_injections(tex: str, slug: str, tpl_code: str) -> tuple[str, list[str], list[str]]:
    """Apply PLAN injections for the given company slug. Returns (tex, skills_added, notes)."""
    plan_entries = PLAN.get(slug, [])
    all_added = []
    notes = []
    is_textbf_tpl = tpl_code in ("SEP_NG", "FE_E")

    for entry in plan_entries:
        fn, category, skills = entry
        if fn == "ri":
            if is_textbf_tpl and category:
                tex, added = inject_textbf(tex, category, skills)
            else:
                tex, added = inject_resumeSubItem(tex, category, skills)
        elif fn == "tb":
            tex, added = inject_textbf(tex, category, skills)
        elif fn == "aws":
            tex, added = inject_aws_paren(tex, skills)
        else:
            added = []
        if added:
            all_added.extend(added)
            notes.append(f"{category or 'AWS()'}: {', '.join(added)}")
    return tex, all_added, notes

def main():
    jobs_file = OUT_DIR / "jobs2.json"
    jobs = json.loads(jobs_file.read_text(encoding="utf-8"))

    results = []
    seen_slugs: dict[str, int] = {}

    for job in jobs:
        company = job["Company"]
        tpl_code = TEMPLATE_ALIAS.get(job["BaseTemplate"], job["BaseTemplate"])
        tpl_path = TEMPLATE_PATHS.get(tpl_code)
        job_slug = slug(company, 0, seen_slugs)

        if not tpl_path or not tpl_path.exists():
            results.append({**job, "slug": job_slug, "status": f"ERROR: template {tpl_code} not found"})
            print(f"[ERROR] {company}: template {tpl_code} missing")
            continue

        # Create output folder
        company_dir = OUT_DIR / job_slug
        company_dir.mkdir(parents=True, exist_ok=True)

        # Copy template
        dest_tex = company_dir / "Ajay_Venkatesh_Resume.tex"
        shutil.copy2(tpl_path, dest_tex)

        # Read and inject
        tex = dest_tex.read_text(encoding="utf-8")
        tex, skills_added, inject_notes = apply_injections(tex, job_slug, tpl_code)
        dest_tex.write_text(tex, encoding="utf-8")

        # Compile
        ok, log = compile_pdf(dest_tex, company_dir)
        status = "OK (1 page)" if ok else "WARNING: not 1 page or compile error"

        # Clean up aux files
        for ext in [".aux", ".log", ".out"]:
            f = company_dir / f"Ajay_Venkatesh_Resume{ext}"
            if f.exists():
                f.unlink()

        result = {
            "Company": company,
            "Title": job["Title"],
            "Location": job["Location"],
            "MatchScore": job["MatchScore"],
            "JobLink": job["JobLink"],
            "BaseTemplate": tpl_code,
            "OriginalTemplate": job["BaseTemplate"],
            "Slug": job_slug,
            "ResumeFolder": str(company_dir.relative_to(ROOT)),
            "ResumePDF": f"20260613/{job_slug}/Ajay_Venkatesh_Resume.pdf",
            "SkillsAdded": skills_added,
            "InjectNotes": inject_notes,
            "BulletsChanged": [],
            "Status": status,
            "JobrightMissingSkills": job.get("JobrightMissingSkills", []),
        }
        results.append(result)
        icon = "✓" if ok else "✗"
        print(f"[{icon}] {company} ({tpl_code}) → {job_slug}/ | added: {skills_added}")

    # Save results JSON
    results_file = OUT_DIR / "batch_results2.json"
    results_file.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote results to {results_file}")

    # Generate HTML summary
    generate_html(results)

def generate_html(results: list):
    rows = []
    for r in results:
        skills_html = ", ".join(r["SkillsAdded"]) if r["SkillsAdded"] else "<em>none</em>"
        inject_html = "<br>".join(r["InjectNotes"]) if r["InjectNotes"] else "<em>none</em>"
        status_cls = "ok" if "OK" in r["Status"] else "warn"
        row = f"""
    <tr data-company="{r['Company'].lower()}" data-template="{r['BaseTemplate'].lower()}" data-status="{status_cls}">
      <td><a href="{r['JobLink']}" target="_blank">{r['Company']}</a></td>
      <td>{r['Title']}</td>
      <td>{r['Location']}</td>
      <td>{r['MatchScore']}</td>
      <td>{r['BaseTemplate']}</td>
      <td>{skills_html}</td>
      <td>{inject_html}</td>
      <td class="{status_cls}">{r['Status']}</td>
      <td><a href="{r['ResumePDF']}">PDF</a></td>
    </tr>"""
        rows.append(row)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Batch 2 Resume Summary — 2026-06-13</title>
<style>
  body {{ font-family: Arial, sans-serif; font-size: 13px; margin: 20px; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ccc; padding: 6px 8px; vertical-align: top; }}
  th {{ background: #2c5f8a; color: white; cursor: pointer; }}
  th:hover {{ background: #1e4060; }}
  tr:nth-child(even) {{ background: #f5f5f5; }}
  tr:hover {{ background: #e8f0fe; }}
  .ok {{ color: green; font-weight: bold; }}
  .warn {{ color: #cc6600; font-weight: bold; }}
  .filters {{ margin-bottom: 12px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }}
  .filters input, .filters select {{ padding: 5px 8px; font-size: 13px; border: 1px solid #aaa; border-radius: 4px; }}
  #count {{ font-weight: bold; color: #555; }}
</style>
</head>
<body>
<h2>Batch 2 Resume Generation — 2026-06-13</h2>
<div class="filters">
  <input id="search" type="text" placeholder="Search company or title..." oninput="filterTable()">
  <select id="tplFilter" onchange="filterTable()">
    <option value="">All Templates</option>
    <option>SEP_E</option><option>SEJ_E</option><option>AI_E</option>
    <option>FS_E</option><option>FE_E</option><option>CE_E</option>
    <option>SE_LLM_E</option><option>SEP_NG</option><option>DE_E</option>
  </select>
  <select id="statusFilter" onchange="filterTable()">
    <option value="">All Statuses</option>
    <option value="ok">OK</option>
    <option value="warn">Warning</option>
  </select>
  <span id="count"></span>
</div>
<table id="resultsTable">
  <thead>
    <tr>
      <th onclick="sortTable(0)">Company</th>
      <th onclick="sortTable(1)">Title</th>
      <th onclick="sortTable(2)">Location</th>
      <th onclick="sortTable(3)">Score</th>
      <th onclick="sortTable(4)">Template</th>
      <th>Skills Added</th>
      <th>Inject Notes</th>
      <th onclick="sortTable(7)">Status</th>
      <th>PDF</th>
    </tr>
  </thead>
  <tbody>
{"".join(rows)}
  </tbody>
</table>
<script>
function filterTable() {{
  const search = document.getElementById('search').value.toLowerCase();
  const tpl = document.getElementById('tplFilter').value.toLowerCase();
  const status = document.getElementById('statusFilter').value;
  const rows = document.querySelectorAll('#resultsTable tbody tr');
  let visible = 0;
  rows.forEach(row => {{
    const company = row.dataset.company || '';
    const template = row.dataset.template || '';
    const rowStatus = row.dataset.status || '';
    const text = row.textContent.toLowerCase();
    const show = (!search || text.includes(search) || company.includes(search))
               && (!tpl || template === tpl)
               && (!status || rowStatus === status);
    row.style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  document.getElementById('count').textContent = visible + ' row(s) shown';
}}

let sortDir = {{}};
function sortTable(col) {{
  const table = document.getElementById('resultsTable');
  const tbody = table.querySelector('tbody');
  const rows = Array.from(tbody.querySelectorAll('tr'));
  const asc = sortDir[col] !== 'asc';
  sortDir[col] = asc ? 'asc' : 'desc';
  rows.sort((a, b) => {{
    const at = a.cells[col]?.textContent.trim() || '';
    const bt = b.cells[col]?.textContent.trim() || '';
    const an = parseFloat(at), bn = parseFloat(bt);
    if (!isNaN(an) && !isNaN(bn)) return asc ? an - bn : bn - an;
    return asc ? at.localeCompare(bt) : bt.localeCompare(at);
  }});
  rows.forEach(r => tbody.appendChild(r));
}}
filterTable();
</script>
</body>
</html>"""

    html_file = OUT_DIR / "batch_summary2.html"
    html_file.write_text(html, encoding="utf-8")
    print(f"Wrote HTML summary to {html_file}")

if __name__ == "__main__":
    main()
