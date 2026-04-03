FROM python:3.11-slim

WORKDIR /app

# OS-level deps for XGBoost / numpy (libgomp for OpenMP).
RUN apt-get update && \
    apt-get install -y --no-install-recommends libgomp1 && \
    rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY config/ config/

ENV PYTHONUNBUFFERED=1
EXPOSE 8000

CMD ["bash", "-c", "ray start --head --dashboard-host=0.0.0.0 --disable-usage-stats && python -m app.main"]
