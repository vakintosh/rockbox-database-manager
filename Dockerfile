# Dockerfile.readonly - Optimized
# Logic: Build everything in stage 1, copy only the artifact (venv) to stage 2.

# --- STAGE 1: Builder ---
FROM python:3.11-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Install build dependencies (cleaned up immediately)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment
RUN uv venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH" \
    VIRTUAL_ENV="/opt/venv"

# Copy package metadata and source
COPY pyproject.toml README.md ./
COPY src/ ./src/

# KEY CHANGE: Install the package *fully* into the venv here.
# We do NOT use -e (editable). We want a static installation.
# This compiles the code, creates console scripts (rdbm), and puts them in /opt/venv.
RUN uv pip install --no-cache .

# --- STAGE 2: Runtime (Hardened) ---
FROM python:3.11-slim

# Security: Remove package manager
RUN apt-get purge -y --allow-remove-essential --auto-remove apt && \
    rm -rf /var/lib/apt/lists/* /var/cache/apt/*

# Create application user (non-root)
RUN useradd --create-home --shell /bin/bash --uid 1000 rdbm

# Create I/O directories with correct permissions
# These are the ONLY places the app can write.
RUN mkdir -p /input /output /tmp /home/rdbm/.cache && \
    chown -R rdbm:rdbm /input /output /tmp /home/rdbm

# KEY CHANGE: Copy the pre-built venv from builder
# We do not copy 'src', 'uv', or 'pyproject.toml'.
# The application is already installed inside /opt/venv.
COPY --from=builder /opt/venv /opt/venv

# Set path to use the venv
ENV PATH="/opt/venv/bin:$PATH"

# Switch to non-root user
USER rdbm

# Volume definitions (Documenting the contract)
VOLUME ["/input", "/output", "/tmp"]

# Working directory
WORKDIR /app

# Runtime Environment
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random

# Healthcheck
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=1 \
    CMD ["rdbm", "--version"]

# Metadata
LABEL security.readonly_root="true" \
      security.capabilities_drop="ALL" \
      security.run_as_user="1000"

ENTRYPOINT ["rdbm"]
CMD ["--help"]
