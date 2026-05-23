#!/usr/bin/env python3
"""Generate one cover letter per role in a date folder's jobs.json.

Follows the five-paragraph structure documented in
memory/project_cover_letter_structure.md:
  1. Opening + role title
  2. Strongest match (role-specific evidence)
  3. Supporting match
  4. Stack overlap
  5. Why this company (mission / domain)

Hard rules enforced:
- NO em dashes (---  or unicode em-dash)
- NO numbers (percentages, $, GPA, year counts, user counts)
- Bold key tech terms
- 1 page

Usage:
    python3 jobs/batch_cover_letter.py <date_folder>
"""

import json, re, subprocess, sys, time
from pathlib import Path
import requests

ROOT = Path("/Users/ajayvenkatesh/Desktop/Resume Job Roles")
COOKIES = json.loads((ROOT / "jobs" / "cookies.json").read_text())
HEADERS = {'accept': 'text/html', 'user-agent': 'Mozilla/5.0 (Macintosh) AppleWebKit/537.36 Chrome/145.0.0.0 Safari/537.36'}
JD_RE = re.compile(r'"description":"((?:[^"\\]|\\.)*?)"')

DATE_FOLDER = sys.argv[1] if len(sys.argv) > 1 else "20260520"
OUT_DIR = ROOT / DATE_FOLDER
TODAY = "May 21, 2026"


def strip_numbers(text: str) -> str:
    """Remove or paraphrase numeric tenure mentions before any verbatim leaks through."""
    text = re.sub(r"\bthree years\b", "the past few years", text)
    text = re.sub(r"\ba few years\b", "", text)
    text = re.sub(r"\bseveral years of production software experience\b",
                  "production software experience", text)
    text = re.sub(r"\bover \d+ years\b", "", text)
    # Strip explicit percentages, $K, etc.
    text = re.sub(r"\b\d+(?:\.\d+)?%", "materially", text)
    text = re.sub(r"\$\\?\$?\d+[KMB]\+?", "meaningful", text)
    return text


def strip_em_dashes(text: str) -> str:
    return text.replace("---", ",").replace("—", ",")


def family_strongest_match(family: str) -> str:
    """Paragraph 2: strongest-match evidence based on family."""
    if family == "SEJ":
        return (
            "At Amazon I engineered backend services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR) "
            "with low-level design patterns and rigorous unit and integration testing via \\textbf{Mockito}, "
            "shipped under code-review discipline. I provisioned the supporting infrastructure with "
            "\\textbf{AWS CDK} (Lambda, API Gateway, DynamoDB, IAM, CloudWatch) and operated "
            "multi-stage, multi-region CI/CD with rollback controls. The same posture, careful Java services "
            "deployed on cloud-native AWS infrastructure, maps cleanly onto what the role describes."
        )
    if family in ("SEAI", "SELLM"):
        return (
            "At Amazon I deployed a \\textbf{Retrieval-Augmented Generation (RAG)} pipeline with an "
            "\\textbf{agentic workflow} that autonomously retrieves operational logs to reason over "
            "incident details, generating context-aware summaries and remediation steps. I also "
            "implemented a \\textbf{Model Context Protocol (MCP)} server for tool-augmented retrieval "
            "that materially reduced query time and compute costs. Deploying LLMs and AI-assisted "
            "systems in production isn't a side project, it has been the shape of my last year of work."
        )
    if family == "AI":
        return (
            "At Amazon I deployed a \\textbf{Retrieval-Augmented Generation (RAG)} pipeline with an "
            "\\textbf{agentic workflow} that autonomously reasons over operational logs to generate "
            "context-aware summaries. At Campus Mesh I built \\textbf{CampusIQ}, an LLM-powered AI "
            "assistant with \\textbf{prompt engineering} and \\textbf{RAG retrieval} over structured "
            "data, plus \\textbf{embedding-based semantic search}. ML evaluation and inference workflows "
            "are where I find the work most rewarding."
        )
    if family == "FS":
        return (
            "At NYU's Novel AI Technologies I shipped a customer-facing analytics platform end-to-end "
            "using \\textbf{React, Node.js, REST APIs}, deployed via \\textbf{Docker} on \\textbf{EC2}, "
            "with Stripe billing, role-based access, and row-level security delivered to paying clients. "
            "At Campus Mesh I built scalable \\textbf{Node.js microservices} powering real-time academic "
            "workflows backed by \\textbf{MongoDB}. Building production full-stack systems with real users "
            "is where I spend my time."
        )
    if family == "FE":
        return (
            "At Amazon I built a \\textbf{React 18} frontend with optimized API integration, advanced "
            "filtering, and client-side caching to materially reduce page load times. At NYU I shipped a "
            "production React UI for an insurance analytics platform with role-based access and a clean "
            "design system delivered to paying clients. Frontend that actually has to handle real users "
            "and real data is the work I want to keep doing."
        )
    if family == "DE":
        return (
            "My Big Data graduate project built a \\textbf{PySpark / HDFS} pipeline over millions of "
            "flight records, training Random Forest and Gradient Boosted Tree models with rigorous EDA. "
            "At NYU I engineered \\textbf{ETL pipelines} transforming \\textbf{NoSQL} into "
            "\\textbf{PostgreSQL} with concurrency control, powering \\textbf{AWS QuickSight} dashboards. "
            "At PwC I parallelized batch ingestion that materially cut execution time on operational feeds."
        )
    if family == "CE":
        return (
            "At PwC I owned a distributed backend on \\textbf{Microsoft Azure} integrating with "
            "\\textbf{Microsoft CRM}, with event-driven processing and fault-tolerant retries over "
            "\\textbf{SQL Server}, leveraging a \\textbf{C\\#/.NET} stack. I owned features end-to-end "
            "from requirements through deployment, alongside architects, product managers, and business "
            "stakeholders."
        )
    # SE default
    return (
        "At Amazon I provisioned \\textbf{Infrastructure-as-Code} on \\textbf{AWS CDK} "
        "(Lambda, API Gateway, DynamoDB, IAM, CloudWatch) with multi-stage CI/CD and rollback controls. "
        "I shipped backend services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR) and a "
        "\\textbf{React 18} frontend with optimized API integration. Production work owned end-to-end "
        "is the shape of work I want to keep doing."
    )


