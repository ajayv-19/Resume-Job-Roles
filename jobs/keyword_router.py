#!/usr/bin/env python3
"""Base-template router.

The router reads the entire job description and makes the routing decision based
on the full posting, not on any single signal in isolation. Specifically it
combines the title, the JD description body, and the matched/missing skills
list from Jobright.

Two-step routing:
  1. **Family detection** — read the title, JD body, and skills together. Pick
     the family (DE / AI / FE / FS / SEJ / SE) based on what the posting actually
     asks for.
  2. **Sub-variant scoring** — within the chosen family, score candidates by
     keyword overlap with the JD's matched + missing skills + title tokens.
     Pick the highest.

Hard rules:
- NEVER auto-route to `_L` (LinkedIn-only variants are a manual choice).
- More-specific title keywords (Java, Full Stack, Frontend) override generic "Software Engineer".
- New-grad signals trigger _NG suffix swap when an _NG variant exists.
"""

import json
import re
from pathlib import Path

ROOT = Path("/Users/ajayvenkatesh/Desktop/Resume Job Roles")
MASTER = ROOT / "base_templates.json"


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9+#.]", " ", (s or "").lower()).strip()


def _tokens(s: str) -> set[str]:
    cleaned = _norm(s)
    parts = cleaned.split()
    out = set(parts)
    for n in (2, 3):
        for i in range(len(parts) - n + 1):
            out.add(" ".join(parts[i : i + n]))
    return out


def load_templates() -> list[dict]:
    return json.loads(MASTER.read_text())["templates"]


def _has_word(text: str, word: str) -> bool:
    """Word-boundary check."""
    return bool(re.search(rf"\b{re.escape(word)}\b", text))


# ---------------- Family detection ----------------

# Order matters: most specific first
FAMILY_RULES = [
    # (family_code, phrases that must appear as substrings in lowercased title)
    ("DE",  ["data engineer", "data engineering", "analytics engineer",
              "big data engineer", "etl engineer", "data platform engineer",
              "data warehouse engineer", "bi engineer", "business intelligence"]),
    ("AI",  ["machine learning engineer", "ml engineer", "ai engineer",
              "ai/ml engineer", "applied scientist", "research scientist",
              "deep learning engineer", "nlp engineer", "computer vision engineer",
              "generative ai", " genai ", "agentic ai", "ai/ml",
              "llm engineer", "llm scientist"]),
    ("FE",  ["frontend", "front-end", "front end", "ui engineer",
              "frontend engineer", "ui developer"]),
    ("FS",  ["full stack", "full-stack", "fullstack",
              "android", "ios developer", "mobile engineer"]),
    ("SEJ", []),    # handled with word-boundary check below
    ("SE",  []),    # default fallthrough
]


def detect_family(title: str, matched: list[str] | None = None,
                   jd_text: str | None = None) -> str:
    """Read the entire job description and decide which template family fits.

    The function inspects three signals together:
      1. The job title text.
      2. The full job description body (required skills, preferred skills, responsibilities).
      3. The matched-skills list from Jobright.

    All three are evaluated. The family is chosen based on what the full posting
    actually asks for, not on any single signal in isolation.
    """
    t = title.lower()
    # Step 1: Title — strongest signal
    for fam, phrases in FAMILY_RULES:
        if fam == "SEJ":
            if _has_word(t, "java") or _has_word(t, "kotlin") or "j2ee" in t \
               or "spring boot" in t or "(java)" in t:
                return "SEJ"
        if fam == "SE":
            break
        for phrase in phrases:
            if phrase in t:
                return fam

    # Step 2: JD body — required-language patterns
    jd = (jd_text or "").lower()
    if jd:
        # Look for "required" / "must have" / "strong experience with" patterns paired with a language
        if re.search(r"(required|must have|strong experience with|strong knowledge of|proficien[ct][^.]{0,60})[^.]{0,80}\bjava\b", jd) \
           or re.search(r"\bspring boot\b[^.]{0,100}(required|primary|main)", jd):
            return "SEJ"
        if re.search(r"(required|must have|strong experience with)[^.]{0,80}\b(machine learning|ml|llm|deep learning|pytorch|tensorflow)\b", jd):
            return "AI"
        if re.search(r"(required|must have|strong experience with)[^.]{0,80}\b(data engineer|etl|spark|airflow|snowflake)\b", jd):
            return "DE"

    # Step 3: Matched skills — secondary signal
    matched_lower = {m.lower() for m in (matched or [])}
    java_signals = {"java", "spring boot", "spring", "j2ee", "java ee", "hibernate", "maven"}
    if len(matched_lower & java_signals) >= 2:
        return "SEJ"
    ai_signals = {"pytorch", "tensorflow", "rag", "langchain", "hugging face", "fine-tuning",
                  "llm", "deep learning", "transformers", "embeddings", "machine learning"}
    if len(matched_lower & ai_signals) >= 3:
        return "AI"
    de_signals = {"spark", "apache spark", "pyspark", "airflow", "snowflake", "bigquery",
                  "redshift", "etl", "data pipelines"}
    if len(matched_lower & de_signals) >= 2:
        return "DE"

    return "SE"


# ---------------- New-grad detection ----------------

def detect_new_grad(title: str) -> bool:
    t = title.lower()
    senior = any(k in t for k in (
        "senior", " sr.", " sr ", "lead", "principal", "staff", "manager",
        " iii", " iv"
    ))
    if senior:
        return False
    new_grad_kw = (
        "new grad", "new graduate", "recent graduate", "early career", "early-career",
        "entry level", "entry-level", "junior", "graduate", "trainee",
        "engineer 1", "engineer i ", "engineer i,", "engineer i)",
        "level 1", "level i", "emerging talent", "rotational",
    )
    return any(k in t for k in new_grad_kw)


