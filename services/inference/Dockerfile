FROM python:3.11-slim as base

ENV PYTHONUNBUFFERED=1 \
    POETRY_VERSION=1.8.3

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

COPY app.py app.py

EXPOSE 8000

ENV MODEL_PATH=/models/yolov5s.onnx

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
