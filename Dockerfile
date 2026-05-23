FROM python:3.11-slim-bookworm

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libgl1 \
    libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

COPY api/requirements.azure.txt /app/api/requirements.azure.txt
RUN pip install --no-cache-dir -r /app/api/requirements.azure.txt

COPY backend /app/backend
COPY scripts/startup.sh /app/scripts/startup.sh
RUN chmod +x /app/scripts/startup.sh

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

EXPOSE 8000

CMD ["/app/scripts/startup.sh"]
