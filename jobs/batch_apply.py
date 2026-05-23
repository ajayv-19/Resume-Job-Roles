#!/usr/bin/env python3
"""Batch-tailor resumes from a date-folder JSON.

Usage:
    python3 jobs/batch_apply.py <date_folder> [<json_filename>]
    e.g. python3 jobs/batch_apply.py 18052026 jobs.json

For each role in the JSON:
  1. Read BaseTemplate code, normalize via TEMPLATE_ALIAS, resolve to .tex path
  2. Copy template into <date>/<Company>/Ajay_Venkatesh_Resume.tex
  3. Classify each MissingSkill → skills-section line OR bullet edit OR skip
  4. Inject + compile to PDF
  5. Output HTML table + JSON summary
"""

import csv
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path("/Users/ajayvenkatesh/Desktop/Resume Job Roles")

DATE = sys.argv[1] if len(sys.argv) > 1 else "18052026"
JSON_FILE = sys.argv[2] if len(sys.argv) > 2 else "jobs.json"
OUT_DIR = ROOT / DATE
OUT_DIR.mkdir(exist_ok=True)
JSON_IN = OUT_DIR / JSON_FILE

TEMPLATES = {
    "SEP_E":  ROOT / "SE/P/E/Ajay_Venkatesh_Resume.tex",
    "SEP_NG": ROOT / "SE/P/NG/Ajay_Venkatesh_Resume.tex",
    "SEP_L":  ROOT / "SE/P/L/Ajay_Venkatesh_Resume.tex",
    "SEJ_E":  ROOT / "SE/J/E/Ajay_Venkatesh_Resume.tex",
    "SEJ_NG": ROOT / "SE/J/NG/Ajay_Venkatesh_Resume.tex",
    "SEJ_L":  ROOT / "SE/J/L/Ajay_Venkatesh_Resume.tex",
    "SEAI_E": ROOT / "SE_AI/E/Ajay_Venkatesh_Resume.tex",
    "SELLM_E":ROOT / "SE_LLM/E/Ajay_Venkatesh_Resume.tex",
    "AI_E":   ROOT / "AI/E/Ajay_Venkatesh_Resume.tex",
    "AI_NG":  ROOT / "AI/NG/Ajay_Venkatesh_Resume.tex",
    "AI_L":   ROOT / "AI/L/Ajay_Venkatesh_Resume.tex",
    "DE_E":   ROOT / "DE/E/Ajay_Venkatesh_Resume.tex",
    "FE_E":   ROOT / "FE/E/Ajay_Venkatesh_Resume.tex",
    "FS_E":   ROOT / "FS/E/Ajay_Venkatesh_Resume.tex",
    "FS_L":   ROOT / "FS/L/Ajay_Venkatesh_Resume.tex",
    "CE_E":   ROOT / "CE/E/Ajay_Venkatesh_Resume.tex",
}

TEMPLATE_ALIAS = {
    "SE": "SEP_E", "SE_E": "SEP_E", "SE_P_E": "SEP_E", "SE_Python_E": "SEP_E",
    "SE_python_E": "SEP_E", "SEPY": "SEP_E", "SEP": "SEP_E",
    "SE_PY_E": "SEP_E", "SEP_E_E": "SEP_E",
    "SE_Java_E": "SEJ_E", "SE_J_E": "SEJ_E", "SE_Java": "SEJ_E",
    "SE_java": "SEJ_E", "SE_java_E": "SEJ_E", "SE/J?E": "SEJ_E",
    "SEP_Java": "SEJ_E", "SEJ": "SEJ_E", "SE_JAva_E": "SEJ_E", "SE_JAva": "SEJ_E",
    "SEJV": "SEJ_E", "SEJA": "SEJ_E", "SEJavaE": "SEJ_E",
    "SE_AI": "SEAI_E", "SEAI": "SEAI_E",
    "SE_LLM": "SELLM_E", "SELLM": "SELLM_E", "SE_LLM_E": "SELLM_E",
    "AI": "AI_E", "DE": "DE_E", "FE": "FE_E", "FS": "FS_E", "CE": "CE_E",
    "FS_NG": "FS_E",  # FS/NG template folder is empty — fallback to FS_E
}

