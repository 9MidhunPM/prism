FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/prism-api
RUN chmod 755 /usr/local/bin/prism-api && mkdir -p /app/data/uploads/processed && useradd --system --uid 10001 prism && chown -R prism:prism /app

ENV PYTHONUNBUFFERED=1 \
    UPLOAD_ROOT=/app/data/uploads
USER prism
EXPOSE 8080
VOLUME ["/app/data/uploads"]
ENTRYPOINT ["/usr/local/bin/prism-api"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]
