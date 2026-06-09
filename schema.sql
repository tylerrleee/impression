CREATE TABLE IF NOT EXISTS jobs (
  id          TEXT PRIMARY KEY,
  s3_key      TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'queued',
  progress    INT  NOT NULL DEFAULT 0,
  transcript  TEXT,
  segments    JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS chunks (
  id        BIGSERIAL PRIMARY KEY,
  job_id    TEXT NOT NULL REFERENCES jobs(id),
  start_sec REAL NOT NULL,
  end_sec   REAL NOT NULL,
  text      TEXT NOT NULL,
  embedding VECTOR(384)
);