# Inauthentic — never inject (note: programming languages REMOVED per user rule —
# Go, Kotlin, Rust, VB.NET, COBOL etc. are ALWAYS added to Programming Languages
# line when JD requires them, regardless of industry experience)
SKIP_INAUTHENTIC = {s.lower() for s in [
    "Robot Operating System", "ROS", "Embedded systems",
    "Hardware acceleration", "Confidential computing", "TEEs",
    "Computational linguistics", "Language data collection",
    "Multimodal data processing", "Redfish API",
    "Mainframe", "Buy Side Financial Firm experience",
    "NIST 800-171 Compliance", "CMMC Compliance", "DevSecOps",
    "HubSpot", "Apollo", "Outreach", "Salesforce",
    "Outbound automation platforms", "Outbound", "GTM systems",
    "Revenue operations", "Growth engineering", "Email deliverability",
    "Webpack", "Dbt", "dbt",
]}

# Concept fluff / soft / generic — skip in skills section
SKIP_CONCEPT = {s.lower() for s in [
    "Highly available distributed systems", "Message-oriented middleware",
    "Model robustness", "Explainability", "Training optimization",
    "Empathy", "Communication", "Leadership", "Collaboration",
    "Curiosity", "Quality-first mindset", "Analytical skills",
    "Bias toward action", "High agency",
    "Cloud deployment", "Cloud Deployments", "Backend development", "Frontend development",
    "Full-stack development", "Full Stack Development",
    "Service-oriented architectures", "Database technologies",
    "End-to-end testing", "Frontend frameworks", "Code documentation",
    "Test automation", "Performance optimization",
    "Source-control workflows", "Complexity analysis", "Code review",
    "Documentation", "Mentoring", "User feedback gathering",
    "Customer service", "Software security measures",
    "DevOps tools", "Microservices testing", "RESTful API testing",
    "Web application testing", "Service-to-service communication",
    "SQA Methodologies", "Software design patterns",
    "Machine learning concepts", "Pre-training methods",
    "Software architecture", "Code optimization",
    "Algorithm optimization", "Distributed Computing",
    "Asynchronous Systems", "Real-time Systems", "Streaming APIs",
    "Low-latency APIs", "Product Quality Focus",
    "Concurrency", "Reliability", "Scalability",
    "Optimization", "Optimised", "Distributed",
    "High level design", "System design", "Scalable system",
    "Eagerness to learn", "Pipeline Management",
    "AI automation workflows", "AI scripting", "Enterprise automation integration",
    "Data Lake Management", "Data Warehouse Management", "Code Quality",
    "AI integration", "Cloud-native services", "Quality Assurance",
    "Independent thinking", "Problem solving", "Critical thinking",
    "Self-starter", "Team player", "Time management",
    "Project management", "Stakeholder management",
    "Methodologies", "Best practices", "Standards compliance",
    "Software Development Lifecycle",  # bullet-only
    "Agile project management", "Agile development", "Agile/Scrum",
    "Kanban", "Behavior Driven Development", "Test Driven Development",
    "Concourse",  # niche
]}

