import os, psycopg

DSN = os.environ["DATABASE_URL"]

def create_job( job_id: str, s3_key: str) -> None:
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO jobs (id, s3_key, status, progress)" \
            "VALUES (%s, %s,'queued', 0)"
            , (job_id, s3_key)
        )

def get_job(job_id: str) -> dict | None:
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute("SELECT status, progress, transcript " \
                    "FROM jobs WHERE id=%s"
                    , (job_id,)
                    )
        row = cur.fetchone()
        if row is None:
            return None
        else:
            return {"status": row[0]
                    , "progress": row[1]
                    , "transcript": row[2]
                    } 