# ---------------- Within-family scoring ----------------

# Family code → candidate template codes (in preferred order)
FAMILY_CANDIDATES = {
    "DE":  ["DE_E"],
    "AI":  ["AI_E", "AI_NG"],   # _NG swap handled downstream
    "FE":  ["FE_E"],
    "FS":  ["FS_E"],
    "SEJ": ["SEJ_E", "SEJ_NG"],
    "SE":  ["SEP_E", "SEP_NG", "SEAI_E", "SELLM_E", "CE_E"],
}


def _score_keywords(template: dict, *, title: str, matched: list[str], missing: list[str]) -> dict:
    """Skill-keyword overlap score for tie-breaking within a family."""
    kw_set = {_norm(k) for k in template["keywords"]}
    title_tokens = _tokens(title)
    matched_norm = {_norm(m) for m in matched}
    missing_norm = {_norm(m) for m in missing}

    matched_hits = kw_set & matched_norm
    missing_hits = kw_set & missing_norm
    title_hits = kw_set & title_tokens

    # Within-family scoring weights: title slightly stronger than matched skills
    score = 3 * len(title_hits) + 2 * len(matched_hits) + 1 * len(missing_hits)

    return {
        "code": template["code"],
        "matched_hits": sorted(matched_hits),
        "missing_hits": sorted(missing_hits),
        "title_hits": sorted(title_hits),
        "score": score,
    }


# ---------------- Main router ----------------

def pick_template(*, title: str, matched: list[str], missing: list[str],
                  jd_text: str | None = None,
                  exclude_linkedin: bool = True, verbose: bool = False) -> dict:
    """Pick the best template by reading the entire job description.

    Pass the full job description text via `jd_text`. The router reads the title,
    the JD body, and the matched/missing skills together, and chooses the family
    based on what the posting actually asks for.

    `_L` (LinkedIn) variants are excluded by default — they're a manual choice.
    """
    templates = load_templates()
    if exclude_linkedin:
        templates = [t for t in templates if not t["code"].endswith("_L")]
    tpl_by_code = {t["code"]: t for t in templates}

    # Step 1: Detect family (uses title → JD body → matched skills, in that priority)
    family = detect_family(title, matched=matched, jd_text=jd_text)
    is_ng = detect_new_grad(title)
    candidates = [c for c in FAMILY_CANDIDATES.get(family, ["SEP_E"]) if c in tpl_by_code]

    # Step 2: Score candidates by keyword overlap
    scored = [_score_keywords(tpl_by_code[c], title=title, matched=matched, missing=missing)
              for c in candidates]

    # Sort: highest score wins; tiebreak prefers the first candidate in FAMILY_CANDIDATES order
    candidate_order = {c: i for i, c in enumerate(candidates)}
    scored.sort(key=lambda s: (-s["score"], candidate_order.get(s["code"], 999)))

    best = scored[0] if scored else {"code": "SEP_E", "score": 0,
                                       "matched_hits": [], "missing_hits": [], "title_hits": []}

    # Step 3: NG suffix swap if title says new-grad and an _NG sibling exists
    if is_ng:
        ng_code = best["code"].rsplit("_", 1)[0] + "_NG"
        if ng_code in tpl_by_code:
            best = {**best, "code": ng_code, "swapped_to_NG": True}

    result = {**best, "family": family, "is_new_grad": is_ng}
    if verbose:
        result["all_scores"] = scored
    return result


if __name__ == "__main__":
    test_cases = [
        # (title, matched, missing, expected_code)
        ("Software Engineer, Full Stack", ["Python", "React", "Node.js", "MongoDB"], ["GCP"], "FS_E"),
        ("Senior Software Engineer, Event Response", ["C++", "Python", "Java", "Distributed Systems"], ["Robotics"], "SEJ_E"),
        ("Java Software Developer", ["Java", "Spring Boot", "Microservices"], ["Kotlin"], "SEJ_E"),
        ("AI Engineer", ["PyTorch", "RAG", "LangChain"], ["JAX"], "AI_E"),
        ("Software Engineer (LLM Inference)", ["PyTorch", "JAX", "vLLM", "C++"], ["Dynamo"], "SELLM_E"),
        ("Data Engineer", ["Spark", "Airflow", "Snowflake"], ["dbt"], "DE_E"),
        ("Software Engineer", ["Python", "AWS", "MySQL"], [], "SEP_E"),
        ("Frontend Engineer", ["React", "TypeScript", "CSS"], ["Vue"], "FE_E"),
        ("Junior Java Engineer", ["Java", "Spring Boot"], [], "SEJ_NG"),
        ("Engineer 1 - Customer Experience Platform", ["Python", "Java", "AWS"], [], "SEP_NG"),
        ("Senior .NET Developer", ["C#", ".NET", "Azure", "SQL Server"], [], "SEP_E"),  # CE_E in SE family
        ("Software Engineer (AI/ML Agentic AI Systems)", ["Python", "RAG", "PyTorch"], ["LangGraph"], "AI_E"),
    ]
    print(f"{'TITLE':60} | {'PICKED':10} | {'EXPECTED':10} | {'FAMILY':4} | NG?")
    print("-" * 110)
    for title, matched, missing, expected in test_cases:
        r = pick_template(title=title, matched=matched, missing=missing)
        ok = "✓" if r["code"] == expected else "✗"
        print(f"{ok} {title[:58]:58} | {r['code']:10} | {expected:10} | {r['family']:4} | {r.get('is_new_grad')}")
