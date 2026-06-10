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

for name in sorted(os.listdir(folder)):
    ext = os.path.splitext(name)[1].lower()
    if ext not in CONTENT_TYPES:
        continue
    path = os.path.join(folder, name)
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}/{name}"
    with open(path, "rb") as f:
        aws.put_audio(s3_key, f.read(), CONTENT_TYPES[ext])
    db.create_job(job_id, s3_key)
    aws.enqueue_job(job_id, s3_key)
    print("queued", name, job_id)