# Concept phrases woven into bullets — REWRITES MUST PARAPHRASE.
# Never use 3+ consecutive words from the JD's exact phrase in the replacement.
# Per memory rule feedback_paraphrase_bullets.md: bullets describe the WORK in
# different language; the Skills line keeps the exact keyword for ATS matching.
BULLET_EDITS = [
    # "Data Processing" → describe the work, don't echo the phrase
    ("data processing", [
        ("Optimized data ingestion with \\textbf{parallel processing} on \\textbf{100K-row} Excel feeds",
         "Parallelized large-scale ingestion across \\textbf{100K-row} Excel feeds, cutting transformation runtime from \\textbf{5 hours to 1}"),
        ("Optimized data ingestion with \\textbf{parallel processing} for \\textbf{100K}-row from Excel",
         "Parallelized large-scale ingestion across \\textbf{100K-row} Excel feeds, cutting transformation runtime from \\textbf{5 hours to 1}"),
    ]),
    # "Data Modeling" → describe schema design / relational design
    ("data modeling", [
        ("Engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into \\textbf{PostgreSQL} with \\textbf{concurrency control and locking}",
         "Designed normalized schemas and engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into \\textbf{PostgreSQL} with \\textbf{concurrency control and locking}"),
    ]),
    # "Distributed System Design" / "Distributed Systems Debugging" → mention multi-service flows
    ("distributed system design", [
        ("Engineered the backend services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR); applied \\textbf{low-level design patterns}",
         "Engineered backend services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR) spanning multiple service tiers with \\textbf{low-level design patterns}"),
        ("Engineered backend services in \\textbf{Java} using \\textbf{Coral, Smithy, Dagger}, and \\textbf{CBOR serialization}",
         "Engineered backend services in \\textbf{Java} using \\textbf{Coral, Smithy, Dagger}, and \\textbf{CBOR serialization} across multiple service tiers"),
    ]),
    ("distributed systems debugging", [
        ("Led code reviews and mentored engineers on \\textbf{software design principles}",
         "Led code reviews, mentored engineers on \\textbf{software design principles}, and diagnosed production incidents across multi-service flows via logs, metrics, and traces"),
    ]),
    # "Event-driven X" → describe async / pub-sub work
    ("event-driven architecture", [
        ("Developed a distributed backend on \\textbf{Microsoft Azure} for a health platform integrating with \\textbf{Microsoft CRM}, with event-driven processing and fault-tolerant retries",
         "Developed a distributed backend on \\textbf{Microsoft Azure} for a health platform integrating with \\textbf{Microsoft CRM}, with asynchronous message processing and fault-tolerant retries"),
    ]),
    ("event-driven systems", [
        ("Developed a distributed backend on \\textbf{Microsoft Azure} for a health platform integrating with \\textbf{Microsoft CRM}, with event-driven processing and fault-tolerant retries",
         "Developed a distributed backend on \\textbf{Microsoft Azure} for a health platform integrating with \\textbf{Microsoft CRM}, with asynchronous message processing and fault-tolerant retries"),
    ]),
    # "Batch Processing" → describe bulk ingestion
    ("batch processing", [
        ("Optimized data ingestion with \\textbf{parallel processing} for \\textbf{100K}-row from Excel",
         "Optimized bulk ingestion of \\textbf{100K-row} Excel feeds with parallel execution, cutting runtime from \\textbf{5 hours to 1}"),
        ("Optimized data ingestion with \\textbf{parallel processing} on \\textbf{100K-row} Excel feeds",
         "Optimized bulk ingestion of \\textbf{100K-row} Excel feeds with parallel execution, cutting runtime from \\textbf{5 hours to 1}"),
    ]),
    # "Query Optimization" / "Database Optimization"
    ("query optimization", [
        ("Engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into \\textbf{PostgreSQL} with \\textbf{concurrency control and locking}",
         "Engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into \\textbf{PostgreSQL} with \\textbf{concurrency control and locking}, tuning hot-path queries to reduce response times"),
    ]),
    ("database optimization", [
        ("Engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into \\textbf{PostgreSQL} with \\textbf{concurrency control and locking}",
         "Engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into \\textbf{PostgreSQL} with \\textbf{concurrency control and locking}, tuning indexes and hot-path queries"),
    ]),
    # "Performance Optimization" → describe latency / throughput improvements
    ("performance optimization", [
        ("Built a \\textbf{React 18} frontend with optimized API integration, advanced filtering, and client-side caching",
         "Built a \\textbf{React 18} frontend with caching, request batching, and prefetching to reduce response latency"),
    ]),
    # "High Availability"
    ("high availability", []),  # already in Amazon ECS 99.9% bullet
    # "Software Development Lifecycle" / SDLC
    ("software development lifecycle", [
        ("Led code reviews and mentored engineers on \\textbf{software design principles}",
         "Owned features from requirements through deployment and on-call support, and mentored engineers on \\textbf{software design principles}"),
    ]),
    ("sdlc", [
        ("Led code reviews and mentored engineers on \\textbf{software design principles}",
         "Owned features from requirements through deployment and on-call support, and mentored engineers on \\textbf{software design principles}"),
    ]),
    # "B2B Software" / "Full Stack Engineering"
    ("b2b software development", [
        ("Developed an insurance analytics platform (\\textbf{React, Node.js, REST APIs}) deployed via \\textbf{Docker} on \\textbf{EC2}; implemented Stripe billing, RBAC, and row-level security",
         "Built a B2B-facing insurance analytics platform (\\textbf{React, Node.js, REST APIs}) deployed via \\textbf{Docker} on \\textbf{EC2}; implemented Stripe billing, RBAC, and row-level security"),
    ]),
    ("full stack engineering", [
        ("Developed an insurance analytics platform (\\textbf{React, Node.js, REST APIs}) deployed via \\textbf{Docker} on \\textbf{EC2}; implemented Stripe billing, RBAC, and row-level security",
         "Built an end-to-end insurance analytics platform (\\textbf{React, Node.js, REST APIs}) deployed via \\textbf{Docker} on \\textbf{EC2}; implemented Stripe billing, RBAC, and row-level security"),
    ]),
    # "Real-time Processing" / "Stream Processing"
    ("real-time processing", []),  # Campus Mesh real-time bullet already covers
    ("stream processing", [
        ("Developed scalable \\textbf{Node.js microservices} powering real-time academic workflows",
         "Developed scalable \\textbf{Node.js microservices} powering low-latency streaming workflows"),
    ]),
    # "Code Quality" / "Test-Driven Development"
    ("code quality", [
        ("Engineered the backend services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR); applied \\textbf{low-level design patterns}, cutting backend execution time by \\textbf{35\\%} with unit/integration testing via \\textbf{Mockito}",
         "Engineered the backend services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR); applied \\textbf{low-level design patterns} and rigorous test coverage, cutting backend execution time by \\textbf{35\\%} with unit/integration testing via \\textbf{Mockito}"),
    ]),
    # "API Design"
    ("api design", [
        ("Provisioned \\textbf{serverless Infrastructure-as-Code} using \\textbf{AWS CDK} with API Gateway, Lambda, DynamoDB, S3, and IAM",
         "Designed REST contracts and provisioned \\textbf{serverless Infrastructure-as-Code} using \\textbf{AWS CDK} with API Gateway, Lambda, DynamoDB, S3, and IAM"),
    ]),
    # "Microservices Architecture" — implicit; no edit needed unless specifically called out
    ("infrastructure as code", []),  # already in Amazon CDK bullet
]

