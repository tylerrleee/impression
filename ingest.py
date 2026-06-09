import sys, os, uuid, mimetypes
from dotenv import load_dotenv

load_dotenv()

from web import aws, db


#  python ingest.py sample_audio/youtube 
folder = sys.argv[1]
AUDIO = {".mp3", ".mp4", ".wav", ".m4a", ".flac", ".ogg"}

for name in sorted(os.listdir(folder)):
    if os.path.splitext(name)[1].lower() not in AUDIO:
        continue
    path = os.path.join(folder, name)
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}/{name}"
    with open(path, "rb") as f:
        aws.put_audio(s3_key, f.read(),
                        mimetypes.guess_type(name)[0] or "application/octet-stream"
            )
    db.create_job(job_id, s3_key)
    aws.enqueue_job(job_id, s3_key)
    print("queued", name, job_id)

