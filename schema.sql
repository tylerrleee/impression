CREATE TABLE IF NOT EXISTS jobs (
  id          TEXT PRIMARY KEY,
  s3_key      TEXT NOT NULL,
  status      TEXT NOT NULL DEFAULT 'queued',
  progress    INT  NOT NULL DEFAULT 0,
  transcript  TEXT,
  segments    JSONB,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);