# Resume + Cover Letter Workflow Guide

This repo holds Ajay Venkatesh's job-application pipeline: a set of LaTeX base resume templates that get tailored per company, plus hand-written cover letters following a strict five-paragraph structure. Everything is automated through Python scripts in `jobs/`.

Use this guide as your operating manual when generating resumes, cover letters, or running the batch pipeline.

For **one job at a time** (job link or JD + base template), follow **§0** below — the agent generates **both resume and cover letter** automatically. For batch runs from `jobs.json`, see §8.

---

## 0. Agent Workflow — Single Job (Resume + Cover Letter)

Use this section whenever the user provides a **job link or job description** and a **base template** for one role. Do not ask for confirmation — execute all steps and deliver both files.

### What the user provides

| Input | Required? | Notes |
|---|---|---|
| **Job link** (e.g. `https://jobright.ai/jobs/info/<id>`) **OR pasted job description** | Yes (one of the two) | If a link is given, fetch the JD (company, title, location, responsibilities, qualifications, matched/missing skills). If fetch fails (no cookies / 401), ask the user to paste the JD text. |
| **Base template code or path** | Yes | e.g. `SE Python E`, `SELLM_E`, `SE/P/E/` — see §2 for codes and aliases |
| **Extra instructions** (projects, certifications, skills to swap/add/remove) | Optional | Overrides auto-tailoring; apply exactly as stated |

**Default deliverables:** tailored resume **and** cover letter in the company folder. Only skip the cover letter if the user explicitly says "resume only."

If the user does not specify a template, route using §11 decision tree + `keyword_router.py` logic. If they specify one, use it.

### Fetching a job from a link

When the user gives a Jobright URL:

1. Try fetching the job page or API (see §8 fetch workflow; `jobs/cookies.json` if available).
2. Extract: `companyName`, `jobTitle`, `jobLocation`, full description, `skillMatchingScores` (matched = score > 0.5, missing = score ≤ 0.5).
3. If the link cannot be fetched, use any JD text embedded in the chat or web context, then proceed.

### Agent steps (execute in order)

**Step 1 — Resolve today's date folder**

- Format: `YYYYMMDD` (e.g. `20260606` for June 6, 2026).
- Path: `<repo_root>/<YYYYMMDD>/`
- If the folder does not exist, create it.

**Step 2 — Create company folder**

- Slug rule: `re.sub(r"[^\w\-]+", "_", company).strip("_")[:60]`
  - Example: `H&R Block` → `H_R_Block`
- Path: `<YYYYMMDD>/<Company_Slug>/`
- If the same company already has a folder for a different role today, use `<Company>_<Title_Tag>` (e.g. `PayPal_ML_Engineer`).

**Step 3 — Copy base template**

- Resolve template code via §2 / `TEMPLATE_ALIAS` in `jobs/batch_apply.py` (e.g. `SE Python E` → `SEP_E` → `SE/P/E/`).
- If the template file is missing locally, restore from git: `git show HEAD:"SE/P/E/Ajay_Venkatesh_Resume.tex"`.
- Copy the source `.tex` into the company folder as `Ajay_Venkatesh_Resume.tex`.
- Do **not** mix Style A and Style B macros (see §3).

**Step 4 — Tailor the resume from the JD**

Read the JD and identify **missing keywords** (skills the JD asks for that are not already in the resume). For each keyword, classify per §4:

| Classification | Action |
|---|---|
| Concrete tool/framework (Kafka, Spring Boot, Redis, AWS Bedrock, …) | Inject into the matching Skills line (Cloud → Cloud, language → Programming, else Tools) |
| Programming language the JD **requires** (Go, Kotlin, Rust, .NET, Scala) | Inject into Programming Languages |
| Language listed as alternative ("Python or Java" when Java exists) | **Skip** |
| Concept phrase ("Distributed Systems Debugging", "Data Modeling") | **Do not** put in Skills — paraphrase into a relevant bullet (§4, `BULLET_EDITS`) |
| Soft skill ("Leadership", "Communication", "Curiosity") | **Skip** |
| Generic phrase ("Scalable system", "System design", "High-level design") | **Skip from Skills**; may appear naturally in bullets |
| Inauthentic tool (ROS, dbt, HubSpot, Webpack, DevSecOps, …) | **Skip** — see `SKIP_INAUTHENTIC` in `batch_apply.py` |

