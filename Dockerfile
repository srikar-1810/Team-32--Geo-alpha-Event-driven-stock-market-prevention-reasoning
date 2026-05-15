FROM python:3.10-slim

# Install system dependencies, PostgreSQL 17, and Redis
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    redis-server \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Hugging Face runs as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:/usr/lib/postgresql/17/bin:$PATH

WORKDIR /app

# Copy requirements and install
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy the rest of the application
COPY --chown=user . .

# Set environment variables for the All-in-One setup
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MOCK_MODE=false
# CRITICAL: Use +asyncpg for SQLAlchemy asyncio
ENV DATABASE_URL=postgresql+asyncpg://localhost:5432/postgres
ENV REDIS_URL=redis://localhost:6379/0
ENV CHROMA_HOST=localhost
ENV CHROMA_PORT=8001

# Make the start script executable
RUN chmod +x scripts/start_hf.sh

# Expose Streamlit port
EXPOSE 7860

# Run the startup script
CMD ["./scripts/start_hf.sh"]
