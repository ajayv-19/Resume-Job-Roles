#!/usr/bin/env python3
"""
Batch resume tailoring for top-matched Jobright recommendations.

For each top job:
  1. Pick best base template by title keywords
  2. Create Company_wise_Resume/<sanitized_company>/ folder
  3. Copy base .tex
  4. Inject MISSING keywords (from CSV) into Skills — but only if they match
     Ajay's authentic skill bank. Never fabricate.
  5. Compile to PDF

The authentic skill bank is the union of skills already present across
Ajay's base templates. Missing keywords outside this bank are dropped to
avoid resume over-fitting.
"""

import csv
import os
import re
import shutil
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JOBS_CSV = Path(__file__).resolve().parent / "last_2_days_jobs.csv"
CWR = ROOT / "Company_wise_Resume"

MIN_SCORE = 95.0

TEMPLATES = {
    "DE":   ROOT / "DE_5" / "E" / "Ajay_Venkatesh_Resume.tex",
    "AI":   ROOT / "AI_2" / "E" / "Ajay_Venkatesh_Resume.tex",
    "FE":   ROOT / "FE_8" / "E" / "Ajay_Venkatesh_Resume.tex",
    "FS":   ROOT / "FS_3" / "E" / "Ajay_Venkatesh_Resume.tex",
    "SEPY": ROOT / "SE_1" / "Python" / "E" / "Ajay_Venkatesh_Resume.tex",
    "SEJV": ROOT / "SE_1" / "Java"   / "E" / "Ajay_Venkatesh_Resume.tex",
}

# Skills Ajay legitimately has (union from existing tailored resumes).
# Used to filter missing-keyword injection. Lower-case for matching.
AUTHENTIC_SKILLS = {
    # Languages
    "python", "java", "scala", "r", "sql", "c++", "typescript", "javascript",
    "es6", "nodejs", "node.js",
    # Big Data / Processing
    "pyspark", "apache spark", "spark", "spark sql", "spark mllib", "hadoop",
    "hdfs", "pandas", "numpy", "etl", "elt", "etl/elt", "airflow",
    "data pipelines", "distributed data pipelines",
    # Web / Backend
    "react", "next.js", "express", "express.js", "node.js", "nodejs",
    "rest api", "graphql", "graphql api", "microservices", "spring boot",
    "html", "css", "websocket",
    # Databases
    "postgresql", "mysql", "sql server", "mongodb", "dynamodb", "firebase",
    "redis", "dataverse", "rdbms", "nosql",
    # Cloud
    "aws", "ec2", "s3", "lambda", "api gateway", "cdk", "iam", "cloudwatch",
    "sagemaker", "redshift", "glue", "quicksight", "fargate", "ecs", "sns", "sqs",
    "azure", "data lake", "data factory", "function apps", "purview",
    "azure devops", "azure ad",
    "gcp", "bigquery",
    # AI/ML
    "llm", "llms", "rag", "langchain", "faiss", "prompt engineering",
    "pytorch", "tensorflow", "hugging face", "nlp", "deep learning",
    "computer vision", "yolov8", "efficientnet", "mlflow", "ml inference",
    "gpt-4", "gpt", "claude", "bedrock", "ai agent", "agentic", "mcp",
    # Tools / DevOps
    "git", "docker", "kubernetes", "ci/cd", "cicd", "jenkins", "gitlab",
    "terraform", "ansible", "powershell", "bash", "linux",
    "github copilot", "cursor", "jupyter", "postman", "datadog",
    "agile", "scrum", "tdd",
    # Methodologies / patterns
    "oop", "design patterns", "system design", "low-level design",
    "unit testing", "integration testing", "mockito",
}

# Aliases — when the missing keyword in CSV uses one form but Ajay
# has the equivalent under another name.
ALIASES = {
    "node.js": "Node.js", "nodejs": "Node.js",
    "es6": "JavaScript (ES6)", "javascript": "JavaScript",
    "ci/cd": "CI/CD", "cicd": "CI/CD",
    "etl/elt": "ETL/ELT",
    "rest": "REST API", "rest api": "REST API",
    "graphql": "GraphQL API",
    "spark": "Apache Spark",
    "k8s": "Kubernetes", "kubernetes": "Kubernetes",
    "pyspark": "PySpark",
    "llm": "LLMs", "llms": "LLMs",
    "rag": "RAG",
}


