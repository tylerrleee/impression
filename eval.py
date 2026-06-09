import requests
"""
When running web tier, user can run this file to run fixed queries to /api/search w/ top k


TODO:

- Write more test cases
- insteado f asserting by keywords, assert by job_id


In cases where the retrieval is messy, test with `bge-small` to see if it is a model or logic problem. 
"""
# (query, a substring that SHOULD appear in a top-k result)
CASES = [
    ("will AI replace software engineers", "software engineering"),
    ("becoming a spacefaring civilization with reusable rockets", "Kardashev"),
    ("starting a small business after losing my job", "pet supplies"),
    ("the best kind of gummy bears", "gummy bears"),
    ("valuation of spacex when it becomes public", "public"),
    ("how can i navigate in this city", "Google Maps"),
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