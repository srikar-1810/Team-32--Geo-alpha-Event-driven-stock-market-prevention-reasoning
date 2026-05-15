FROM python:3.10-slim

# Install system dependencies, PostgreSQL, and Redis
RUN apt-get update && apt-get install -y \
    postgresql \
    postgresql-contrib \
    redis-server \
    build-essential \
    libpq-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements and install
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Set environment variables for the All-in-One setup
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV MOCK_MODE=false
ENV DATABASE_URL=postgresql://postgres:postgres@localhost:5432/geomarketgpt
ENV REDIS_URL=redis://localhost:6379/0
ENV CHROMA_HOST=localhost
ENV CHROMA_PORT=8000

# Make the start script executable
RUN chmod +x scripts/start_hf.sh

# Expose Streamlit port
EXPOSE 7860

# Run the startup script
CMD ["./scripts/start_hf.sh"]