# Category buckets for routing skills to Skills section lines
PROGRAMMING = {"python", "java", "c++", "c#", "c", "go", "golang", "ruby", "rust", "scala",
               "typescript", "javascript", "kotlin", "vb.net", "cobol",
               "r", "sql", "swift", "perl", "bash", "php", "objective-c", "dart",
               "haskell", "groovy", "matlab", "lua"}
WEB_BACKEND = {"react", "react.js", "next.js", "node.js", "nodejs", "express",
               "express.js", "django", "flask", "fastapi", "spring boot", "spring",
               "spring mvc", "java ee", "rest api", "rest apis", "restful apis",
               "graphql", "microservices", "html", "css", "vue", "angular",
               "redux", "context api", "nest.js", "nestjs", "rails", "swagger"}
DATABASES = {"mysql", "postgresql", "mongodb", "dynamodb", "redis", "snowflake",
             "bigquery", "cloudsql", "elasticsearch", "elastic", "cassandra",
             "neo4j", "oracle", "sql server", "microsoftsql", "firebase",
             "couchbase", "vector databases", "rdbms", "nosql"}
CLOUD_DEVOPS = {"aws", "aws bedrock", "aws sagemaker", "aws rds", "aws sqs",
                "aws sns", "aws cloudwatch", "aws lambda", "aws ec2", "aws s3",
                "aws iam", "aws cdk", "aws ecs", "aws fargate", "aws glue",
                "aws athena", "aws api gateway", "azure", "azure functions",
                "azure logic apps", "azure ai services", "azure devops", "azure ad",
                "gcp", "google cloud platform", "terraform", "cloudformation",
                "docker", "kubernetes", "k8s", "helm", "jenkins", "github actions",
                "gitlab ci", "circleci", "argo", "argocd", "ci/cd", "kafka",
                "rabbitmq", "kinesis", "grpc"}
