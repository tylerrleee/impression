FROM python:3.12-slim
WORKDIR /app
COPY web/requirements.txt web/requirements.txt
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu
RUN pip install --no-cache-dir -r web/requirements.txt
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
COPY web/ web/
COPY frontend/ frontend/
CMD ["uvicorn", "web.main:app", "--host", "0.0.0.0", "--port", "8000"]