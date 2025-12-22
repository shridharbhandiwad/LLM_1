# Dockerfile for Offline Private LLM-RAG System
# Build this on an internet-connected machine, then transfer to air-gapped system

FROM ubuntu:22.04

# Prevent interactive prompts
ENV DEBIAN_FRONTEND=noninteractive

# Install system dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-dev \
    python3-pip \
    build-essential \
    cmake \
    git \
    sqlite3 \
    && rm -rf /var/lib/apt/lists/*

# Set Python 3.11 as default
RUN update-alternatives --install /usr/bin/python python /usr/bin/python3.11 1
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1

# Create application directory
WORKDIR /opt/rag-system

# Copy requirements
COPY requirements.txt .

# Install Python dependencies
# In production, use --no-index --find-links for offline installation
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy application code
COPY src/ ./src/
COPY main.py .
COPY .env.example .env

# Create data directories
RUN mkdir -p /var/lib/rag-system/vectors \
             /var/lib/rag-system/keys \
             /var/log/rag-system \
             /opt/models/embeddings \
             /opt/models/llm

# Copy models (must be added during build)
# COPY models/ /opt/models/

# Set environment variables for offline mode
ENV TRANSFORMERS_OFFLINE=1
ENV HF_DATASETS_OFFLINE=1
ENV TOKENIZERS_PARALLELISM=false

# Disable network (will be enforced by host firewall)
ENV DISABLE_NETWORK=true

# Security hardening
RUN chmod -R 700 /var/lib/rag-system
RUN chmod -R 700 /var/log/rag-system

# Create non-root user
RUN useradd -m -u 1000 raguser && \
    chown -R raguser:raguser /opt/rag-system /var/lib/rag-system /var/log/rag-system /opt/models

USER raguser

# Expose only localhost interface
EXPOSE 127.0.0.1:8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import sys; sys.path.insert(0, '/opt/rag-system'); from src.security import NetworkIsolationVerifier; sys.exit(0 if NetworkIsolationVerifier.verify_all()['all_passed'] else 1)"

# Run application
CMD ["python", "main.py"]
