 Add a Data Engineering Layer to Impression (Airflow + Spark + OpenTelemetry)

 Context

 Impression today is a manual, opaque, single-worker pipeline: an operator runs ingest.py
 by hand → SQS → one single-threaded worker.py → pgvector. There is no observability
 (only print() to stdout), no orchestration (manual CLI, no schedules, no DLQ visibility),
 and no batch-compute plane (re-embedding or analytics would be ad-hoc scripts).

 Goal (per user): a portfolio-showcase Data Engineering layer that demonstrates breadth across
 OpenTelemetry, Airflow, and Spark, phased in that order, running hybrid — developed locally
 on docker-compose, with Terraform written so it maps cleanly to AWS (MWAA / EMR / managed OTLP) later.

 We wrap the existing two paths (ingest / serve) in three planes without rewriting them:

 ┌───────────────┬───────────────┬──────────────────────────────────────────────────────────────────────────────┬─────────┐
 │     Plane     │     Tool      │                                     Adds                                     │ Status  │
 ├───────────────┼───────────────┼──────────────────────────────────────────────────────────────────────────────┼─────────┤
 │ Observability │ OpenTelemetry │ traces across the async SQS boundary + metrics → Grafana                     │ Phase A │
 ├───────────────┼───────────────┼──────────────────────────────────────────────────────────────────────────────┼─────────┤
 │ Control       │ Airflow       │ scheduled ingestion, nightly eval quality-gate, DLQ triage, backfill trigger │ Phase B │
 ├───────────────┼───────────────┼──────────────────────────────────────────────────────────────────────────────┼─────────┤
 │ Batch compute │ Spark         │ distributed re-embedding backfill + medallion analytics tables               │ Phase C │
 └───────────────┴───────────────┴──────────────────────────────────────────────────────────────────────────────┴─────────┘

 They interlock: an Airflow DAG triggers the Spark backfill; OTel traces carry the Airflow run_id
 and the SQS job_id end-to-end.

 ---
 Phase A — OpenTelemetry (observability plane)

 Why first: highest value, lowest risk, and the artifacts (a single trace spanning enqueue →
 transcription → embedding → DB write across SQS) become the demo centerpiece.

 A1. Shared instrumentation module

 - New obs/otel.py (importable by both web/ and worker/): one init_telemetry(service_name)
 helper that wires the OTLP exporter (endpoint from OTEL_EXPORTER_OTLP_ENDPOINT), a tracer, and a
 meter. Keep it a no-op if the env var is unset so local runs without the stack still work.
 - Add to web/requirements.txt and worker/requirements.txt:
 opentelemetry-sdk, opentelemetry-exporter-otlp,
 opentelemetry-instrumentation-fastapi, opentelemetry-instrumentation-psycopg,
 opentelemetry-instrumentation-botocore.

 A2. Worker spans + context propagation (the showcase)

 - In worker/worker.py:
   - main() (line 132): after receive_message, extract trace context from the SQS message
 attributes and start the root span; this is the consumer half of the propagation.
   - handle() (line 89): child spans for download, transcribe (wrap the loop at line 100),
 embed (in save_result, line 62), db_write (line 65). Tag spans with job_id, s3_key,
 audio.duration, chunks.count.
   - Metrics: jobs_processed_total (counter), transcription_seconds + embed_seconds
 (histograms), chunks_per_job (histogram), job_failures_total (counter in the except,
 line 124).
 - In ingest.py (line 43) and web/main.py upload (line 31): when calling aws.enqueue_job,
 inject the current trace context into the SQS MessageAttributes. This requires a small
 signature change to aws.enqueue_job to accept/forward message attributes.

 A3. Web auto-instrumentation + search SLI

 - In web/main.py: call FastAPI + psycopg instrumentors at startup. The /api/search path
 (line 34) auto-traces the request and the pgvector <=> query as a child span.
 - Add a search_latency_seconds histogram and a search_results_returned histogram.
 - A background gauge polling SQS ApproximateNumberOfMessages → queue_depth (cheap, every 15s).

 A4. Local stack (docker-compose)

 - New docker-compose.obs.yml (overlay, kept separate from prod): otel-collector
 (config obs/otel-collector.yaml) → Jaeger (traces) + Prometheus
 (obs/prometheus.yml) + Grafana (provisioned dashboard obs/grafana/).
 - Wire worker and web services' OTEL_EXPORTER_OTLP_ENDPOINT to the collector.

 A5. AWS stub (hybrid)

 - infra/observability.tf (commented/stub): notes for pointing the collector at AWS managed
 Prometheus (AMP) + X-Ray, or running the collector as a sidecar. No live resources yet.

 ---
 Phase B — Airflow (control plane)

 Why second: it replaces the manual operator step and gives a UI full of green DAG runs — strong
 portfolio visual. Reuses Phase A: tasks call instrumented code so DAG runs show up in traces.

 B1. Airflow service

 - New docker-compose.airflow.yml overlay: airflow-webserver + airflow-scheduler +
 airflow-init (LocalExecutor, Postgres metadata DB — can reuse the existing compose Postgres
 with a separate database). DAGs mounted from airflow/dags/.
 - airflow/requirements.txt pins providers (apache-airflow-providers-amazon for SQS/S3).

 B2. DAGs (airflow/dags/)

 1. ingest_dag.py — scheduled discovery of new audio in an S3 inbox/ prefix (or a watched
 folder mount): list → for each new object, create a job row + enqueue SQS. Replaces the manual
 ingest.py loop; reuses web.db.create_job and web.aws.enqueue_job. Idempotent on job_id.
 2. eval_quality_gate_dag.py — nightly: run the existing eval.py recall@k, write the score to
 a new eval_runs table (timestamped), and fail the DAG / alert if recall regresses below a
 threshold. This is data-quality monitoring over time.
 3. dlq_triage_dag.py — periodic: poll the SQS dead-letter queue, classify failures, redrive
 transient ones to the main queue, alert on poison jobs. Operationalizes the DLQ that exists in
 infra/main.tf but has zero visibility today.
 4. reembed_backfill_dag.py — manual/triggered: kicks off the Phase-C Spark job and waits for
 completion (the Airflow→Spark seam).

 B3. Schema additions (schema.sql)

 - eval_runs (id, run_at, k, recall_at_k, n_queries, model_name, notes) — quality-gate history.
 - (Optional) search_logs (id, q, k, n_results, top_score, latency_ms, ts) — written from
 web/main.py /api/search; feeds Phase C analytics and zero-result analysis.

 B4. AWS stub (hybrid)

 - infra/airflow.tf (stub): notes/skeleton for MWAA (environment, S3 DAGs bucket, execution
 role). Not applied; documents the local→cloud mapping.

 ---
 Phase C — Spark (batch compute plane)

 Why last + framed honestly: at current corpus size Spark adds nothing to ingestion. It earns
 its place as the backfill + analytics layer that "scales when the corpus does." Triggered by
 Airflow (B2.4), exported to Grafana (Phase A).

 C1. Distributed re-embedding backfill (the real Spark use)

 - New spark/reembed.py: read chunks via JDBC → repartition → mapPartitions loads the
 sentence-transformer once per partition → re-encode text → write vectors back. This is the
 textbook DE migration job for the day all-MiniLM-L6-v2 is swapped for a new model (and the
 VECTOR(384) column / dim changes). Idempotent by chunk.id.

 C2. Medallion analytics (bronze → silver → gold)

 - New spark/analytics.py: read jobs.transcript / chunks / search_logs (silver) → build
 gold tables: word/topic frequency, chunk-length distribution, corpus growth over time,
 zero-result query analysis from search_logs. Write gold tables back to Postgres (or Parquet
 in S3) for a Grafana "corpus analytics" dashboard.

 C3. Local + AWS stub (hybrid)

 - New docker-compose.spark.yml overlay: a Spark master + worker (bitnami/spark) for local runs;
 spark-submit driven by the Airflow DAG.
 - infra/spark.tf (stub): skeleton for EMR Serverless (or Glue) application + job-run role +
 S3 scripts bucket, mirroring the local job. Not applied.

 ---
 Critical files

 Modify: worker/worker.py (spans + metrics + SQS context extract), web/main.py
 (instrument + search SLI + search_logs write), ingest.py (SQS context inject),
 web/aws.py (enqueue_job forwards message attributes), web/requirements.txt,
 worker/requirements.txt, schema.sql (eval_runs, search_logs).

 Add: obs/ (otel.py, collector + prometheus + grafana configs),
 docker-compose.obs.yml, airflow/ (dags + requirements), docker-compose.airflow.yml,
 spark/ (reembed.py, analytics.py), docker-compose.spark.yml,
 infra/observability.tf, infra/airflow.tf, infra/spark.tf (all stubs),
 plus a docs/data-engineering.md write-up tying the three planes together for the portfolio.

 Reuse (do not reimplement): web.db.create_job, web.aws.enqueue_job, web.db.search_chunks,
 worker.window_segments, eval.py's recall@k logic.

 ---
 Verification (end-to-end)

 1. Phase A: docker compose -f docker-compose.yml -f docker-compose.obs.yml up, ingest a
 30s clip, then open Jaeger and confirm a single trace spans enqueue → transcribe → embed
 → db_write with the right job_id. Open Grafana and confirm transcription_seconds,
 queue_depth, and search_latency_seconds populate after a search.
 2. Phase B: bring up the Airflow overlay, drop a file in the S3 inbox/ prefix, trigger
 ingest_dag and watch it create the job + enqueue. Trigger eval_quality_gate_dag and confirm a
 row lands in eval_runs; verify it fails when recall is below threshold (temporarily lower the
 bar to prove the gate).
 3. Phase C: trigger reembed_backfill_dag → Spark job re-encodes all chunks; confirm vectors
 change and eval.py recall is unchanged (same model) or shifts (new model). Run analytics.py
 and confirm gold tables/Parquet populate and render in the Grafana analytics dashboard.
 4. Regression guard: existing /api/search and playback still work unchanged; prod
 docker-compose.prod.yml is untouched (all new services live in separate overlay files).