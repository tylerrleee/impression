import os, time, json, boto3, psycopg
import tempfile
from faster_whisper import WhisperModel

SQS_URL = os.environ["SQS_QUEUE_URL"]
DSN     = os.environ["DATABASE_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]
REGION  = os.environ.get("AWS_REGION", "us-east-1")
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")

sqs     = boto3.client("sqs", region_name = REGION)
s3      = boto3.client("s3",  region_name = REGION)

print(f"loading whisper model: {MODEL_SIZE}", flush=True)
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("model ready", flush=True)


def set_status(job_id, status, progress, transcript=None):
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(
            "UPDATE jobs " \
            "SET status = %s, " \
                "progress=%s " \
            "WHERE id=%s"
            , (status, progress, job_id))

def save_result(job_id, transcript, segments):
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(
            "UPDATE jobs SET status='done', progress=100, "
            "transcript=%s, segments=%s WHERE id=%s",
            (transcript, json.dumps(segments), job_id))
        

def handle(job_id, s3_key):
    set_status(job_id, "processing", 0)
    fd, path = tempfile.mkstemp(suffix = os.path.splitext(s3_key)[1])
    os.close(fd)
    try:
        s3.download_file(S3_BUCKET, s3_key, path)
        seg_iter, info = model.transcribe(path, beam_size = 1)
        total = info.duration or 0
        segments, last_pct = [], -1
        for seg in seg_iter:
            segments.append({"start": round(seg.start, 2),
                             "end" : round(seg.end, 2),
                             "text": seg.text.strip()}
                             )
            pct = min(99, int(seg.end / total * 100)) if total else 0
            if pct != last_pct:
                set_status(job_id, "processing", pct)
                last_pct = pct
        
        transcript = " ".join(s["text"] for s in segments)
        save_result(job_id, transcript, segments)
        print("done", job_id, f"({len(segments)} segments)", flush=True)

    except Exception as e:
        print(f"Failed to process job {job_id}: {e}", flush=True)
        set_status(job_id, "failed", 0)
        raise e
    finally:
        os.remove(path)


def main():
    print("worker up, pollong", SQS_URL, flush = True)
    while True:
        resp = sqs.receive_message(QueueUrl = SQS_URL
                                   , MaxNumberOfMessages = 1
                                   , WaitTimeSeconds = 20)
        for msg in resp.get("Messages", []):
            body = json.loads(msg["Body"])
            print("got job", body["job_id"], flush = True)
            try:
                handle(body["job_id"], body["s3_key"])
                sqs.delete_message(QueueUrl = SQS_URL,
                                   ReceiptHandle = msg["ReceiptHandle"]
                                   )
            except Exception as e:
                print("job failed, leaving on queue:", e, flush = True)

if __name__ == "__main__":
    main()


    
        