**Authenticity is non-negotiable** — see §4 company stack table. Do not inject every missing skill; pick the ones that are concrete, relevant, and authentic. Prefer quality over quantity.

Apply user **extra instructions** (project swaps, cert changes, bullet rewrites) on top of the above.

**LaTeX rules while editing:**

- Escape special chars in injected skills: `#`, `$`, `%`, `&`, `_` → backslash-prefix (`C#` → `C\#`).
- Keep resume to **one page** (§4 page-overflow trim order if needed).

**Step 5 — Compile resume**

From inside the company folder:

```bash
pdflatex -interaction=nonstopmode Ajay_Venkatesh_Resume.tex
```

Then remove build artifacts: `*.aux`, `*.log`, `*.out`.

Verify output is **1 page**. On Windows, open the PDF in a viewer (not the code editor); on macOS: `mdls -name kMDItemNumberOfPages -raw <file>.pdf`.

**Step 6 — Write and compile cover letter (always, unless user says "resume only")**

Create `Ajay_venkatesh_Cover_letter.tex` in the same company folder using the skeleton in §6.

- Strict **five-paragraph** structure (§6).
- **No em dashes**, **no numbers**, **no 3+ verbatim JD words**.
- Bold key tech with `\textbf{}`.
- Compile with `pdflatex -interaction=nonstopmode Ajay_venkatesh_Cover_letter.tex`, clean artifacts, verify 1 page.

**Step 7 — Report back**

Tell the user:
- Folder path (`YYYYMMDD/<Company>/`)
- Template used
- Matched vs missing skills (brief summary from JD)
- Skills injected vs woven into bullets vs skipped (brief)
- Any manual edits applied from their extra instructions
- Confirm both PDFs were generated (1 page each)

### Copy-paste prompt (for the user)

Use this prompt in a new chat:

```
Generate a tailored resume and cover letter using AGENT_GUIDE.md (§0 workflow).

Job link OR job description:
<paste Jobright URL or full JD — company, title, location, matched/missing skills if available>

Base template: <e.g. SE Python E, SELLM_E, SE/P/E/>

Extra instructions (optional):
<any project swaps, cert changes, skills to add/remove, bullet rewrites — or leave blank>

Follow §0 automatically: fetch JD if link given, create today's YYYYMMDD folder if missing, create company subfolder, copy base template, tailor resume per §4 authenticity rules, compile resume, write and compile cover letter per §6, verify both are 1 page.
```

### Example folder after completion

```
20260606/
└── Clearwater_Analytics/
    ├── Ajay_Venkatesh_Resume.tex
    ├── Ajay_Venkatesh_Resume.pdf
    ├── Ajay_venkatesh_Cover_letter.tex
    └── Ajay_venkatesh_Cover_letter.pdf
```

---

## 1. Repository Layout

```
Resume Job Roles/
├── AGENT_GUIDE.md                  # this file
├── certificates.json               # all certificates with Google Drive links
├── base_templates.json             # template registry (code -> path -> keywords)
├── base_template_projects.json     # canonical project bullets
├── jobs/
│   ├── batch_apply.py              # main pipeline: JSON -> tailored resumes -> HTML report
│   ├── keyword_router.py           # picks the right base template from JD + title + skills
│   ├── batch_cover_letter.py       # cover letter batch generator (use sparingly; prefer hand-crafted)
│   ├── audit_languages.py          # checks language injection decisions
│   ├── cookies.json                # Jobright session cookies for scraping JDs
│   └── fetch_jobs.py               # scrapes Jobright URLs
├── SE/  P/E, P/NG, P/L            # Software Engineer (Python track) — entry / new grad / linkedin
│   ├── J/E, J/NG, J/L              # Software Engineer (Java track)
├── SE_AI/E                         # Software Engineer + AI (broad ML/AI hybrid SE)
├── SE_LLM/E                        # Software Engineer focused on LLMs / RAG / agentic
├── AI/E, AI/NG, AI/L               # AI / ML Engineer
├── DE/E, DE/L                      # Data Engineer
├── FE/E, FE/L                      # Frontend Engineer
├── FS/E, FS/L                      # Full Stack Engineer
├── CE/E                            # Cloud Engineer (Microsoft / Azure / .NET)
├── PA/D365/E, PA/D365/L            # Power Apps / Dynamics 365 Developer
├── 20260521/, 20260521_2/, ...     # date-folder batches with tailored resumes
└── Certificates/                   # PDF certificates (also mirrored on Google Drive)
```

