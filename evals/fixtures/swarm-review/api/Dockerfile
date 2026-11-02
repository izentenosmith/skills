FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY shoplane ./shoplane
USER 10001:10001
EXPOSE 8000
CMD ["gunicorn", "-b", "0.0.0.0:8000", "shoplane.app:app"]
