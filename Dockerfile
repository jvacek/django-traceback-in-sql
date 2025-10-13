# Simplified Dockerfile using UV's multi-Python installation feature
# UV can install and manage multiple Python versions in a single image

FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim

# Install system dependencies for all database drivers
RUN apt-get update && apt-get install -y --no-install-recommends \
    # PostgreSQL client libraries
    libpq-dev \
    # MySQL client libraries
    default-libmysqlclient-dev \
    pkg-config \
    # Build tools
    gcc \
    g++ \
    make \
    # Utilities
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

# Install multiple Python versions using UV
# This allows tox to test against all these versions
RUN uv python install 3.10 3.11 3.12 3.13

# Install tox using UV
RUN uv pip install --system --no-cache \
    tox>=4.0.0 \
    tox-gh-actions>=3.0.0

# Verify Python installations are available
RUN uv python list

# Default command runs tox
CMD ["tox"]