Each base template folder contains:
- `Ajay_Venkatesh_Resume.tex` — the source
- `Ajay_Venkatesh_Resume.pdf` — the compiled output
- `keywords.txt` — keywords that trigger routing to this template

---

## 2. Base Template Codes

Every job in `jobs.json` has a `BaseTemplate` field that names which template to copy. The codes are normalized (see `TEMPLATE_ALIAS` in `batch_apply.py`):

| Code | Path | When to use |
|---|---|---|
| `SEP_E` | `SE/P/E/` | Generic Software Engineer (Python-leaning) |
| `SEP_NG` | `SE/P/NG/` | Software Engineer new-grad / Engineer I |
| `SEJ_E` | `SE/J/E/` | Java-track SDE roles (Spring Boot, JVM-heavy) |
| `SEJ_NG` | `SE/J/NG/` | Java-track new-grad / Engineer I |
| `SEAI_E` | `SE_AI/E/` | "Software Engineer, AI" hybrid titles — generic ML |
| `SELLM_E` | `SE_LLM/E/` | SE/FS title that mentions LLM, RAG, agentic, MCP, embeddings, vector DB, LangChain in JD |
| `AI_E`, `AI_NG`, `AI_L` | `AI/E,NG,L/` | AI / ML / Applied Scientist / Research Scientist titles |
| `DE_E` | `DE/E/` | Data Engineer / Analytics Engineer / ETL roles |
| `FE_E` | `FE/E/` | Frontend Engineer / UI Engineer |
| `FS_E` | `FS/E/` | Full Stack Engineer |
| `CE_E` | `CE/E/` | Cloud Engineer / .NET / Microsoft Azure / C# heavy |
| `PA_D365E` | `PA/D365/E/` | Power Apps / Dynamics 365 Developer / Power Platform Consultant |

**Hard rules for routing:**
- `_L` suffix = **LinkedIn variant**, NOT seniority. Never auto-route senior/lead/principal to `_L`.
- Pure AI/ML titles (AI Engineer, ML Engineer, Applied Scientist, Research Scientist) → `AI_E`.
- Generic Software Engineer or Full Stack titles **with LLM/RAG/agentic mentioned in JD** → `SELLM_E` (not `SEP_E` / `FS_E`).
- Engineer II / Senior / Lead are **NOT new grad** even if the regex thinks so — verify by JD body.

The router in `keyword_router.py` reads title + JD body + matched/missing skills together. Don't trust it blindly; spot-check borderline cases.

---

## 3. LaTeX Toolchain

- **Compiler:** `pdflatex` from TeX Live 2026 BasicTeX (path: `/Library/TeX/texbin/pdflatex`).
- **Compile command:** `pdflatex -interaction=nonstopmode Ajay_Venkatesh_Resume.tex` from inside the folder.
- **Always clean up:** `rm -f *.aux *.log *.out` after compile.
- **Required packages:** `fontawesome5`, `xcolor`, `hyperref`, `lmodern`, `enumitem`, `tabularx`, `geometry`, `titlesec`. All ship with TeX Live; no manual install needed.

### Two layout styles

The templates split into two distinct LaTeX styles. Don't mix them within one resume.

**Style A** (used by SEP_E, SEJ_E, SE_AI_E, SE_LLM_E, AI_E, AI_NG, AI_L, FS_E, CE_E):
- `\documentclass[a4paper,10pt]{article}`
- `xcolor` with `darkblue` hyperlinks
- Macros: `\resumeSubheading`, `\resumeProject`, `\resumeSubItem`, `\resumeHeadingSkillStart`
- Bullet form: `\item \footnotesize{...}`
- Subheading args: `{Company}{Location}{Title}{Date}`

