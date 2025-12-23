# OFFLINE PRIVATE LLM-RAG SYSTEM
## Defense-Grade Air-Gapped AI for Confidential Documents

---

## OVERVIEW

A complete **offline, air-gapped LLM-RAG (Retrieval Augmented Generation) system** designed for defense and intelligence applications.

### Key Features

- Zero network connectivity - Complete air-gap isolation
- Zero data leakage - No external API calls
- Multi-level security - Classification-aware document handling
- Full auditability - Encrypted audit trails
- Context-only responses - Hallucination prevention
- Source attribution - Full document traceability

### Use Cases

- Defense mission planning and intelligence analysis
- Radar and sensor data analysis
- Classified document Q&A
- Standard Operating Procedure (SOP) retrieval
- Technical manual querying

---

## QUICK START

### Windows Users

See **[WINDOWS_SETUP.md](WINDOWS_SETUP.md)** for detailed Windows installation instructions.

Quick start for Windows:
```bash
pip install -r requirements.txt
python scripts/download_models.py
python main.py
```

### Linux/Mac Users

#### On Internet-Connected Machine:

```bash
# Download dependencies and models
pip download -r requirements.txt -d wheels/
python scripts/download_models.py

# Package for transfer
tar -czf rag-system-offline.tar.gz .
```

#### On Air-Gapped Machine:

```bash
# Install and configure
tar -xzf rag-system-offline.tar.gz
pip install --no-index --find-links=wheels/ -r requirements.txt
cp .env.example .env

# Setup security
sudo bash scripts/setup_firewall.sh

# Run system
python main.py
```

---

## USAGE

```python
from main import OfflineRAGSystem
from pathlib import Path

system = OfflineRAGSystem()
system.initialize()

# Ingest documents
system.ingest_documents(Path("/path/to/documents"), user_id="admin")

# Query system
response = system.query("What is the radar's maximum range?", user_id="analyst_ts")
print(response)
```

---

## DOCUMENTATION

- **ARCHITECTURE.md** - System architecture and design
- **DEPLOYMENT_GUIDE.md** - Installation and deployment
- **SECURITY_CHECKLIST.md** - Security validation

---

## SECURITY

- Network isolation via firewall rules
- AES-256 encryption at rest
- Role-based access control (RBAC)
- Encrypted audit logging
- Classification enforcement

---

## TESTING

```bash
# Run all tests
pytest tests/ -v

# Security tests
pytest tests/test_security.py -v

# Verify network isolation
python -c "from src.security import NetworkIsolationVerifier; NetworkIsolationVerifier.verify_all()"
```

---

**Version:** 1.0  
**Status:** Production-Ready  
**Classification:** UNCLASSIFIED (Documentation)
