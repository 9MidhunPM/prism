FROM python:3.13-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY alembic.ini .
COPY alembic ./alembic
COPY app ./app
COPY docker-entrypoint.sh /usr/local/bin/prism-api
RUN useradd --create-home --uid 10001 prism \
    && mkdir -p /app/data \
    && chown -R prism:prism /app \
    && chmod 755 /usr/local/bin/prism-api

ENV PYTHONUNBUFFERED=1
EXPOSE 80
USER prism
ENTRYPOINT ["/usr/local/bin/prism-api"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
