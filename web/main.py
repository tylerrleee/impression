"""
The upload route is a plain def, not async def, 
so FastAPI runs it in a threadpool and the blocking boto3 calls don't stall the event loop. 
The WS handler is async, so its blocking DB read goes through asyncio.to_thread.

"""
import uuid, asyncio
from fastapi import FastAPI, UploadFile, File, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from . import aws, db

app = FastAPI()

@app.get("/")

def index():
    return FileResponse("frontend/index.html")

@app.post("/api/upload")
# Duplicate upload? multiple upload 
## future check for idempotent key
def upload(file: UploadFile = File(...)):
    job_id = str(uuid.uuid4())
    s3_key = f"uploads/{job_id}/{file.filename}"
    aws.put_audio(s3_key, file.file.read(), file.content_type or "application/octet-stream")
    db.create_job(job_id, s3_key)
    aws.enqueue_job(job_id, s3_key)
    return {"job_id": job_id}

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