**Style B** (used by SEP_NG, SEJ_NG, DE_E, FE_E, PA_D365E):
- `\documentclass[letterpaper,10pt]{article}`
- `fancyhdr`, `tabular*` for headers
- Macros: `\resumeSubheading`, `\resumeItem`
- Bullet form: `\resumeItem{...}`
- Subheading args: `{Company}{Date}{Title}{Location}` (different order!)

### Hard constraints
- **One page maximum.** Always verify with `mdls -name kMDItemNumberOfPages -raw <file>.pdf` (macOS) after compile.
- **Escape LaTeX special chars** in injected skills: `#`, `$`, `%`, `&`, `_` → backslash-prefix. Use `latex_escape()` in `batch_apply.py`. Forgetting this = silently dropped C#, Q&A, etc.
- **No em dashes** in cover letters (see §6). Resumes are unaffected but stay consistent.

---

## 4. Resume Tailoring Rules

### Skills section structure

Every resume has these skill lines (or close variants):
- **Programming Languages:** C++, Java, Python, TypeScript, JavaScript (ES6), SQL, ...
- **Web & Backend:** React, Node.js, Express.js, REST API, GraphQL, Microservices, ...
- **Databases:** MySQL, PostgreSQL, DynamoDB, MongoDB, ...
- **Cloud & DevOps:** AWS (CDK, EC2, S3, ...), Azure (Function Apps, ...), Docker, Kubernetes, CI/CD, Kafka, ...
- **AI/ML:** PyTorch, LLM Fine-tuning, RAG (LangChain, FAISS), NLP, Deep Learning, Hugging Face, ...
- **Tools & Platforms:** Git, Linux, Visual Studio, Cursor, GitHub Copilot, Jupyter, Postman, ...

### Skill injection rules (when adding from JD missing-skills list)

| Skill type | Action |
|---|---|
| Concrete named tool/framework (Kafka, Spring Boot, AWS Bedrock, Redis, etc.) | Inject into the matching line — Cloud → Cloud, Programming → Programming, else Tools. |
| Programming language (Go, Kotlin, Rust, .NET, Scala) — JD requires or prefers | Inject into Programming Languages. |
| Programming language listed as alternative ("Python or Java" when Java is already there) | **Skip** — it's redundant. |
| Concept phrase ("Distributed Systems Debugging", "Data Modeling", "Infrastructure as Code") | **Do not put in Skills.** Weave into a bullet point where it fits the narrative. |
| Soft skill ("Empathy", "Leadership", "Communication", "Curiosity") | **Skip entirely.** |
| Generic engineering phrase ("Scalable system", "Optimised", "Distributed", "High-level design", "System design") | **Skip from Skills.** May appear naturally in bullets. |
| Inauthentic tool (ROS, embedded systems, mainframe, DevSecOps, dbt, HubSpot, Webpack) | **Skip** — Ajay hasn't shipped these. |

The full skip-lists are in `batch_apply.py` as `SKIP_INAUTHENTIC` and `SKIP_CONCEPT`.

### Bullet weaving rules (paraphrase!)

When a concept phrase belongs in a bullet, **paraphrase it**. Never use 3+ verbatim words from the JD. The Skills line keeps the exact keyword for ATS; the bullet describes the work in different language.

Example:
- JD says: "Distributed Systems Debugging"
- Bullet edit: change "Led code reviews and mentored engineers" → "Led code reviews, mentored engineers, and **diagnosed production incidents across multi-service flows via logs, metrics, and traces**"

Pre-canned bullet edits live in `BULLET_EDITS` in `batch_apply.py`. Add more there if you find a recurring concept phrase.

### Authenticity rules — non-negotiable

These come from real experience and must not be claimed otherwise:

| Company | Authentic stack |
|---|---|
| **PwC (Aug 2021 – Aug 2024)** | Microsoft Azure, SQL Server, .NET, Dynamics 365 CRM, Power Platform (Power Apps, Power Automate, Power BI), Java (some), TypeScript, Azure DevOps, Visual Studio. **Do not claim** PySpark/Apache Spark at PwC — that's NYU + Flight Delay project. |
| **Amazon SDE Intern (May 2025 – Aug 2025)** | Java (Coral, Smithy, Dagger DI, CBOR, Mockito), React 18, AWS (CDK, API Gateway, Lambda, DynamoDB, S3, IAM, ECS Fargate, SQS, SNS, Athena), OAuth, Midway SSO, HELIS, RAG with agentic workflow, Model Context Protocol (MCP) server. |
| **NYU Novel AI Technologies (Aug 2024 – Present)** | React, Node.js, TypeScript, REST APIs, Docker, EC2, PostgreSQL, AWS QuickSight, Stripe, Cognito, RBAC. |
| **CampusMesh (Jan 2026 – Present)** | Node.js microservices, MySQL (Sequelize), DynamoDB, Serverless Framework on AWS (Lambda, API Gateway, S3, CloudFront), KMS, SSM Parameter Store, least-privilege IAM, AWS Chime SDK, JWT custom authorizer, RAG with embedding-based semantic search for CampusIQ AI assistant. |

**Authentic NYU coursework** (do not invent more): System Design, Machine Learning, Deep Learning, Big Data, Computer Architecture, Data Structures, Advanced Java (Java-track only). **Not Advanced Python.**

### Standard CampusMesh bullets (current canonical version)

These three bullets appear identically across all base templates:
1. *Developed scalable Node.js microservices powering real-time academic workflows across study groups, messaging, calls, notifications, and profile management, backed by MySQL (Sequelize) and DynamoDB.*
2. *Deployed serverless architecture on AWS using Serverless Framework with Lambda, API Gateway, S3, and CloudFront across 4 environments (local, dev, staging, production); enforced security with KMS-managed keys, SSM Parameter Store, and least-privilege IAM.*
3. *Worked on LLM-based retrieval pipelines (RAG) for CampusIQ (AI Assistant), leveraging embedding-based semantic search and structured data indexing to improve contextual accuracy by 30%.*

If a template needs different framing (e.g., CE_E has a Chime SDK + AES authorizer variant), check the existing template before standardizing.

### Page-overflow remediation

If the resume goes to 2 pages after skill injection, trim in this order:
1. Drop the **PwC mentoring/code-review bullet** (least relevant for most modern SE/AI roles).
2. Drop concept-phrase skills that should have been skipped (Reinforcement Learning, FireBase, generic methodologies).
3. Drop the **NYU underwriting/broker portal bullet** (least LLM-relevant).
4. Drop the **ResNet project** (third project on SE_LLM_E, least LLM-specific).
5. Trim long parenthetical lists in Cloud / AI/ML / Tools lines.

Recompile and verify 1 page after each trim.

---

## 5. JSON Schema for `jobs.json`

Each batch folder has a `jobs.json` with one entry per role:

```json
{
  "Company": "Paramount",
  "Title": "Software Engineer",
  "Location": "New York, NY",
  "PublishTime": "Posted 3 days ago",
  "MinYOE": "2",
  "MatchScore": 0.81,
  "MatchedSkills": ["Java", "Python", "API development", ...],
  "MissingSkills": ["Kotlin", "Backend services development", "AI-assisted development tools", "Embeddings", "Cloud platforms - GCP"],
  "JobLink": "https://jobright.ai/jobs/info/<id>",
  "JobId": "...",
  "BaseTemplate": "SELLM_E",
  "RoutingDetails": {
    "family": "SE",
    "is_new_grad": false,
    "score": 8,
    "matched_keyword_hits": [...],
    "title_keyword_hits": [...],
    "original_code": "SEP_E",
    "override_reason": "JD mentions RAG, LLM, embeddings"
  },
  "JDText": "<full JD body — up to 8000 chars>",
  "WorkExpComment": "",
  "ProjectComment": "use flight delay project"
}
```

### Comment fields (manual override)
- `WorkExpComment` — free-text instruction for the work experience section (e.g., "rephrase Amazon bullets to lead with system design").
- `ProjectComment` — free-text instruction for the projects section (e.g., "swap Hospital Management for RoBERTa LoRA", "use flight delay project").
- Leave empty → script auto-handles via standard skill injection.
- Non-empty → role is flagged `NeedsManualEdit: true` in `batch_results.json` and printed in the queue at end of run. You then read the comment and edit the `.tex` by hand.

