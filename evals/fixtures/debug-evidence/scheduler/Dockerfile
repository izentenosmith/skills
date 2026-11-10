FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir redis==5.0.8
COPY scheduler.py .
USER 10001:10001
CMD ["python", "scheduler.py"]
