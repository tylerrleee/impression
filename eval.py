import requests
"""
When running web tier, user can run this file to run fixed queries to /api/search w/ top k


TODO:

- Write more test cases
- insteado f asserting by keywords, assert by job_id


In cases where the retrieval is messy, test with `bge-small` to see if it is a model or logic problem. 
Job_id | s3_key
b3428f27-0a27-4bac-bdb6-75b6f3235fb1 | uploads/b3428f27-0a27-4bac-bdb6-75b6f3235fb1/[By Jeans] ‘grentperez - Clementine’ Cover by HANNI | NewJeans.mp3
 2a924e0d-9786-475f-8be7-818843d0d2b2 | uploads/2a924e0d-9786-475f-8be7-818843d0d2b2/Big Tech Engineer in Beijing → 30, Rated “Unqualified”, Living Alone. How Did I Get Here?.mp3
 ef19c644-80ef-43aa-93f7-d1c1fb35e85b | uploads/ef19c644-80ef-43aa-93f7-d1c1fb35e85b/From Idea to $650M Exit: Lessons in Building AI Startups.mp3
 20ff15b6-85dc-4f91-a9c7-5ce19df5c011 | uploads/20ff15b6-85dc-4f91-a9c7-5ce19df5c011/Anthropic co-founder actually wants AI to slow down.mp3
 3dbc6162-b08f-4f32-9ff7-b726aea04c49 | uploads/3dbc6162-b08f-4f32-9ff7-b726aea04c49/Google Maps is unreasonably fast. Let me explain.mp3
 ed60d223-ad78-4804-a924-20aa37fb56d3 | uploads/ed60d223-ad78-4804-a924-20aa37fb56d3/i just graduated, what do I do now... - Tyler Nguyen (128k).mp3
 4c6da2a5-d409-43ec-9b13-482de535d638 | uploads/4c6da2a5-d409-43ec-9b13-482de535d638/My New $10,000,000 Food Network Show!.mp3
 bf9425cc-a296-4274-8743-7a2dcebe2482 | uploads/bf9425cc-a296-4274-8743-7a2dcebe2482/don't let AI rob you.mp3
 a6cb00e5-0b38-4108-b323-612213cb2325 | uploads/a6cb00e5-0b38-4108-b323-612213cb2325/Closing Your Mental Loops in an AI-Overloaded World | David Tufts.mp3
 f9701d84-f99f-4a16-a5ee-16115ffb74a6 | uploads/f9701d84-f99f-4a16-a5ee-16115ffb74a6/i just graduated, what do I do now... - Tyler Nguyen (128k).mp3
 1555016c-c550-420f-a5b7-49fc66895ae1 | uploads/1555016c-c550-420f-a5b7-49fc66895ae1/JUST RECORDED: Elon Musk Announces SPACEX Plans.mp3
 85a87eff-98e7-44e5-a279-484dbe43f94d | uploads/85a87eff-98e7-44e5-a279-484dbe43f94d/Introducing Claude Fable 5.mp3

"""
# (query, a substring that SHOULD appear in a top-k result)
CASES = [
    # love song
    ("romantic or cute songs", "b3428f27-0a27-4bac-bdb6-75b6f3235fb1"),
    ("living conditions of tech workers", "2a924e0d-9786-475f-8be7-818843d0d2b2"),
    ("cofounder stories" , "ef19c644-80ef-43aa-93f7-d1c1fb35e85b"),
    ("Claude coding tools", "20ff15b6-85dc-4f91-a9c7-5ce19df5c011"),
    ("finding directions", "3dbc6162-b08f-4f32-9ff7-b726aea04c49"),
    ("newgrad plans" , "ed60d223-ad78-4804-a924-20aa37fb56d3"),
    ("tv shows", "4c6da2a5-d409-43ec-9b13-482de535d638"),
    ("AI ethics and security", "bf9425cc-a296-4274-8743-7a2dcebe2482"),
    ("how to think", "a6cb00e5-0b38-4108-b323-612213cb2325"),
    ("how do i evaluate a stock?", "1555016c-c550-420f-a5b7-49fc66895ae1"),
    ("new AI", "85a87eff-98e7-44e5-a279-484dbe43f94d")
    
]

K = 5
hits = 0
for q, expected in CASES:
    rows = requests.get("http://localhost:8000/api/search",
                        params={"q": q, "k": K}).json()
    returned = [r["job_id"] for r in rows]
    found = expected in returned
    print(("HIT " if found else "MISS") + f" {q!r}")
    if not found:
        print(f"     wanted {expected}")
        print(f"     got    {returned}")
    hits += found

print(f"\nrecall@{K}: {hits}/{len(CASES)} = {hits/len(CASES):.0%}")