FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir flask==3.0.3 redis==5.0.8 gunicorn==22.0.0
COPY app.py .
USER 10001:10001
CMD ["gunicorn", "-b", "0.0.0.0:8000", "app:app"]
