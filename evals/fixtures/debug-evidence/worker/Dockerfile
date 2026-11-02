FROM python:3.12-slim
WORKDIR /app
RUN pip install --no-cache-dir redis==5.0.8 torch==2.4.1 torchvision==0.19.1 --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple
COPY worker.py .
USER 10001:10001
CMD ["python", "worker.py"]