def supporting_paragraph(family: str) -> str:
    """Paragraph 3: supporting evidence from a different angle."""
    if family in ("AI", "SEAI", "SELLM"):
        return (
            "On the systems side, I provisioned \\textbf{Infrastructure-as-Code} on \\textbf{AWS CDK} "
            "and built an event-driven processing system on \\textbf{AWS ECS Fargate, SQS, SNS} that "
            "decoupled distributed message processing under variable load. I'm also fluent in "
            "\\textbf{Docker}, \\textbf{Kubernetes}, and at home debugging production incidents through "
            "logs, metrics, and traces."
        )
    if family == "CE":
        return (
            "On the cloud-native and AI side, at Amazon I provisioned \\textbf{Infrastructure-as-Code} "
            "with \\textbf{AWS CDK} and shipped a \\textbf{React 18} frontend with optimized API "
            "integration. I also built a \\textbf{Retrieval-Augmented Generation (RAG)} pipeline with "
            "an agentic workflow over operational data."
        )
    if family == "DE":
        return (
            "On the production side, at Amazon I shipped backend services in \\textbf{Java} with unit "
            "and integration testing via \\textbf{Mockito}, and provisioned \\textbf{AWS CDK} "
            "infrastructure for serverless data pipelines."
        )
    if family in ("FS", "FE"):
        return (
            "On the backend, I shipped services in \\textbf{Java} (Coral, Smithy, Dagger, CBOR) with "
            "low-level design patterns and \\textbf{Mockito} testing at Amazon, and worked on "
            "\\textbf{LLM-based retrieval pipelines (RAG)} for CampusIQ at Campus Mesh, leveraging "
            "embedding-based semantic search."
        )
    # SEJ / SE default
    return (
        "At NYU's Novel AI Technologies I shipped a customer-facing analytics platform end-to-end "
        "with \\textbf{React, Node.js, REST APIs}, deployed via \\textbf{Docker} on \\textbf{EC2}, "
        "with Stripe billing, role-based access, and row-level security for paying clients."
    )


