FROM python:3.13-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl build-essential \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml ./

RUN pip install uv && uv sync

COPY . .

CMD ["uv", "run", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001"]
