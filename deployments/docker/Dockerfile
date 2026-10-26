FROM python:3.12-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

COPY . /app

RUN pip install --no-cache-dir uv && \
    uv sync --frozen --no-dev && \
    rm -rf /root/.cache

EXPOSE 8000

CMD ["uv", "run", "python", "-m", "src.main"]
