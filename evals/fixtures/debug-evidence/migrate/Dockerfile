FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir "psycopg[binary]==3.2.1"
COPY entrypoint.sh migrate.py ./
RUN chmod +x /app/entrypoint.sh
ENTRYPOINT ["/app/entrypoint.sh"]
