FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends curl wget gnupg && rm -rf /var/lib/apt/lists/*

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

RUN playwright install --with-deps chromium

COPY backend/app/ ./app/
COPY backend/tasks/ ./tasks/
COPY backend/worker_health.py ./worker_health.py
COPY backend/docker-entrypoint.sh /usr/local/bin/docker-entrypoint.sh
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

EXPOSE 8000

CMD ["/usr/local/bin/docker-entrypoint.sh"]