---

## 6. Cover Letter Rules

All cover letters follow a **strict five-paragraph layout**. No exceptions.

### Five paragraphs

1. **Opening (intro + role mention)**
   - Name + NYU M.S. in Computer Engineering
   - Experience summary, **without numbers**: "with production software experience at PwC in Bengaluru, a summer SDE internship at Amazon, and ongoing on-campus work at NYU's Novel AI Technologies"
   - Specific role title from the JD
   - Short focus statement aligned with role family

2. **Strongest-match paragraph** — pull from the most relevant company/project for THIS role.
   - Java roles → Amazon Java work (Coral, Smithy, Mockito, Dagger)
   - AI/LLM roles → Amazon RAG + agentic + MCP work
   - Full-stack → NYU insurance platform (React, Node.js, Docker on EC2, Stripe, RBAC)
   - Frontend → Amazon React 18 with caching, NYU React platform
   - Data Engineer → PySpark/HDFS Flight Delay project, NYU ETL pipelines
   - Cloud/Microsoft → PwC Azure + Microsoft CRM + SQL Server
   - DevOps → Campus Mesh serverless deployment

3. **Secondary-match paragraph** — pull from a different company that reinforces the fit.

4. **Stack overlap OR honest-gap framing**
   - List concrete tech: Python / TypeScript / React / AWS / Docker / SQL etc.
   - If C++ / Kotlin / Rust / Scala / Ruby on Rails gap exists, frame honestly: "Kotlin is the one stack item I haven't shipped in production yet, but I've picked up new backend languages quickly before."

5. **"What pulls me toward [Company]"** — mission / domain tie-in.
   - Healthcare → "engineering judgment compounds because the work has real consequences for patients and clinicians"
   - AV / Robotics → "real units, on real roads, with people inside the vehicle"
   - Fintech / lending → "regulated workflows, sensitive data, customer outcomes in real units"
   - Education → "students whose progress depends on the system being correct"
   - Climate / energy → "software that compounds into real-world climate outcomes"
   - Trading / quant → "discipline of measuring work in real units"
   - Government / defense → "operational seriousness, careful documented engineering"
   - Brooklyn / NYC-based company → tie in "based here in Brooklyn"

### Close
- "I'd welcome the chance to discuss further. Thanks for considering my application."
- "Sincerely, Ajay Venkatesh"

### Hard rules — verify before compile

| Rule | Enforcement |
|---|---|
| **No em dashes** (`—` or `---`) | Use commas, periods, parentheses, or restructure. `grep -c '—\|---'` must return 0. |
| **No numbers anywhere** | No `40%`, `$50K`, `GPA 3.9`, `three years`, `a few years`, `10K users`, `6 clients`, `7M records`, `250K records`. Paraphrase all to qualitative language. |
| **No 3+ verbatim JD words** | Rephrase JD requirements so resume + letter don't mirror. |
| **Bold key tech terms** with `\textbf{}` for visual emphasis. |
| **1 page max** | `pdflatex` must report `(1 page, ...)`. |

### Paraphrasing tenure references

| Bad | Good |
|---|---|
| "three years at PwC" | "at PwC in Bengaluru" |
| "a few years at PwC" | "at PwC in Bengaluru" |
| "several years of production experience" | "with production software experience" |
| "spent three years on a distributed backend" | "owned the distributed backend on Azure" |
| "five years" | (drop entirely) |

### Anti-patterns — never produce

- Generic openers ("I'm excited about this opportunity")
- Listing skills without proof of work
- Copying JD phrases verbatim
- Mentioning lack of clearance, missing years, etc.
- Closing with "I'm a quick learner / passionate / team player"
- Em dashes anywhere
- Numbers anywhere

### Cover letter LaTeX template

Use this skeleton (letterpaper, 11pt, lmodern, parskip):

