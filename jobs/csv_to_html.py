#!/usr/bin/env python3
"""Convert selection_summary.csv to a sortable + per-column filterable HTML table."""

import csv
import html
import json
from datetime import datetime
from pathlib import Path

DATE = datetime.now().strftime("%Y-%m-%d")
ROOT = Path("/Users/ajayvenkatesh/Desktop/Resume Job Roles")
SRC = ROOT / "jobs" / DATE / "selection_summary.csv"
OUT = ROOT / "jobs" / DATE / "selection_summary.html"

with open(SRC, encoding="utf-8") as f:
    rows = list(csv.DictReader(f))

# Make folder paths into clickable file:// links + open the local PDF
for r in rows:
    folder = r.get("Folder", "")
    pdf_path = (ROOT / folder / "Ajay_Venkatesh_Resume.pdf").resolve()
    r["Resume PDF"] = str(pdf_path)

cols = [
    "Bucket", "Score", "Company", "Title", "Template",
    "Skills Added", "Authentic Missing (all)", "Matched (CSV)",
    "Compile", "URL", "Resume PDF",
]

def cell(col: str, val: str) -> str:
    if col == "URL" and val:
        return f'<a href="{html.escape(val)}" target="_blank">apply</a>'
    if col == "Resume PDF" and val:
        return f'<a href="file://{html.escape(val)}" target="_blank">PDF</a>'
    if col == "Score":
        return html.escape(val)
    return html.escape(val or "")

body_rows = []
for r in rows:
    tds = "".join(f"<td data-col='{c}'>{cell(c, r.get(c, ''))}</td>" for c in cols)
    body_rows.append(f"<tr data-bucket='{html.escape(r['Bucket'])}'>{tds}</tr>")

header = "".join(
    f"<th data-col='{c}'>{html.escape(c)}<span class='sort-ind'></span>"
    f"<br><input class='filter' data-col='{c}' placeholder='filter…'></th>"
    for c in cols
)

html_doc = f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Resume Tailoring — {DATE}</title>
<style>
  body {{ font: 13px/1.4 -apple-system, BlinkMacSystemFont, sans-serif; margin: 16px; }}
  h1 {{ font-size: 18px; margin: 0 0 8px; }}
  .meta {{ color: #555; margin-bottom: 12px; }}
  .controls {{ margin-bottom: 8px; }}
  .controls button {{ font: inherit; padding: 4px 10px; margin-right: 6px; cursor: pointer; }}
  .controls button.active {{ background: #1f6feb; color: #fff; border-color: #1f6feb; }}
  table {{ border-collapse: collapse; width: 100%; }}
  th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
  th {{ background: #f4f6f8; text-align: left; position: sticky; top: 0; cursor: pointer; user-select: none; }}
  th input.filter {{ width: 95%; font: 11px sans-serif; padding: 2px; margin-top: 2px; box-sizing: border-box; }}
  tr:nth-child(even) td {{ background: #fafbfc; }}
  td[data-col="Title"] {{ max-width: 320px; }}
  td[data-col="Skills Added"], td[data-col="Authentic Missing (all)"], td[data-col="Matched (CSV)"] {{ max-width: 240px; font-size: 12px; color: #333; }}
  .badge {{ display: inline-block; padding: 1px 6px; border-radius: 9px; font-size: 11px; font-weight: 600; }}
  .b-SDE {{ background: #dbe9ff; color: #1f4fb6; }}
  .b-DE  {{ background: #d9f1e0; color: #1d7a3e; }}
  .b-AI  {{ background: #fde2c5; color: #9a4c00; }}
  .sort-ind {{ float: right; opacity: .5; font-size: 10px; }}
  #count {{ margin-left: 8px; color: #555; }}
</style>
</head>
<body>
<h1>Resume Tailoring — {DATE}</h1>
<div class="meta">
  Selected {len(rows)} jobs across SDE / DE / AI from 200-job recommendation pull (last 7 days).
  Click headers to sort. Filters in each header column. Bucket buttons below filter buckets quickly.
</div>
<div class="controls">
  <button data-bucket="ALL" class="active">All ({len(rows)})</button>
  <button data-bucket="SDE">SDE ({sum(1 for r in rows if r['Bucket']=='SDE')})</button>
  <button data-bucket="DE">DE ({sum(1 for r in rows if r['Bucket']=='DE')})</button>
  <button data-bucket="AI">AI ({sum(1 for r in rows if r['Bucket']=='AI')})</button>
  <span id="count"></span>
</div>
<table id="t">
  <thead><tr>{header}</tr></thead>
  <tbody>
    {"".join(body_rows)}
  </tbody>
</table>
<script>
const cols = {json.dumps(cols)};
const tbody = document.querySelector('#t tbody');
const allRows = Array.from(tbody.querySelectorAll('tr'));
const filters = {{}};
let bucketFilter = 'ALL';
let sortCol = 'Score', sortDir = -1;

// Decorate Bucket cell with a badge
allRows.forEach(tr => {{
  const td = tr.querySelector('td[data-col="Bucket"]');
  const b = td.textContent.trim();
  td.innerHTML = `<span class="badge b-${{b}}">${{b}}</span>`;
}});

function apply() {{
  let visible = 0;
  allRows.forEach(tr => {{
    const bucket = tr.dataset.bucket;
    if (bucketFilter !== 'ALL' && bucket !== bucketFilter) {{ tr.style.display = 'none'; return; }}
    let show = true;
    for (const c of cols) {{
      const f = (filters[c] || '').toLowerCase();
      if (!f) continue;
      const td = tr.querySelector(`td[data-col="${{c}}"]`);
      const val = (td.textContent || '').toLowerCase();
      if (!val.includes(f)) {{ show = false; break; }}
    }}
    tr.style.display = show ? '' : 'none';
    if (show) visible++;
  }});
  document.getElementById('count').textContent = `Showing ${{visible}} / ${{allRows.length}}`;
}}

document.querySelectorAll('input.filter').forEach(inp => {{
  inp.addEventListener('input', e => {{
    e.stopPropagation();
    filters[inp.dataset.col] = inp.value;
    apply();
  }});
  inp.addEventListener('click', e => e.stopPropagation());
}});

document.querySelectorAll('.controls button').forEach(b => {{
  b.addEventListener('click', () => {{
    bucketFilter = b.dataset.bucket;
    document.querySelectorAll('.controls button').forEach(x => x.classList.remove('active'));
    b.classList.add('active');
    apply();
  }});
}});

document.querySelectorAll('th').forEach(th => {{
  th.addEventListener('click', () => {{
    const c = th.dataset.col;
    if (sortCol === c) sortDir = -sortDir; else {{ sortCol = c; sortDir = 1; }}
    const numeric = (c === 'Score');
    const sorted = allRows.slice().sort((a, b) => {{
      const av = a.querySelector(`td[data-col="${{c}}"]`).textContent.trim();
      const bv = b.querySelector(`td[data-col="${{c}}"]`).textContent.trim();
      if (numeric) return (parseFloat(av) - parseFloat(bv)) * sortDir;
      return av.localeCompare(bv) * sortDir;
    }});
    tbody.innerHTML = '';
    sorted.forEach(r => tbody.appendChild(r));
    document.querySelectorAll('th .sort-ind').forEach(s => s.textContent = '');
    th.querySelector('.sort-ind').textContent = sortDir === 1 ? '▲' : '▼';
  }});
}});

apply();
</script>
</body>
</html>"""

OUT.write_text(html_doc, encoding="utf-8")
print(f"Wrote {OUT}")
print(f"Open: file://{OUT}")