AI_ML = {"pytorch", "tensorflow", "langchain", "langgraph", "llamaindex", "faiss",
         "bedrock", "hugging face", "huggingface", "mlflow", "mlops", "rag",
         "llm", "llms", "agentic ai", "agentic", "mcp", "fine-tuning",
         "prompt engineering", "embedding models", "embeddings",
         "computer vision", "nlp", "deep learning", "transformers",
         "scikit-learn", "pandas", "numpy", "openai", "anthropic",
         "strands agents", "jax", "dynamo"}
TOOLS = {"git", "github", "gitlab", "bitbucket", "jira", "datadog", "splunk",
         "postman", "stripe", "sso", "oauth", "saml", "power bi", "tableau",
         "looker", "quicksight", "dax", "cursor", "github copilot", "jupyter",
         "visual studio", "linux", "vim", "vscode", "intellij", "cloudsmith"}


def normalize_template(code: str) -> str:
    return TEMPLATE_ALIAS.get(code, code)


def classify(skill: str) -> tuple[str, str | None]:
    s = skill.lower().strip()
    if s in SKIP_INAUTHENTIC or s in SKIP_CONCEPT:
        return ("skip", None)
    for phrase, _ in BULLET_EDITS:
        if phrase == s or phrase in s:
            return ("bullet", phrase)
    # Skills-section category routing
    for cat_set, cat_name in [
        (PROGRAMMING, "Programming"), (WEB_BACKEND, "Web"), (DATABASES, "Database"),
        (CLOUD_DEVOPS, "Cloud"), (AI_ML, "AI/ML"), (TOOLS, "Tools"),
    ]:
        if s in cat_set:
            return ("skills", cat_name)
    # Loose substring fallback
    for cat_set, cat_name in [(CLOUD_DEVOPS, "Cloud"), (DATABASES, "Database"),
                              (WEB_BACKEND, "Web"), (AI_ML, "AI/ML")]:
        for kw in cat_set:
            if kw in s:
                return ("skills", cat_name)
    # Default to Tools if it looks like a named product
    if re.match(r"^[A-Za-z][\w\.\-]*$", skill.strip()) and len(skill) < 25:
        return ("skills", "Tools")
    return ("skip", None)


def latex_escape(s: str) -> str:
    """Escape LaTeX special characters that show up in skill names.
    The full set is # $ % & _ { } ~ ^ \\ — for skill names we mainly worry about
    # (C#), & (Q&A-style), % (rare), _ (rare). Don't escape characters that are
    already preceded by a backslash."""
    out = []
    i = 0
    while i < len(s):
        ch = s[i]
        if ch in {"#", "$", "%", "&", "_"}:
            # Don't double-escape if already escaped
            if i > 0 and s[i - 1] == "\\":
                out.append(ch)
            else:
                out.append("\\" + ch)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


