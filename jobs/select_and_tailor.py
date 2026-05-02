#!/usr/bin/env python3
"""
1. Read 2026-05-01 jobright CSV
2. Filter all 200 (already within 7d) and bucket into AI / DE / SDE
3. Pick top 20 AI, top 40 DE (or all available), top 40 SDE
4. For each: pick best base template, copy to Company_wise_Resume/<Company>__<slug>/
5. Inject authentic missing skills into the Tools line
6. Compile to PDF (best effort; record success/fail)
7. Write summary table to jobs/2026-05-01/selection_summary.csv + .md
"""

import csv
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

ROOT = Path("/Users/ajayvenkatesh/Desktop/Resume Job Roles")
DATE = datetime.now().strftime("%Y-%m-%d")
JOBS_CSV = ROOT / "jobs" / DATE / f"{DATE}_jobright_recommendations.csv"
CWR = ROOT / "Company_wise_Resume"
OUT_CSV = ROOT / "jobs" / DATE / "selection_summary.csv"
OUT_MD  = ROOT / "jobs" / DATE / "selection_summary.md"

TARGETS = {"SDE": 40, "DE": 40, "AI": 20}

TEMPLATES = {
    "DE":   ROOT / "DE_5" / "E" / "Ajay_Venkatesh_Resume.tex",
    "AI":   ROOT / "AI_2" / "E" / "Ajay_Venkatesh_Resume.tex",
    "FE":   ROOT / "FE_8" / "E" / "Ajay_Venkatesh_Resume.tex",
    "FS":   ROOT / "FS_3" / "E" / "Ajay_Venkatesh_Resume.tex",
    "SEPY": ROOT / "SE_1" / "Python" / "E" / "Ajay_Venkatesh_Resume.tex",
    "SEJV": ROOT / "SE_1" / "Java"   / "E" / "Ajay_Venkatesh_Resume.tex",
}

AUTHENTIC_SKILLS = {
    "python", "java", "scala", "r", "sql", "c++", "typescript", "javascript",
    "es6", "nodejs", "node.js",
    "pyspark", "apache spark", "spark", "spark sql", "spark mllib", "hadoop",
    "hdfs", "pandas", "numpy", "etl", "elt", "etl/elt", "airflow",
    "data pipelines", "distributed data pipelines",
    "react", "next.js", "express", "express.js",
    "rest api", "rest", "graphql", "graphql api", "microservices", "spring boot",
    "html", "css", "websocket",
    "postgresql", "mysql", "sql server", "mongodb", "dynamodb", "firebase",
    "redis", "dataverse", "rdbms", "nosql",
    "aws", "ec2", "s3", "lambda", "api gateway", "cdk", "iam", "cloudwatch",
    "sagemaker", "redshift", "glue", "quicksight", "fargate", "ecs", "sns", "sqs",
    "azure", "data lake", "data factory", "function apps", "purview",
    "azure devops", "azure ad",
    "gcp", "bigquery",
    "llm", "llms", "rag", "langchain", "faiss", "prompt engineering",
    "pytorch", "tensorflow", "hugging face", "nlp", "deep learning",
    "computer vision", "yolov8", "efficientnet", "mlflow", "ml inference",
    "gpt-4", "gpt", "claude", "bedrock", "ai agent", "agentic", "mcp",
    "git", "docker", "kubernetes", "k8s", "ci/cd", "cicd", "jenkins", "gitlab",
    "terraform", "ansible", "powershell", "bash", "linux",
    "github copilot", "cursor", "jupyter", "postman", "datadog",
    "agile", "scrum", "tdd",
    "agile methodologies", "agile methodology", "agile development",
    "automated testing", "scalability", "monitoring", "monitoring tools",
    "json", "distributed systems", "kafka", "google cloud platform",
    "snowflake", "elasticsearch", "fastapi", "flask",
    "infrastructure as code", "infrastructure-as-code", "cloudformation",
    "retrieval-augmented generation (rag)", "retrieval-augmented generation",
    "test automation", "embeddings",
    "ai-assisted development tools", "software architecture",
    "backend development", "backend engineering", "backend systems development",
    "full stack development", "full-stack development",
    "branching strategies", "maven", "swagger",
    "oop", "design patterns", "system design", "low-level design",
    "unit testing", "integration testing", "mockito",
}

