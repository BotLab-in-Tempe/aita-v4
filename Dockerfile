FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    docker-cli \
 && rm -rf /var/lib/apt/lists/*

# Copy project metadata + source
COPY pyproject.toml ./pyproject.toml
COPY README.md ./README.md
COPY langgraph.json ./langgraph.json
COPY src ./src

# Install project (and its deps) via pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir .

EXPOSE 8000

# FastAPI app at src/api/api.py with `app`
CMD ["uvicorn", "src.api.api:app", "--host", "0.0.0.0", "--port", "8000"]