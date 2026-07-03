"""
The upload route is a plain def, not async def, 
so FastAPI runs it in a threadpool and the blocking boto3 calls don't stall the event loop. 
The WS handler is async, so its blocking DB read goes through asyncio.to_thread.

"""
import uuid, asyncio, os
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import FileResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from . import aws, db
from .ratelimit import limiter
from sentence_transformers import SentenceTransformer

app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
embedder = SentenceTransformer("all-MiniLM-L6-v2")   # same model as the worker

@app.get("/")


def index():
    return FileResponse("frontend/index.html")

@app.post("/api/upload")
@limiter.limit("10/hour")
# Duplicate upload? multiple upload
## future check for idempotent key
def upload(request: Request, file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}/{file.filename}"
    aws.put_audio(s3_key, file.file.read(), file.content_type or "application/octet-stream")
    title = os.path.splitext(file.filename)[0] if file.filename else None
    db.create_job(job_id, s3_key, title=title)
    aws.enqueue_job(job_id, s3_key)
    return {"job_id": job_id}

@app.get("/api/search")
@limiter.limit("30/minute")
def search(request: Request, q: str, k: int = 5):
    vec  = embedder.encode(q, normalize_embeddings=True)
    rows = db.search_chunks(vec, k)
    return [{"job_id": r[0], "start": round(r[1], 1),
             "end": round(r[2], 1), "text": r[3],
             "title": r[4], "source_url": r[5],
             "score": round(r[6], 4)} for r in rows]

@app.get("/api/chunks")
def chunks(job_id: str):
    rows = db.get_chunks(job_id)
    return [{"start": round(r[0], 1), "end": round(r[1], 1), "text": r[2], "words": r[3]} for r in rows]

@app.get("/api/audio_url")
@limiter.limit("60/minute")
def audio_url(request: Request, job_id: str):
    key = db.get_s3_key(job_id)
    if not key:
        raise HTTPException(404, "job not found")

    return {"url": aws.presign_audio(key)}

@app.websocket("/ws/{job_id}")
async def progress(ws: WebSocket, job_id: str):
    await ws.accept()
    last = None
    try:
        while True:
            job = await asyncio.to_thread(db.get_job, job_id)
            if job is None:
                await ws.send_json({"status" : "unknown"})
                return
            key = (job["status"], job["progress"])
            if key != last:
                await ws.send_json(job)
                last = key
            if job["status"] == "done":
                return
            await asyncio.sleep(0.5)
    except WebSocketDisconnect:
        return