import os, time, json, boto3, psycopg
from dotenv import load_dotenv
load_dotenv()

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


import tempfile
from faster_whisper import WhisperModel
from sentence_transformers import SentenceTransformer
from pgvector.psycopg import register_vector
 
from opentelemetry import trace, metrics
from opentelemetry.propagate import extract
from opentelemetry.trace import SpanKind, Status, StatusCode
from obs.otel import init_telemetry

init_telemetry("worker")

SQS_URL = os.environ["SQS_QUEUE_URL"]
DSN     = os.environ["DATABASE_URL"]
S3_BUCKET = os.environ["S3_BUCKET"]
REGION  = os.environ.get("AWS_REGION", "us-east-1")
MODEL_SIZE = os.environ.get("WHISPER_MODEL", "small")

sqs     = boto3.client("sqs", region_name = REGION)
s3      = boto3.client("s3",  region_name = REGION)

tracer = trace.get_tracer("worker")
meter  = metrics.get_meter("worker")

# --- Metrics instruments (created once, used everywhere) ---
jobs_processed        = meter.create_counter("jobs_processed_total")
job_failures          = meter.create_counter("job_failures_total")
transcription_seconds = meter.create_histogram("transcription_seconds", unit = "s")
embed_seconds         = meter.create_histogram("embed_seconds", unit = "s")
chunks_per_job        = meter.create_histogram("chunks_per_job")


print(f"loading whisper model: {MODEL_SIZE}", flush=True)
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("model ready", flush=True)

embedder = SentenceTransformer("all-MiniLM-L6-v2") 
print("embedder ready", flush=True)

def window_segments(segments, target_sec = 45):
    """
    
    """
    chunks, cur, start = [], [], None
    for seg in segments:
        if not cur:
            start = seg["start"]
        cur.append(seg)
        if seg["end"] - start >= target_sec:
            words = []
            for s in cur:
                words.extend(s.get("words", []))
            chunks.append({"start" : start,
                           "end" : seg["end"],
                           "text" : " ".join(s["text"] for s in cur).strip(),
                           "words": words})
            cur = []
    if cur:
        words = []
        for s in cur:
            words.extend(s.get("words", []))
        chunks.append({"start" : start,
                       "end" : cur[-1]["end"],
                       "text" : " ".join(s["text"] for s in cur).strip(),
                       "words": words})
    return chunks

def set_status(job_id, status, progress, transcript=None):
    """
    Connect to RDS and update job status
    'queued', 'in progress', 'done'
    """
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(
            "UPDATE jobs " \
            "SET status = %s, " \
                "progress=%s " \
            "WHERE id=%s"
            , (status, progress, job_id))

def save_result(job_id, transcript, segments):
    transcript = " ".join(s["text"] for s in segments)
    chunks     = window_segments(segments)
 
    with tracer.start_as_current_span("embed") as span:
        t0 = time.perf_counter()
        vectors = embedder.encode([c["text"] for c in chunks],
                                  normalize_embeddings = True)
        embed_seconds.record(time.perf_counter() - t0)
        span.set_attribute("chunks.count", len(chunks))
    chunks_per_job.record(len(chunks))
 
    with tracer.start_as_current_span("db_write") as span:
        span.set_attribute("chunks.count", len(chunks))
        with psycopg.connect(DSN) as conn:
            register_vector(conn)
            with conn.cursor() as cur:
                cur.execute("DELETE FROM chunks WHERE job_id=%s", (job_id,))
                for c, v in zip(chunks, vectors):
                    cur.execute(
                        "INSERT INTO chunks (job_id, start_sec, end_sec, text, embedding, words) " \
                        "VALUES (%s, %s, %s, %s, %s, %s)",
                        (job_id, c["start"], c["end"], c["text"], v, json.dumps(c.get("words", [])))
                    )
                cur.execute(
                    "UPDATE jobs SET status='done' , progress = 100," \
                    "transcript=%s , segments=%s WHERE id=%s",
                    (transcript, json.dumps(segments), job_id)
                )
    print("done", job_id, f"({len(chunks)} chunks)", flush=True)

def job_done(job_id):
    """ Idempotent retries to avoid reprocessing if duplicate jobs"""
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute("SELECT status FROM jobs WHERE id=%s", (job_id,))
        row = cur.fetchone()
        return bool(row) and row[0] == "done"

def handle(job_id, s3_key):
 
    if job_done(job_id):
        print("Skipping job, already done ", job_id, flush = True)
        return
 
    set_status(job_id, "processing", 0)
    fd, path = tempfile.mkstemp(suffix = os.path.splitext(s3_key)[1])
    os.close(fd)
    try:
        with tracer.start_as_current_span("download") as span:
            span.set_attribute("s3_key", s3_key)
            s3.download_file(S3_BUCKET, s3_key, path)
 
        with tracer.start_as_current_span("transcribe") as span:
            t0 = time.perf_counter()
            seg_iter, info = model.transcribe(path, beam_size = 1, word_timestamps = True)
            total = info.duration or 0
            span.set_attribute("audio.duration", total)
            segments, last_pct = [], -1
            for seg in seg_iter:
                seg_words = []
                if seg.words:
                    for w in seg.words:
                        seg_words.append({"start": round(w.start, 2),
                                          "end": round(w.end, 2),
                                          "word": w.word.strip()})
                segments.append({"start": round(seg.start, 2),
                                 "end" : round(seg.end, 2),
                                 "text": seg.text.strip(),
                                 "words": seg_words}
                                 )
                pct = min(99, int(seg.end / total * 100)) if total else 0
                if pct != last_pct:
                    set_status(job_id, "processing", pct)
                    last_pct = pct
            transcription_seconds.record(time.perf_counter() - t0)
            span.set_attribute("segments.count", len(segments))
 
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
    print("worker up, polling", SQS_URL, flush = True)
    while True:
        resp = sqs.receive_message(QueueUrl = SQS_URL
                                   , MaxNumberOfMessages = 1
                                   , WaitTimeSeconds = 20
                                   # REQUIRED to receive the traceparent we injected
                                   # producer-side; without it SQS strips attributes.
                                   , MessageAttributeNames = ["All"])
        for msg in resp.get("Messages", []):
            body = json.loads(msg["Body"])
            print("got job", body["job_id"], flush = True)
 
            # Consumer half of propagation: rebuild the parent Context from the
            # message attributes, then open the root span as its child.
            carrier = {k: v["StringValue"]
                       for k, v in msg.get("MessageAttributes", {}).items()}
            ctx = extract(carrier)
 
            with tracer.start_as_current_span(
                "process_job", context = ctx, kind = SpanKind.CONSUMER
            ) as span:
                span.set_attribute("messaging.system", "aws_sqs")
                span.set_attribute("job_id", body["job_id"])
                span.set_attribute("s3_key", body["s3_key"])
                try:
                    handle(body["job_id"], body["s3_key"])
                    sqs.delete_message(QueueUrl = SQS_URL,
                                       ReceiptHandle = msg["ReceiptHandle"]
                                       )
                    jobs_processed.add(1, {"outcome": "success"})
                except Exception as e:
                    span.record_exception(e)
                    span.set_status(Status(StatusCode.ERROR))
                    job_failures.add(1)
                    print("job failed, leaving on queue:", e, flush = True)
 
if __name__ == "__main__":
    main()



    
        
