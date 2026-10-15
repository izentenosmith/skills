FROM python:3.12-slim
WORKDIR /app
COPY app/ app/
COPY config/ config/
USER 10001
CMD ["python", "-m", "app.server"]
