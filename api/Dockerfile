FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_SYSTEM_PYTHON=1
ENV PATH="/usr/local/bin:$PATH"

# Install dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    postgresql-client \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy UV binary
COPY --from=ghcr.io/astral-sh/uv:0.5.4 /uv /uvx /bin/

# Install Python dependencies
COPY pyproject.toml ./
RUN uv pip compile pyproject.toml > requirements.txt && \
    uv pip install --system -r requirements.txt

# Copy application code
COPY . .

EXPOSE 8000
# Run the application with live reload
CMD ["uv","run","gunicorn", "app.main:app", "-k", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--reload"]