def stack_paragraph(matched: list[str]) -> str:
    """Paragraph 4: stack overlap based on matched skills."""
    matched_lower = {m.lower() for m in matched}
    parts = []
    if "python" in matched_lower:
        parts.append("\\textbf{Python}")
    if "java" in matched_lower:
        parts.append("\\textbf{Java}")
    if "typescript" in matched_lower or "javascript" in matched_lower:
        parts.append("\\textbf{TypeScript and JavaScript}")
    if "react" in matched_lower:
        parts.append("\\textbf{React}")
    langs = ", ".join(parts) if parts else "\\textbf{Python, Java, TypeScript}"

    db_set = matched_lower & {"postgresql", "mysql", "mongodb", "dynamodb", "redis", "snowflake"}
    dbs = ", ".join(d.capitalize() for d in db_set) if db_set else "PostgreSQL, MySQL, MongoDB, DynamoDB"

    return (
        f"Stack-wise: {langs} for backend and product surfaces, cloud microservices on \\textbf{{AWS}} "
        f"with \\textbf{{Docker}} and CI/CD, and {dbs} for the data layer. I'm comfortable spanning the "
        f"stack and reasoning about reliability and safety in customer-facing systems."
    )


def closing_paragraph(company: str, jd: str) -> str:
    """Paragraph 5: why-this-company tie-in based on JD body."""
    jd_l = jd.lower()
    if any(k in jd_l for k in ("healthcare", "medical", "patient", "clinical", "life science", "biotech", "bioinformatics", "pharma")):
        return (f"What pulls me toward {company} is the seriousness of healthcare and life-science software, "
                f"where engineering judgment compounds because the work has real consequences for patients and clinicians.")
    if any(k in jd_l for k in ("autonomous", "self-driving", "robotics", "vehicle", "rocket", "satellite", "starlink", "aerospace")):
        return (f"What pulls me toward {company} is the stakes. Engineering for systems where mistakes happen "
                f"in real units, on real hardware, with real consequences is exactly the kind of work I want to grow into.")
    if any(k in jd_l for k in ("climate", "renewable", "sustainability", "energy", "carbon")):
        return (f"What pulls me toward {company} is the mission. Building software that compounds into "
                f"real-world climate outcomes is the kind of feedback loop I want to be inside of.")
    if any(k in jd_l for k in ("fintech", "lending", "credit", "borrower", "payment", "bank", "insurance", "trading", "wealth", "tax")):
        return (f"What pulls me toward {company} is the combination of regulated workflows, sensitive data, "
                f"and customer outcomes that matter in real units, not just internal vanity metrics.")
    if any(k in jd_l for k in ("education", "learning", "student", "teach", "curriculum", "edtech", "university")):
        return (f"What pulls me toward {company} is the mission. Education software runs on real consequences "
                f"for students, parents, and teachers who trust the product to behave the way it claims.")
    if any(k in jd_l for k in ("market", "alpha", "quant", "trading desk")):
        return (f"What pulls me toward {company} is the discipline. Building software where the work is "
                f"measured in real units, on real systems, alongside people who think probabilistically about risk.")
    if any(k in jd_l for k in ("government", "defense", "national security", "public sector", "federal", "secret clearance")):
        return (f"What pulls me toward {company} is the operational seriousness of the work, where careful, "
                f"documented engineering matters more than novelty.")
    if any(k in jd_l for k in ("iot", "embedded", "connected device", "telematics", "telecom")):
        return (f"What pulls me toward {company} is the layered engineering, where cloud-native software has "
                f"to behave correctly against real-world devices, networks, and operational constraints.")
    if any(k in jd_l for k in ("retail", "commerce", "shopping", "merchant", "consumer")):
        return (f"What pulls me toward {company} is the scale of the consumer-facing problem and the chance "
                f"to ship product software where the feedback loop closes through actual customer behavior.")
    return (f"What pulls me toward {company} is the chance to build production software that matters, "
            f"alongside engineers who care about getting the details right.")


