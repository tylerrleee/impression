import sys, os, uuid
from dotenv import load_dotenv

load_dotenv()

from web import aws, db

CONTENT_TYPES = {
    ".mp3":  "audio/mpeg",
    ".mp4":  "audio/mp4",
    ".m4a":  "audio/mp4",
    ".wav":  "audio/wav",
    ".flac": "audio/flac",
    ".ogg":  "audio/ogg",
}

folder = sys.argv[1]

# optional urls.txt: each line is "filename\tURL"
url_map = {}
urls_path = os.path.join(folder, "urls.txt")
if os.path.exists(urls_path):
    with open(urls_path) as f:
        for line in f:
            line = line.strip()
            if not line or '\t' not in line:
                continue
            fname, url = line.split('\t', 1)
            url_map[fname] = url

for name in sorted(os.listdir(folder)):
    ext = os.path.splitext(name)[1].lower()
    if ext not in CONTENT_TYPES:
        continue
    path = os.path.join(folder, name)
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}/{name}"
    with open(path, "rb") as f:
        aws.put_audio(s3_key, f.read(), CONTENT_TYPES[ext])
    title = os.path.splitext(name)[0]
    source_url = url_map.get(name)
    db.create_job(job_id, s3_key, title=title, source_url=source_url)
    aws.enqueue_job(job_id, s3_key)
    print("queued", name, job_id)