ALIASES = {
    "node.js": "Node.js", "nodejs": "Node.js",
    "es6": "JavaScript (ES6)", "javascript": "JavaScript",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    "etl/elt": "ETL/ELT", "etl": "ETL", "elt": "ELT",
    "rest": "REST API", "rest api": "REST API",
    "graphql": "GraphQL API",
    "spark": "Apache Spark", "apache spark": "Apache Spark",
    "k8s": "Kubernetes", "kubernetes": "Kubernetes",
    "pyspark": "PySpark",
    "llm": "LLMs", "llms": "LLMs",
    "rag": "RAG",
    "gpt": "GPT-4", "gpt-4": "GPT-4",
    "aws": "AWS", "ec2": "EC2", "s3": "S3", "lambda": "AWS Lambda",
    "azure": "Azure", "gcp": "GCP", "bigquery": "BigQuery",
    "sql": "SQL", "python": "Python", "java": "Java",
    "react": "React", "next.js": "Next.js",
    "docker": "Docker", "git": "Git",
    "mongodb": "MongoDB", "postgresql": "PostgreSQL", "mysql": "MySQL",
    "redis": "Redis", "dynamodb": "DynamoDB",
    "airflow": "Apache Airflow",
    "tensorflow": "TensorFlow", "pytorch": "PyTorch",
    "hugging face": "Hugging Face",
    "langchain": "LangChain",
    "agile": "Agile", "scrum": "Scrum", "tdd": "TDD",
    "agile methodologies": "Agile", "agile methodology": "Agile",
    "agile development": "Agile",
    "automated testing": "Automated Testing",
    "google cloud platform": "GCP",
    "snowflake": "Snowflake", "elasticsearch": "Elasticsearch",
    "fastapi": "FastAPI", "flask": "Flask",
    "infrastructure as code": "Infrastructure as Code",
    "infrastructure-as-code": "Infrastructure as Code",
    "cloudformation": "CloudFormation",
    "retrieval-augmented generation (rag)": "RAG",
    "retrieval-augmented generation": "RAG",
    "test automation": "Automated Testing",
    "embeddings": "Embeddings",
    "json": "JSON",
    "distributed systems": "Distributed Systems",
    "kafka": "Kafka", "maven": "Maven",
    "system design": "System Design",
    "microservices": "Microservices",
    "spring boot": "Spring Boot",
    "typescript": "TypeScript",
    "kafka": "Kafka",
    "snowflake": "Snowflake",
    "tableau": "Tableau",
    "power bi": "Power BI",
}


def categorize(title: str) -> str:
    t = title.lower()
    has_data_eng = ("data engineer" in t or "data engineering" in t or
                    "data platform" in t or "data warehouse" in t or
                    "analytics engineer" in t or "etl" in t or
                    "data conversion" in t)
    has_ai = any(k in t for k in (
        "machine learning", "ml engineer", "ai engineer", " ai/",
        "/ai", "ai/ml", "deep learning", "applied scientist",
        "research scientist", "computer vision", "nlp", "llm",
        "gen ai", "genai", "generative ai", "mlops",
    ))
    has_data_other = any(k in t for k in (
        "data scientist", "data science", "big data",
        "bi engineer", "business intelligence", "data quality",
    ))
    if has_data_eng:
        return "DE"
    if has_ai:
        return "AI"
    if has_data_other:
        return "DE"
    return "SDE"


