import os, psycopg
from pgvector.psycopg import register_vector

DSN = os.environ["DATABASE_URL"]


def search_chunks(vec, k = 5):
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT job_id, start_sec, end_sec, text "
                "FROM chunks ORDER BY embedding <=> %s LIMIT %s",
                (vec, k))
            return cur.fetchall()
        
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