def generate(role: dict) -> str:
    company = role["Company"]
    title = role["Title"]
    family = role.get("RoutingDetails", {}).get("family", "SE")
    matched = role.get("MatchedSkills", [])
    is_ng = role.get("RoutingDetails", {}).get("is_new_grad", False)

    # Fetch JD body
    jd = ""
    try:
        r = requests.get(role["JobLink"], headers=HEADERS, cookies=COOKIES, timeout=20)
        m = JD_RE.search(r.text)
        jd = m.group(1) if m else ""
    except Exception:
        pass

    # Geographic detection
    location_line = "Brooklyn, NY"
    location_intro = ""
    if any(k in jd.lower() for k in ("brooklyn", "williamsburg")):
        location_intro = "I'm based here in Brooklyn, "

    p1 = (
        f"My name is Ajay Venkatesh. {location_intro}I'm finishing my M.S. in Computer Engineering at NYU, "
        f"with production software experience at PwC in Bengaluru, a summer SDE internship at Amazon, "
        f"and ongoing on-campus work at NYU's Novel AI Technologies. I'm writing about the {title} role."
    )
    p2 = family_strongest_match(family)
    p3 = supporting_paragraph(family)
    p4 = stack_paragraph(matched)
    p5 = closing_paragraph(company, jd)

    body = f"""\\documentclass[letterpaper,11pt]{{article}}

\\usepackage[top=0.8in, bottom=0.8in, left=0.9in, right=0.9in]{{geometry}}
\\usepackage[hidelinks]{{hyperref}}
\\usepackage{{lmodern}}
\\usepackage{{parskip}}
\\usepackage{{microtype}}

\\setlength{{\\parskip}}{{6pt}}
\\setlength{{\\parindent}}{{0pt}}

\\begin{{document}}

\\begin{{flushleft}}
\\textbf{{\\large Ajay Venkatesh}} \\\\
{location_line} \\\\
+1 516 585 9013 \\\\
\\href{{mailto:av3855@nyu.edu}}{{av3855@nyu.edu}}
\\end{{flushleft}}

\\vspace{{10pt}}

{TODAY}

\\vspace{{6pt}}

Hiring Manager \\\\
{company}

\\vspace{{10pt}}

Dear Hiring Manager,

{p1}

{p2}

{p3}

{p4}

{p5}

I'd welcome the chance to discuss further. Thanks for considering my application.

\\vspace{{12pt}}

Sincerely, \\\\
Ajay Venkatesh

\\end{{document}}
"""
    # Apply hard-rule scrubbing
    body = strip_em_dashes(body)
    body = strip_numbers(body)
    return body


def slug(s): return re.sub(r"[^\w\-]+", "_", s).strip("_")[:60]


def main():
    if not (OUT_DIR / "jobs.json").exists():
        print(f"Missing {OUT_DIR}/jobs.json", file=sys.stderr); sys.exit(1)
    jobs = json.loads((OUT_DIR / "jobs.json").read_text())
    print(f"Regenerating cover letters for {len(jobs)} roles in {DATE_FOLDER}...", file=sys.stderr)

    fails, page_overflow = [], []
    for i, j in enumerate(jobs, 1):
        if "error" in j:
            continue
        folder = OUT_DIR / slug(j["Company"])
        folder.mkdir(exist_ok=True)
        tex = folder / "Ajay_venkatesh_Cover_letter.tex"
        try:
            tex.write_text(generate(j), encoding="utf-8")
            r = subprocess.run(["pdflatex", "-interaction=nonstopmode", "Ajay_venkatesh_Cover_letter.tex"],
                               cwd=folder, capture_output=True, timeout=60)
            for ext in (".aux", ".log", ".out"):
                (folder / f"Ajay_venkatesh_Cover_letter{ext}").unlink(missing_ok=True)
            pdf = folder / "Ajay_venkatesh_Cover_letter.pdf"
            ok = pdf.exists()
            # Check page count
            out_text = r.stdout.decode(errors='ignore')
            pages = re.search(r'\((\d+) pages?,', out_text)
            page_n = int(pages.group(1)) if pages else 0
            if page_n > 1:
                page_overflow.append(j['Company'])
            if not ok:
                fails.append(j["Company"])
            print(f"  [{i}/{len(jobs)}] {j['Company'][:30]:30} | {'OK' if ok else 'FAIL':5} | {page_n} page", file=sys.stderr)
            time.sleep(0.2)
        except Exception as e:
            fails.append(f"{j['Company']}: {e}")

    print(f"\nFailures: {len(fails)}, 2-page overflows: {len(page_overflow)}", file=sys.stderr)
    if page_overflow:
        print("  Overflowed: " + ", ".join(page_overflow), file=sys.stderr)


if __name__ == "__main__":
    main()
