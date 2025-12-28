FROM ubuntu:24.04

LABEL maintainer="Vakintosh <hello@vakintosh.com>"
LABEL description="Rockbox Database Manager - CLI tool for managing Rockbox database files"
LABEL version="0.4.0"

# Prevent interactive prompts during package installation
ENV DEBIAN_FRONTEND=noninteractive

# Set working directory
WORKDIR /app

# Install system dependencies
# - Python 3.11+
# - curl for downloading uv
# - Audio file format libraries
RUN apt-get update && apt-get install -y \
    python3 \
    python3-venv \
    curl \
    ca-certificates \
    # Audio libraries (for mutagen)
    libflac12 \
    libvorbis0a \
    libopus0 \
    && rm -rf /var/lib/apt/lists/*

# Install uv (fast Python package installer)
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:$PATH"

# Copy project files
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/

# Create and activate virtual environment
RUN python3 -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Install the package with CLI dependencies only using uv
# uv pip install is much faster than pip
RUN uv pip install --no-cache -e .

# Create directories for music and database
RUN mkdir -p /music /output

# Set Python to unbuffered mode for better logging
ENV PYTHONUNBUFFERED=1

# Default command shows help
CMD ["rdbm", "--help"]

# Volume mounts (can be overridden at runtime)
VOLUME ["/music", "/output"]
