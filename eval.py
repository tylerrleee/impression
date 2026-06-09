import requests
"""
When running web tier, user can run this file to run fixed queries to /api/search w/ top k
"""
# (query, a substring that SHOULD appear in a top-k result)
CASES = [
    # --- 1. Synonyms & Paraphrasing (Semantic should win) ---
    # The user searches a concept, but the transcript uses different words.
    ("financial constraints", "budget"),
    ("fixing software issues", "debugging"),
    ("reducing expenses", "cost cutting"),
    
    # --- 2. Concept to Specific Entity (Semantic should win) ---
    # The user searches a broad category, expecting a specific noun/tool.
    ("container orchestration", "Kubernetes"),
    ("smartphone manufacturer", "Apple"), # or "Samsung"
    ("relational database", "Postgres"),

    # --- 3. Acronyms & Expansions (Hybrid) ---
    # Testing if the embedder maps the abbreviation to the full words.
    ("artificial intelligence", "AI"),
    ("large language models", "LLM"),
    ("Amazon Web Services", "AWS"),

    # --- 4. Conversational/Audio Speech (Semantic should win) ---
    #  idioms and casual phrasing.
    ("let's sync up later", "schedule a meeting"),
    ("touch base", "follow up"),

    # --- 5. Exact Identifiers & Hard Constraints (Keyword should win) ---
    # Vector embeddings often blur exact numbers or specific IDs
    ("ticket 8675", "8675"),
    ("error code 500", "internal server error"),
    ("job a38c3a6d", "a38c3a6d") 
]

K = 5
hits = 0
for q, expected in CASES:
    rows = requests.get("http://localhost:8000/api/search",
                        params={"q": q, "k": K}).json()
    found = any(expected.lower() in r["text"].lower() for r in rows)
    print(("HIT " if found else "MISS") + f" {q!r}")
    hits += found
print(f"\nrecall@{K}: {hits}/{len(CASES)} = {hits/len(CASES):.0%}")