def inject_skills_line(text: str, prefix: str, items: list[str]) -> tuple[str, list[str]]:
    body_lower = text.lower()
    # Word-boundary check so short tokens like "Go" don't match "MongoDB"/"Django"
    def already_present(item: str) -> bool:
        i = item.lower()
        return bool(re.search(rf"(?<![a-z0-9+#]){re.escape(i)}(?![a-z0-9+#])", body_lower))
    items = [i for i in items if not already_present(i)]
    if not items:
        return text, []
    # LaTeX-escape items before injection (e.g., C# → C\#, Q&A → Q\&A)
    escaped_items = [latex_escape(i) for i in items]
    first_word = prefix.split()[0]
    pat_b = rf"(\\resumeSubItem\{{[^}}]*?{re.escape(first_word)}[^}}]*?:\}}\{{[^}}]*?)(\}})"
    pat_a = rf"(\\textbf\{{[^}}]*?{re.escape(first_word)}[^}}]*?:\}}[^\n]*?)( ?\\\\)"
    for pat in (pat_b, pat_a):
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            new = re.sub(pat, lambda mm: mm.group(1).rstrip().rstrip(",") + ", " + ", ".join(escaped_items) + mm.group(2),
                         text, count=1, flags=re.IGNORECASE)
            return new, items  # report unescaped names to caller
    # Fallback to Tools line
    if first_word != "Tools":
        return inject_skills_line(text, "Tools", items)
    return text, []


CATEGORY_LINES = {"Programming": "Programming Languages", "Web": "Web",
                  "Database": "Database", "Cloud": "Cloud", "AI/ML": "AI/ML",
                  "Tools": "Tools"}


def apply_bullet_edit(text: str, phrase: str) -> tuple[str, str | None]:
    edits = next((e for p, e in BULLET_EDITS if p == phrase), [])
    for find, repl in edits:
        if find in text:
            return text.replace(find, repl, 1), phrase
    return text, None


def process_role(role: dict) -> dict:
    company = role.get("Company", "Unknown")
    title = role.get("Title", "Unknown")
    tpl_code = normalize_template(role.get("BaseTemplate", "SEP_E"))
    if tpl_code not in TEMPLATES:
        return {"Company": company, "Title": title, "Template": role.get("BaseTemplate"),
                "Compile": "FAIL", "Error": f"Unknown template {tpl_code}",
                "JobLink": role.get("JobLink", ""), "PDF": "",
                "SkillsAdded": [], "BulletsChanged": [], "Skipped": []}

    slug = re.sub(r"[^\w\-]+", "_", company).strip("_")[:60]
    folder = OUT_DIR / slug
    folder.mkdir(exist_ok=True)
    tex = folder / "Ajay_Venkatesh_Resume.tex"
    shutil.copy(TEMPLATES[tpl_code], tex)

    text = tex.read_text(encoding="utf-8")
    skills_groups = {k: [] for k in CATEGORY_LINES}
    bullet_phrases = []
    skipped = []
    for s in role.get("MissingSkills", []):
        kind, target = classify(s)
        if kind == "skip":
            skipped.append(s)
        elif kind == "bullet":
            bullet_phrases.append((s, target))
        elif kind == "skills":
            skills_groups[target].append(s)

    skills_added = []
    for cat, items in skills_groups.items():
        if not items:
            continue
        text, added = inject_skills_line(text, CATEGORY_LINES[cat], items)
        skills_added.extend(added)

    bullets_changed = []
    for original, phrase in bullet_phrases:
        text, applied = apply_bullet_edit(text, phrase)
        if applied:
            bullets_changed.append(original)

    tex.write_text(text, encoding="utf-8")
    subprocess.run(["pdflatex", "-interaction=nonstopmode", "Ajay_Venkatesh_Resume.tex"],
                   cwd=folder, capture_output=True, timeout=60)
    for ext in (".aux", ".log", ".out"):
        (folder / f"Ajay_Venkatesh_Resume{ext}").unlink(missing_ok=True)
    pdf_ok = (folder / "Ajay_Venkatesh_Resume.pdf").exists()

    return {
        "Company": company,
        "Title": title,
        "Template": tpl_code,
        "MatchScore": role.get("MatchScore"),
        "JobLink": role.get("JobLink", ""),
        "PDF": str((folder / "Ajay_Venkatesh_Resume.pdf").relative_to(ROOT)),
        "SkillsAdded": skills_added,
        "BulletsChanged": bullets_changed,
        "Skipped": skipped,
        "Compile": "OK" if pdf_ok else "FAIL",
    }


