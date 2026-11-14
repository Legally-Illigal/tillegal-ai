FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends antiword && \
    rm -rf /var/lib/apt/lists/* && \
    pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    rm -rf /root/.cache

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "src.main"]