```latex
\documentclass[letterpaper,11pt]{article}
\usepackage[top=0.8in, bottom=0.8in, left=0.9in, right=0.9in]{geometry}
\usepackage[hidelinks]{hyperref}
\usepackage{lmodern}
\usepackage{parskip}
\usepackage{microtype}
\setlength{\parskip}{6pt}
\setlength{\parindent}{0pt}
\begin{document}
\begin{flushleft}
\textbf{\large Ajay Venkatesh} \\
Brooklyn, NY \\
+1 516 585 9013 \\
\href{mailto:av3855@nyu.edu}{av3855@nyu.edu}
\end{flushleft}
\vspace{10pt}
<Date>
\vspace{6pt}

Hiring Manager \\
<Company> \\
<Location>

\vspace{10pt}

Dear Hiring Manager,

<Paragraph 1: intro + role mention>

<Paragraph 2: strongest match>

<Paragraph 3: secondary match>

<Paragraph 4: stack overlap / honest gap>

<Paragraph 5: why this company>

I'd welcome the chance to discuss further. Thanks for considering my application.

\vspace{12pt}
Sincerely, \\
Ajay Venkatesh
\end{document}
```

Save as `Ajay_venkatesh_Cover_letter.tex` (note the lowercase `v`) inside the company folder.

---

## 7. Folder Structure Conventions

### Batch folders

Date-based folders capture each batch run:
```
YYYYMMDD/                  e.g., 20260521/
├── jobs.json              # role list with BaseTemplate per company
├── batch_results.json     # output of batch_apply.py
├── batch_summary.html     # filterable HTML table
└── <Company_Name>/        # one folder per role
    ├── Ajay_Venkatesh_Resume.tex
    ├── Ajay_Venkatesh_Resume.pdf
    └── Ajay_venkatesh_Cover_letter.tex   (optional, hand-written)
    └── Ajay_venkatesh_Cover_letter.pdf
```

Folder slug rule: company name → `re.sub(r"[^\w\-]+", "_", company).strip("_")[:60]`. Example: `H&R Block` → `H_R_Block`.

### Duplicate company handling

When two roles share a company name (e.g., two PayPal roles, two Goldman Sachs roles), the batch script collides them into one folder. Handle by:
1. Renaming first folder to `<Company>_<Title_Tag>` (e.g., `PayPal_ML_Engineer`).
2. Manually re-running `process_role()` for the second role with a tweaked Company name.
3. Updating `batch_results.json` PDF paths and regenerating HTML.

### Suffix variant: `_2`

If you re-process the same date with a different batch of jobs, append `_2`: `20260521_2/`. The `BaseTemplate` decisions in `_2` are independent.

---

## 8. Running the Pipeline

### Fetch jobs from Jobright URLs

A typical fetch script (one-off, lives in `/tmp/fetch_<date>.py`):
- Loads `jobs/cookies.json` (Jobright session)
- Iterates a list of `https://jobright.ai/jobs/info/<id>` URLs
- For each URL extracts: `companyName`, `jobTitle`, `jobLocation`, `publishTimeDesc`, `minYearsOfExperience`, `displayScore`, `skillMatchingScores`, `description`
- Splits `skillMatchingScores` into matched (`score > 0.5`) vs missing (`score <= 0.5`)
- Calls `pick_template()` from `keyword_router.py` with title + JD body + matched + missing
- Writes `<date_folder>/jobs.json`

**Critical regex fix:** the description field uses JSON escapes. Use `r'"description":"((?:[^"\\]|\\.)*?)"'` — the simpler `r'"description":"([^"\\]+)'` truncates JDs at the first escape.

### Apply the batch

```bash
cd "/Users/ajayvenkatesh/Desktop/Resume Job Roles"
python3 jobs/batch_apply.py <date_folder> jobs.json
```

This will:
1. Read `<date_folder>/jobs.json`
2. For each role: copy base template → inject skills → apply bullet edits → escape LaTeX → compile via `pdflatex`
3. Print one-line status per role + any `NEEDS MANUAL EDIT` queue
4. Write `<date_folder>/batch_results.json` and `<date_folder>/batch_summary.html`

### Verify pages

```bash
cd <date_folder> && for d in */; do
  pages=$(mdls -name kMDItemNumberOfPages -raw "$d/Ajay_Venkatesh_Resume.pdf" 2>/dev/null)
  [ "$pages" != "1" ] && echo "  ${d%/}: $pages pages"
done
```