def pick_template(title: str) -> str:
    t = title.lower()
    if any(k in t for k in ("data engineer", "analytics engineer", "big data",
                             "bi engineer", "business intelligence", "data quality")):
        return "DE"
    if any(k in t for k in ("data science", "data scientist")):
        return "DE"
    if any(k in t for k in ("ai engineer", "ml engineer", "machine learning",
                             "mlops", "/ai", "ai engineering", "ai/ml")):
        return "AI"
    if "frontend" in t or "front-end" in t or "front end" in t:
        return "FE"
    if "full stack" in t or "full-stack" in t or "fullstack" in t:
        return "FS"
    if "backend" in t or "back-end" in t or "back end" in t:
        return "SEJV"
    if "(java)" in t or " java " in t or t.endswith(" java"):
        return "SEJV"
    if "react" in t:
        return "FE"
    return "SEPY"


def sanitize_name(company: str) -> str:
    """Folder-safe company name."""
    s = re.sub(r"[^A-Za-z0-9_\- ]", "", company).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:60] or "Unknown"


def parse_missing_skills(s: str) -> list[str]:
    if not s:
        return []
    return [k.strip() for k in s.split(",") if k.strip()]


def filter_authentic(missing: list[str]) -> list[str]:
    """Keep only missing keywords that are authentic to Ajay."""
    keep = []
    seen = set()
    for raw in missing:
        norm = raw.lower().strip().rstrip(".")
        if norm in seen:
            continue
        if norm in AUTHENTIC_SKILLS:
            display = ALIASES.get(norm, raw.strip())
            keep.append(display)
            seen.add(norm)
    return keep


def already_in_skills(tex: str, kw: str) -> bool:
    return kw.lower() in tex.lower()


def inject_missing_into_skills(tex: str, missing: list[str]) -> str:
    """Append missing authentic skills to the Tools line. Line-based for robustness."""
    if not missing:
        return tex
    lines = tex.split("\n")
    for i, line in enumerate(lines):
        if "\\textbf{Tools" in line and line.rstrip().endswith("\\\\"):
            existing_lower = line.lower()
            to_add = [m for m in missing if m.lower() not in existing_lower]
            if not to_add:
                return tex
            base = line.rstrip()[:-2].rstrip().rstrip(",")
            lines[i] = base + ", " + ", ".join(to_add) + " \\\\"
            return "\n".join(lines)
    return tex


def compile_pdf(tex_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["pdflatex", "-interaction=nonstopmode", tex_path.name],
            cwd=tex_path.parent, capture_output=True, timeout=60
        )
        return (tex_path.parent / tex_path.with_suffix(".pdf").name).exists()
    except Exception as e:
        print(f"   compile error: {e}")
        return False


def cleanup_aux(folder: Path) -> None:
    for ext in (".aux", ".log", ".out", ".synctex.gz"):
        for f in folder.glob(f"*{ext}"):
            f.unlink(missing_ok=True)


def main():
    with open(JOBS_CSV) as f:
        rows = list(csv.DictReader(f))

    top = []
    for r in rows:
        try:
            score = float(r.get("Match Score", 0) or 0)
        except ValueError:
            continue
        if score >= MIN_SCORE:
            top.append(r)

    print(f"=== Tailoring {len(top)} resumes (score >= {MIN_SCORE}) ===\n")

    counts = {"created": 0, "skipped_existing": 0, "compile_fail": 0}
    summary = []

    for j in top:
        company = j["Company"].strip()
        title = j["Title"].strip()
        score = j["Match Score"]
        tpl_key = pick_template(title)
        tpl_path = TEMPLATES[tpl_key]

        folder_name = sanitize_name(company)
        out_dir = CWR / folder_name
        out_tex = out_dir / "Ajay_Venkatesh_Resume.tex"

        if out_dir.exists() and out_tex.exists():
            counts["skipped_existing"] += 1
            summary.append((score, company, title, tpl_key, "EXISTS"))
            continue

        out_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy(tpl_path, out_tex)

        # Inject missing-skill keywords (filtered to authentic)
        missing = parse_missing_skills(j.get("Missing Skills", ""))
        authentic = filter_authentic(missing)
        if authentic:
            tex = out_tex.read_text(encoding="utf-8")
            new_tex = inject_missing_into_skills(tex, authentic)
            if new_tex != tex:
                out_tex.write_text(new_tex, encoding="utf-8")

        ok = compile_pdf(out_tex)
        cleanup_aux(out_dir)

        if ok:
            counts["created"] += 1
            summary.append((score, company, title, tpl_key, "OK"))
        else:
            counts["compile_fail"] += 1
            summary.append((score, company, title, tpl_key, "COMPILE_FAIL"))

    # Print summary
    print(f"\nResults: {counts}\n")
    print(f"{'Score':>7} | {'Company':35} | {'Template':6} | {'Title':50} | Status")
    print("-" * 130)
    for score, company, title, tpl, status in sorted(
        summary, key=lambda x: -float(x[0])
    ):
        print(f"{score:>7} | {company[:35]:35} | {tpl:6} | {title[:50]:50} | {status}")


if __name__ == "__main__":
    main()