def pick_template(title: str, bucket: str) -> str:
    t = title.lower()
    if bucket == "AI":
        return "AI"
    if bucket == "DE":
        return "DE"
    # SDE — pick sub-flavor
    if "frontend" in t or "front-end" in t or "front end" in t:
        return "FE"
    if "full stack" in t or "full-stack" in t or "fullstack" in t:
        return "FS"
    if "(java)" in t or " java " in t or t.endswith(" java") \
       or "spring" in t or "j2ee" in t:
        return "SEJV"
    if "backend" in t or "back-end" in t or "back end" in t:
        if "python" in t or "django" in t or "fastapi" in t:
            return "SEPY"
        return "SEJV"
    if "react" in t or "angular" in t or "vue" in t:
        return "FE"
    if "android" in t or "ios" in t or "mobile" in t:
        return "FS"
    return "SEPY"


def sanitize(s: str) -> str:
    s = re.sub(r"[^A-Za-z0-9_\- ]", "", s).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:60] or "Unknown"


def parse_skills(s: str) -> list[str]:
    return [x.strip() for x in (s or "").split(",") if x.strip()]


def authentic_filter(skills: list[str]) -> list[tuple[str, str]]:
    """Return list of (display, normalized) for skills that are authentic."""
    keep: list[tuple[str, str]] = []
    seen: set[str] = set()
    for raw in skills:
        norm = raw.lower().strip().rstrip(".")
        if norm in seen:
            continue
        if norm in AUTHENTIC_SKILLS:
            seen.add(norm)
            display = ALIASES.get(norm, raw.strip())
            keep.append((display, norm))
    return keep


def inject_into_skills(tex: str, missing: list[str]) -> tuple[str, list[str]]:
    """Append missing authentic skills to the Tools line.

    Supports two template flavors:
      A) \textbf{Tools:} ... [\\]
      B) \resumeSubItem{Tools \& Platforms:}{ ... }
    Skills already mentioned anywhere in the resume are skipped.
    """
    if not missing:
        return tex, []
    full_lower = tex.lower()
    to_add_global = [m for m in missing if m.lower() not in full_lower]
    if not to_add_global:
        return tex, []

    lines = tex.split("\n")
    for i, line in enumerate(lines):
        stripped = line.rstrip()

        # Flavor A: \textbf{Tools:} ...  (optional trailing \\)
        if "\\textbf{Tools" in line:
            had_slash = stripped.endswith("\\\\")
            base = stripped[:-2].rstrip() if had_slash else stripped
            base = base.rstrip().rstrip(",")
            new_line = base + ", " + ", ".join(to_add_global)
            if had_slash:
                new_line += " \\\\"
            lines[i] = new_line
            return "\n".join(lines), to_add_global

        # Flavor B: \resumeSubItem{Tools ...}{ existing }
        if "\\resumeSubItem{Tools" in line and "}{" in line and line.rstrip().endswith("}"):
            # Insert before the trailing closing brace
            idx = line.rfind("}")
            inner = line[:idx].rstrip().rstrip(",")
            lines[i] = inner + ", " + ", ".join(to_add_global) + "}"
            return "\n".join(lines), to_add_global

    return tex, []


def compile_pdf(tex_path: Path) -> bool:
    try:
        subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path.name],
            cwd=tex_path.parent, capture_output=True, timeout=60,
        )
        return tex_path.with_suffix(".pdf").exists()
    except Exception:
        return False


def cleanup_aux(folder: Path) -> None:
    for ext in (".aux", ".log", ".out", ".synctex.gz"):
        for f in folder.glob(f"*{ext}"):
            f.unlink(missing_ok=True)


