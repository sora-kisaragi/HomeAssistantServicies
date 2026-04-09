# hadolint global ignore=DL3013
# NGC PyTorch — supports linux/arm64 (Grace-Hopper / DGX Spark) and linux/amd64
FROM nvcr.io/nvidia/pytorch:25.03-py3

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY server.py .

EXPOSE 9002

CMD ["uvicorn", "server:app", "--host", "0.0.0.0", "--port", "9002"]
