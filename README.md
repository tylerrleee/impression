# Impression

Semantic search over archival audio. You ingest a library of spoken-word audio
(podcasts, talks, lectures), and search it by **meaning** rather than keywords.
Results come back as timestamped, playable clips. Search returns the moment
someone *said* the thing, and the player seeks straight to it.

**Live demo:** https://demo.tylerle.net
(search and playback only - ingestion is an offline operator tool, see below)

---

## Why I built this

I like the idea of podcasts and listening to them (espcially Rotten Mango, The Peterman, Hasan Minhaj..). However, I do not usually seem to be able to remember much of the content, and backtracking is a hassle. 
I don't want to eyeball the exact timestamp or the exact podcast that I listened to when I went to the gym a few days ago. 

This tool helps -- and I hope it will for others -- me interact with a piece of auxiliary in a more approachable manner, 


## TLDR

Type a query like *"What are the signals for SpaceX before they IPO"* and get back the
exact n-segments of where a speaker discussed that idea, even if they never
used those words. Click play and the audio jumps to that timestamp.

Main functions:

1. **Transcribe** audio to text with timestamps (Whisper).
2. **Chunk and embed** the transcript into a vector store, so meaning is
   searchable.
3. **Serve** vector search with playback into the original
   audio by timestamp.

 Transcription and embedding happen once, offline, at ingest time. Everything a visitor does
runs on an EC2 instance that queries RDS Postgres and pgvector, and return a chunk of similar embedding vector. 

---

## Architecture

```
                          INGEST (offline, operator-run)
   ┌────────────┐   put    ┌────────┐   enqueue   ┌────────┐   poll   ┌──────────┐
   │ ingest.py  │ ───────► │   S3   │             │  SQS   │ ◄─────── │  worker  │
   │ (your box) │          │ audio  │ ──────────► │ jobs   │          │ (CPU)    │
   └────────────┘          └────────┘             └────────┘          └────┬─────┘
         │                                                                  │
         │ create job row                                                   │ transcribe (faster-whisper)
         ▼                                                                  │ chunk + embed (MiniLM)
   ┌─────────────────────────────────────────────────────────────────────┐ │
   │                         RDS Postgres + pgvector                       │◄┘
   │   jobs(job_id, s3_key, status)   chunks(job_id, start, end, text, vec)│
   └─────────────────────────────────────────────────────────────────────┘
         ▲                                                  ▲
         │ query embed + vector search                      │ presign GET
   ┌─────┴───────┐                                          │
   │   web (CPU) │  ◄──── Caddy (TLS) ◄──── visitor ────────┘
   │  FastAPI    │
   └─────────────┘                         SERVE (always-on, public)
```

**Two decoupled paths.** Ingestion (write-heavy, slow, expensive) is fully
separated from serving (read-heavy, fast, cheap). 

### Serving path 

- **Caddy** terminates TLS (automatic Let's Encrypt) and reverse-proxies to the
  web tier.
- **FastAPI (CPU)** embeds the search query with the same model used at ingest,
  runs a pgvector cosine-similarity search, and returns the top-k chunks with
  timestamps. For playback it issues a short-lived **presigned S3 URL**, so audio
  streams directly from S3 to the browser (with HTTP range requests for seeking)
  and never proxies through the app.
- **RDS Postgres + pgvector** holds transcripts, chunks, and 384-dim embeddings.

### Ingestion path (offline, operator-run)

- **`ingest.py`** uploads each audio file to S3, writes a job row, and enqueues a
  job ID on **SQS**.
- A **worker** long-polls SQS, downloads the audio, transcribes it with
  **faster-whisper**, chunks the transcript into overlapping timestamped windows,
  embeds each chunk, and writes everything to Postgres.
- The worker is **idempotent**: it deletes prior chunks for a job before
  inserting, and does not delete the SQS message until the job succeeds. A crash
  or restart re-processes cleanly instead of corrupting or duplicating data. A
  dead-letter queue catches messages that fail repeatedly.

Ingestion currently runs on **CPU** and is triggered manually by the operator.
The public demo deliberately does **not** expose uploads (the serving tier's IAM
role has no `PutObject`), so visitors cannot trigger compute or store arbitrary
files.

---

## Retrieval

- **Transcription:** `faster-whisper`, `small` model, int8. Streams segments so
  ingest shows real percent-complete (`segment.end / info.duration`).
- **Chunking:** transcript segments are grouped into ~45s overlapping windows,
  each carrying `start_sec` / `end_sec` so a result maps back to a position in the
  audio.
- **Embeddings:** `sentence-transformers/all-MiniLM-L6-v2` (384-dim). The *same*
  model embeds chunks at ingest and queries at search time, which is what makes
  similarity meaningful.
- **Search:** pgvector cosine distance (`<=>`), top-k, joined back to the parent
  job for playback.

### Evaluation

Retrieval quality is measured with a small **hand-labeled eval harness**
(`eval.py`): a set of natural-language queries, each labeled with the job that
contains the answer, scored by **recall@k**.

Current result: **recall@5 of ~64% over 15 hand-labeled queries.**

- The harness mattered more than the number. The first run scored 2/10 because the eval cases were invalid (queries
about topics that weren't in the corpus, plus one non-English file the embedding
model can't represent).  
- Ground truth is
established by locating the answering chunk directly
(`SELECT job_id FROM chunks WHERE text ILIKE '%...%'`) and asserting on `job_id`,
not on brittle substring matches.

---

## Stack

| Layer        | Choice                                             |
|--------------|----------------------------------------------------|
| Web API      | FastAPI (CPU), behind Caddy (auto-TLS)             |
| ASR          | faster-whisper (`small`, int8)                     |
| Embeddings   | sentence-transformers MiniLM-L6-v2 (384-dim)      |
| Vector store | Postgres + pgvector on RDS                         |
| Storage      | S3 (audio), presigned GET for playback            |
| Queue        | SQS (jobs) + dead-letter queue                     |
| Infra        | Terraform (S3, SQS, RDS), Docker Compose, EC2     |
| Auth to AWS  | EC2 instance role (no static keys on the box)     |

---

## Running locally

```bash
# 1. Postgres with pgvector
docker compose up -d            # brings up pgvector/pgvector:pg16
psql ... -f schema.sql          # creates extension + tables

# 2. env
cp .env.example .env            # DATABASE_URL, S3_BUCKET, AWS_REGION

# 3. web tier
uvicorn web.main:app --reload

# 4. ingest a folder of audio (offline)
python ingest.py sample_audio/

# 5. run the worker to process the queue
python worker/worker.py
```

`DATABASE_URL` must be a full DSN
(`postgresql://user:pass@host:5432/db`). Use `localhost` for host processes,
`db:5432` inside Compose, or the RDS endpoint in production.

---
