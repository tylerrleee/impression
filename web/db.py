import os, psycopg
from pgvector.psycopg import register_vector

DSN = os.environ["DATABASE_URL"]

def get_s3_key(job_id):
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute("SELECT s3_key FROM jobs WHERE id=%s", 
                    (job_id,))
        row = cur.fetchone()
        return row[0] if row else None
    
def search_chunks(vec, k = 5):
    with psycopg.connect(DSN) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT c.job_id, c.start_sec, c.end_sec, c.text, j.title "
                "FROM chunks c JOIN jobs j ON j.id = c.job_id "
                "ORDER BY c.embedding <=> %s LIMIT %s",
                (vec, k))
            return cur.fetchall()
        
def create_job( job_id: str, s3_key: str, title: str | None = None) -> None:
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(
            "INSERT INTO jobs (id, s3_key, status, progress, title)" \
            "VALUES (%s, %s,'queued', 0, %s)"
            , (job_id, s3_key, title)
        )

def get_chunks(job_id: str):
    with psycopg.connect(DSN) as c, c.cursor() as cur:
        cur.execute(
            "SELECT start_sec, end_sec, text FROM chunks "
            "WHERE job_id = %s ORDER BY start_sec",
            (job_id,))
        return cur.fetchall()

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