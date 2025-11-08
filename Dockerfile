FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# System deps for building Python packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
 && rm -rf /var/lib/apt/lists/*

# Copy project metadata first for better build caching
COPY pyproject.toml ./
COPY README.md ./README.md
COPY langgraph.json ./langgraph.json

# Install project (and its deps) via pyproject.toml
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir "uvicorn[standard]" && \
    pip install --no-cache-dir .

# Copy source code
COPY src ./src

EXPOSE 8000

# FastAPI app assumed at src/api/api.py with `app` variable
CMD ["uvicorn", "src.api.api:app", "--host", "0.0.0.0", "--port", "8000"]