def escape(s):
    if not isinstance(s, str):
        s = str(s)
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def write_html(results: list[dict], out: Path):
    rows = []
    for r in results:
        skills = "; ".join(r.get("SkillsAdded", [])) or ""
        bullets = "; ".join(r.get("BulletsChanged", [])) or ""
        skipped = "; ".join(r.get("Skipped", [])) or ""
        pdf_path = (ROOT / r["PDF"]).resolve() if r.get("PDF") else ""
        rows.append(
            f"<tr data-key='{escape(r['JobLink'])}'>"
            f"<td data-col='Template'>{escape(r['Template'])}</td>"
            f"<td data-col='Company'>{escape(r['Company'])}</td>"
            f"<td data-col='Title'>{escape(r['Title'])}</td>"
            f"<td data-col='Score'>{r.get('MatchScore','') or ''}</td>"
            f"<td data-col='SkillsAdded'>{escape(skills)}</td>"
            f"<td data-col='BulletsChanged'>{escape(bullets)}</td>"
            f"<td data-col='Skipped'>{escape(skipped)}</td>"
            f"<td data-col='Compile'>{escape(r['Compile'])}</td>"
            f"<td data-col='JobLink'><a href='{escape(r['JobLink'])}' target='_blank'>jobright</a></td>"
            f"<td data-col='PDF'>" + (f"<a href='file://{escape(str(pdf_path))}' target='_blank'>PDF</a>" if pdf_path else "—") + "</td>"
            f"<td data-col='Applied'><button class='apply-btn' data-key='{escape(r['JobLink'])}'>Mark Applied</button></td>"
            f"</tr>"
        )
    cols = ["Template", "Company", "Title", "Score", "SkillsAdded", "BulletsChanged",
            "Skipped", "Compile", "JobLink", "PDF", "Applied"]
    header = "".join(
        f"<th data-col='{c}'>{c}<br><input class='filter' data-col='{c}' placeholder='filter…'></th>"
        for c in cols
    )
    html = f"""<!doctype html>
<html><head><meta charset='utf-8'><title>Batch — {DATE}</title>
<style>
body {{ font: 13px/1.4 -apple-system, sans-serif; margin: 16px; }}
h1 {{ font-size: 18px; margin: 0 0 8px; }}
.controls {{ margin-bottom: 8px; }}
.controls button {{ font: inherit; padding: 4px 10px; margin-right: 6px; cursor: pointer; }}
.controls .reset {{ margin-left: 16px; background: #f5f5f5; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 6px 8px; vertical-align: top; }}
th {{ background: #f4f6f8; text-align: left; position: sticky; top: 0; cursor: pointer; }}
th input.filter {{ width: 95%; font: 11px sans-serif; padding: 2px; box-sizing: border-box; margin-top: 2px; }}
tr:nth-child(even) td {{ background: #fafbfc; }}
td[data-col="Title"] {{ max-width: 300px; }}
td[data-col="SkillsAdded"], td[data-col="BulletsChanged"], td[data-col="Skipped"] {{ max-width: 240px; font-size: 12px; color: #333; }}
button.apply-btn {{ font: inherit; padding: 4px 10px; border: 1px solid #1f6feb; background: #fff; color: #1f6feb; border-radius: 4px; cursor: pointer; }}
button.apply-btn:hover {{ background: #e3f2fd; }}
button.apply-btn.applied {{ background: #2e7d32; border-color: #2e7d32; color: #fff; cursor: default; }}
tr.applied td {{ opacity: 0.55; text-decoration: line-through; }}
tr.applied td[data-col="Applied"] {{ opacity: 1; text-decoration: none; }}
</style></head><body>
<h1>Batch Resume Tailoring — {DATE}</h1>
<div class='meta'>{len(results)} resumes processed.</div>
<div class='controls'>
<button id='reset-applied' class='reset'>Reset all "Applied"</button>
<span id='applied-counter' style='margin-left:12px; color:#555;'></span>
</div>
<table id='t'><thead><tr>{header}</tr></thead><tbody>{''.join(rows)}</tbody></table>
<script>
const tbody = document.querySelector('#t tbody');
const allRows = Array.from(tbody.querySelectorAll('tr'));
const colFilters = {{}};
function apply() {{
    for (const tr of allRows) {{
        let show = true;
        for (const [col, val] of Object.entries(colFilters)) {{
            if (!val) continue;
            const cell = tr.querySelector(`td[data-col="${{col}}"]`);
            const text = (cell?.innerText || '').toLowerCase();
            if (!text.includes(val.toLowerCase())) {{ show = false; break; }}
        }}
        tr.style.display = show ? '' : 'none';
    }}
}}
document.querySelectorAll('input.filter').forEach(inp => {{
    inp.addEventListener('input', () => {{ colFilters[inp.dataset.col] = inp.value; apply(); }});
    inp.addEventListener('click', e => e.stopPropagation());
}});
document.querySelectorAll('th').forEach(th => {{
    let asc = true;
    th.addEventListener('click', e => {{
        if (e.target.tagName === 'INPUT') return;
        const idx = Array.from(th.parentNode.children).indexOf(th);
        const sorted = Array.from(tbody.querySelectorAll('tr')).sort((a,b) => {{
            const av = a.children[idx].innerText, bv = b.children[idx].innerText;
            const an = parseFloat(av), bn = parseFloat(bv);
            if (!isNaN(an) && !isNaN(bn)) return asc ? an-bn : bn-an;
            return asc ? av.localeCompare(bv) : bv.localeCompare(av);
        }});
        sorted.forEach(r => tbody.appendChild(r));
        asc = !asc;
    }});
}});
const STORAGE_KEY = 'applied-{DATE}';
const appliedSet = new Set(JSON.parse(localStorage.getItem(STORAGE_KEY) || '[]'));
function refreshAppliedUI() {{
    let count = 0;
    document.querySelectorAll('tr[data-key]').forEach(tr => {{
        const key = tr.dataset.key;
        const btn = tr.querySelector('.apply-btn');
        if (appliedSet.has(key)) {{
            tr.classList.add('applied');
            btn.classList.add('applied');
            btn.textContent = '✓ Applied';
            count++;
        }} else {{
            tr.classList.remove('applied');
            btn.classList.remove('applied');
            btn.textContent = 'Mark Applied';
        }}
    }});
    document.getElementById('applied-counter').textContent = `${{count}} applied / ${{allRows.length}} total`;
}}
document.querySelectorAll('.apply-btn').forEach(btn => {{
    btn.addEventListener('click', () => {{
        const key = btn.dataset.key;
        if (appliedSet.has(key)) appliedSet.delete(key);
        else appliedSet.add(key);
        localStorage.setItem(STORAGE_KEY, JSON.stringify([...appliedSet]));
        refreshAppliedUI();
    }});
}});
document.getElementById('reset-applied').addEventListener('click', () => {{
    if (confirm('Reset all "Applied" marks?')) {{
        appliedSet.clear();
        localStorage.removeItem(STORAGE_KEY);
        refreshAppliedUI();
    }}
}});
refreshAppliedUI();
</script>
</body></html>"""
    out.write_text(html, encoding="utf-8")


def main():
    jobs = json.loads(JSON_IN.read_text())
    print(f"Processing {len(jobs)} roles from {JSON_IN.name}...")
    results = []
    for i, r in enumerate(jobs, 1):
        if "error" in r:
            continue
        out = process_role(r)
        results.append(out)
        print(f"  [{i}/{len(jobs)}] {out['Company'][:30]:30} | {out['Template']:8} | {out['Compile']} | +{len(out['SkillsAdded'])} skills, {len(out['BulletsChanged'])} bullets")

    (OUT_DIR / "batch_results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
    write_html(results, OUT_DIR / "batch_summary.html")
    fails = [r for r in results if r["Compile"] != "OK"]
    print(f"\nDone. Failures: {len(fails)}")
    print(f"HTML: {OUT_DIR / 'batch_summary.html'}")


if __name__ == "__main__":
    main()
