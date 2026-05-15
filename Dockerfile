# Agent Memory Docker Image

FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy dependency files
COPY pyproject.toml .env.example* ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy application
COPY surql/ surql/
COPY agent*.py ./
COPY load.py ./
COPY README.md ./

# Default command
CMD ["uv", "run", "agent.py"]