def main():
    rows = list(csv.DictReader(open(JOBS_CSV)))
    for r in rows:
        try:
            r["_score"] = float(r.get("Match Score") or 0)
        except ValueError:
            r["_score"] = 0.0
        r["_bucket"] = categorize(r["Title"])

    pools = {"AI": [], "DE": [], "SDE": []}
    for r in rows:
        pools[r["_bucket"]].append(r)
    for k in pools:
        pools[k].sort(key=lambda x: -x["_score"])

    selected: list[dict] = []
    for k, n in TARGETS.items():
        chosen = pools[k][:n]
        for r in chosen:
            r["_assigned_bucket"] = k
        selected.extend(chosen)

    print(f"Pool sizes -> AI: {len(pools['AI'])}, DE: {len(pools['DE'])}, SDE: {len(pools['SDE'])}")
    print(f"Selected   -> AI: {min(len(pools['AI']), TARGETS['AI'])}, "
          f"DE: {min(len(pools['DE']), TARGETS['DE'])}, "
          f"SDE: {min(len(pools['SDE']), TARGETS['SDE'])}")

    summary_rows: list[dict] = []
    for r in selected:
        company = r["Company"].strip()
        title = r["Title"].strip()
        bucket = r["_assigned_bucket"]
        tpl_key = pick_template(title, bucket)
        tpl_path = TEMPLATES[tpl_key]

        slug = sanitize(f"{company}_{title}")
        out_dir = CWR / slug
        out_tex = out_dir / "Ajay_Venkatesh_Resume.tex"

        out_dir.mkdir(parents=True, exist_ok=True)
        # Always re-copy from template so re-runs pick up template/injection fixes.
        shutil.copy(tpl_path, out_tex)

        missing_raw = parse_skills(r.get("Missing Skills", ""))
        matched_raw = parse_skills(r.get("Matched Skills", ""))
        authentic = authentic_filter(missing_raw)
        injected: list[str] = []
        if authentic:
            tex = out_tex.read_text(encoding="utf-8")
            new_tex, injected = inject_into_skills(tex, [d for d, _ in authentic])
            if new_tex != tex:
                out_tex.write_text(new_tex, encoding="utf-8")

        ok = compile_pdf(out_tex)
        cleanup_aux(out_dir)

        summary_rows.append({
            "Bucket": bucket,
            "Score": f"{r['_score']:.2f}",
            "Company": company,
            "Title": title,
            "Template": tpl_key,
            "Folder": str(out_dir.relative_to(ROOT)),
            "URL": r.get("URL", ""),
            "Skills Added": "; ".join(injected),
            "Authentic Missing (all)": "; ".join(d for d, _ in authentic),
            "Matched (CSV)": r.get("Matched Skills", ""),
            "Compile": "OK" if ok else "FAIL",
        })

    fieldnames = [
        "Bucket", "Score", "Company", "Title", "Template",
        "Folder", "URL", "Skills Added", "Authentic Missing (all)",
        "Matched (CSV)", "Compile",
    ]
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(summary_rows)

    # Markdown table grouped by bucket
    md = ["# Resume Tailoring — " + DATE, ""]
    md.append(f"Pool: AI={len(pools['AI'])}, DE={len(pools['DE'])}, SDE={len(pools['SDE'])}")
    md.append("")
    for b in ("SDE", "DE", "AI"):
        md.append(f"## {b}")
        md.append("")
        md.append("| Score | Company | Title | Template | Skills Added | URL |")
        md.append("|------:|---------|-------|----------|--------------|-----|")
        for s in (x for x in summary_rows if x["Bucket"] == b):
            url = s["URL"]
            url_md = f"[link]({url})" if url else ""
            md.append(
                f"| {s['Score']} | {s['Company']} | {s['Title']} | "
                f"{s['Template']} | {s['Skills Added']} | {url_md} |"
            )
        md.append("")
    OUT_MD.write_text("\n".join(md), encoding="utf-8")

    fails = [s for s in summary_rows if s["Compile"] != "OK"]
    print(f"\nTotal selected: {len(summary_rows)}  | Compile fails: {len(fails)}")
    print(f"Summary CSV: {OUT_CSV}")
    print(f"Summary MD : {OUT_MD}")


if __name__ == "__main__":
    main()