Anything that prints needs page-overflow remediation (see §4 trim order).

---

## 9. Memory System (Claude Code specific)

When operating as a Claude Code agent, persistent rules live at:
```
~/.claude/projects/-Users-ajayvenkatesh-Desktop-Resume-Job-Roles/memory/
├── MEMORY.md                                  # index, always loaded
├── feedback_no_emdash_cover_letters.md
├── feedback_no_numbers_in_cover_letters.md
├── feedback_paraphrase_bullets.md
├── feedback_concrete_skills_only.md
├── feedback_pwc_authentic_stack.md
├── feedback_authentic_coursework.md
├── feedback_dont_skip_languages.md
├── feedback_L_means_linkedin.md
├── feedback_no_jd_overfit.md
├── feedback_no_confirmation.md
├── feedback_llm_rag_agentic_route_sellm.md
├── project_resume_workflow.md
├── project_batch_resume_workflow.md
└── project_cover_letter_structure.md
```

If you're a different agent (ChatGPT Codex, etc.) without this memory system, this `AGENT_GUIDE.md` is the consolidated equivalent — all the rules in those memory files are reflected above.

---

## 10. Certificates

All certificates are stored in `certificates.json` at repo root with Google Drive URLs. When a resume's certifications section needs hyperlinks, pull from there. The current canonical list (cloud-only for CE_E and AI-leaning roles): AWS Cloud Practitioner, Azure Data Fundamentals, Azure Data Scientist Associate. The Power Platform cert family is mostly used in PA_D365E and CE_E.

Format inside resume:
```latex
\href{<drive_url>}{\textbf{<Cert Name>} \scriptsize\faLink}
```

---

## 11. Quick-Reference Decision Tree

**Single job (user pastes JD + template):** follow **§0** end-to-end.

Generating a new resume for a job:

1. **What's the title?**
   - Has "AI", "ML", "Applied Scientist", "Research Scientist" → `AI_E` (or `AI_NG` if new-grad)
   - Has "Data Engineer", "Analytics Engineer" → `DE_E`
   - Has "Frontend", "UI Engineer" → `FE_E`
   - Has "Full Stack" → `FS_E`
   - Has "Java" or "Spring Boot" → `SEJ_E` (or `SEJ_NG`)
   - Has ".NET", "C#" → `CE_E`
   - Has "Power Apps", "Dynamics 365" → `PA_D365E`
   - Has "Engineer I", "Junior", "New Grad", "Entry-Level" → `_NG` variant
2. **Read the JD body.**
   - If JD mentions LLM / RAG / agentic / MCP / embeddings → upgrade to `SELLM_E` (unless title is already AI/ML).
   - If JD heavy on Java / Spring even though title is generic SE → upgrade to `SEJ_E`.
   - If JD heavy on Azure / C# / .NET → upgrade to `CE_E`.
3. **Classify each missing skill** per §4 table. Inject into Skills section or weave into bullets or skip.
4. **Apply manual comments** if `WorkExpComment` or `ProjectComment` is non-empty.
5. **Compile + verify 1 page.** If 2 pages, trim per §4 remediation order.
6. **Write cover letter** following §6 five-paragraph structure (§0 Step 6 for single-job workflow). Verify no em dashes, no numbers, 1 page.

---

## 12. Common Pitfalls — Don't Repeat

- **Forgetting to escape `#` in C#** → silently drops the character. Always run skills through `latex_escape()`.
- **Substring-matching "Go" against "MongoDB" / "Django"** → use word-boundary regex.
- **Module-level `OUT_DIR` in `batch_apply.py`** → when importing `process_role()`, monkey-patch `batch_apply.OUT_DIR = <correct_folder>` first.
- **Adding "Reinforcement Learning" to AI/ML line** for non-RL roles → bloats the line and pushes to 2 pages.
- **Claiming PySpark at PwC** → inauthentic. PySpark came from NYU + Flight Delay project.
- **Engineer II routed to `_NG`** → the regex matches "engineer i" as substring of "engineer ii". Always verify NG flag against title.
- **Two roles, same company** → folder collision. Split into `<Company>_<Title_Tag>` folders.

---

End of guide. Keep this file in sync as the workflow evolves.
