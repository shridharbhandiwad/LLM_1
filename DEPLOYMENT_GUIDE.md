# OFFLINE PRIVATE LLM-RAG SYSTEM
## Deployment Guide for Air-Gapped Environments

**Classification:** UNCLASSIFIED (Deployment Guide)  
**Version:** 1.0  
**Date:** 2025-12-22

---

## TABLE OF CONTENTS

1. [Prerequisites](#prerequisites)
2. [Phase 1: Internet-Connected Preparation](#phase-1-internet-connected-preparation)
3. [Phase 2: Transfer to Air-Gapped System](#phase-2-transfer-to-air-gapped-system)
4. [Phase 3: Installation](#phase-3-installation)
5. [Phase 4: Configuration](#phase-4-configuration)
6. [Phase 5: Security Hardening](#phase-5-security-hardening)
7. [Phase 6: Testing](#phase-6-testing)
8. [Phase 7: Operations](#phase-7-operations)
9. [Troubleshooting](#troubleshooting)

---

## PREREQUISITES

### Hardware Requirements

**Minimum:**
- CPU: 8 cores (x86_64)
- RAM: 16GB
- Storage: 100GB SSD
- Network: None (air-gapped)

**Recommended:**
- CPU: 16 cores
- RAM: 32GB
- Storage: 500GB NVMe SSD
- GPU: NVIDIA GPU with 8GB VRAM (optional)

### Software Requirements

- Operating System: Ubuntu 22.04 LTS or RHEL 8/9
- Python 3.11+
- Root/sudo access for initial setup

---

## PHASE 1: INTERNET-CONNECTED PREPARATION

### Step 1: Clone Repository

```bash
git clone <repository-url>
cd offline-rag-system
```

### Step 2: Download Python Dependencies

```bash
# Create wheels directory
mkdir -p wheels

# Download all dependencies
pip download -r requirements.txt -d wheels/

# Verify downloads
ls -lh wheels/
```

### Step 3: Download Models

#### Embedding Model

```bash
python scripts/download_models.py
```

This will download:
- `sentence-transformers/all-MiniLM-L6-v2` (~90MB)

#### LLM Model

Download manually from HuggingFace:

**Option 1: LLaMA-3.2-3B-Instruct (Recommended)**
```bash
# Install huggingface-cli
pip install huggingface-hub

# Download quantized model
huggingface-cli download bartowski/Llama-3.2-3B-Instruct-GGUF \
  --local-dir models/llm \
  --include '*Q4_K_M.gguf'

# Rename to expected name
mv models/llm/*Q4_K_M.gguf models/llm/llama-3.2-3b-instruct.gguf
```

**Option 2: Mistral-7B-Instruct (Better quality, more resources)**
```bash
huggingface-cli download TheBloke/Mistral-7B-Instruct-v0.3-GGUF \
  --local-dir models/llm \
  --include '*Q4_K_M.gguf'
```

### Step 4: Create Transfer Package

```bash
# Package everything
tar -czf rag-system-offline.tar.gz \
  src/ \
  tests/ \
  scripts/ \
  data/ \
  models/ \
  wheels/ \
  main.py \
  requirements.txt \
  .env.example \
  Dockerfile \
  docker-compose.yml \
  ARCHITECTURE.md \
  DEPLOYMENT_GUIDE.md \
  README.md

# Verify package
ls -lh rag-system-offline.tar.gz
```

### Step 5: Calculate Checksum

```bash
sha256sum rag-system-offline.tar.gz > rag-system-offline.tar.gz.sha256
cat rag-system-offline.tar.gz.sha256
```

---

## PHASE 2: TRANSFER TO AIR-GAPPED SYSTEM

### Transfer Methods

1. **USB Drive** (Recommended)
   - Copy `rag-system-offline.tar.gz` and `.sha256` file
   - Use encrypted USB if handling classified systems

2. **Secure File Transfer**
   - Via approved secure transfer mechanism
   - Verify integrity after transfer

3. **Physical Media**
   - DVD/CD-ROM for highly classified systems
   - Follow organizational procedures

### Verify Transfer Integrity

```bash
# On air-gapped system
sha256sum -c rag-system-offline.tar.gz.sha256
```

---

## PHASE 3: INSTALLATION

### Step 1: Extract Package

```bash
# Create installation directory
sudo mkdir -p /opt/rag-system
cd /opt/rag-system

# Extract
sudo tar -xzf /path/to/rag-system-offline.tar.gz

# Set ownership
sudo chown -R $USER:$USER /opt/rag-system
```

### Step 2: Install System Dependencies

#### Ubuntu/Debian

```bash
# Install from offline repository or cached packages
sudo apt-get install -y \
  python3.11 \
  python3.11-dev \
  python3-pip \
  build-essential \
  cmake \
  sqlite3
```

#### RHEL/CentOS

```bash
sudo yum install -y \
  python3.11 \
  python3.11-devel \
  gcc \
  gcc-c++ \
  cmake \
  sqlite
```

### Step 3: Install Python Dependencies

```bash
# Install from local wheels (no internet needed)
pip3 install --no-index --find-links=wheels/ -r requirements.txt

# Verify installation
pip3 list
```

### Step 4: Create Configuration

```bash
# Copy environment template
cp .env.example .env

# Edit configuration
nano .env
```

Key settings to configure:
```env
EMBEDDING_MODEL_PATH=/opt/rag-system/models/embeddings/all-MiniLM-L6-v2
LLM_MODEL_PATH=/opt/rag-system/models/llm/llama-3.2-3b-instruct.gguf
VECTOR_DB_PATH=/var/lib/rag-system/vectors/
DISABLE_NETWORK=true
```

### Step 5: Create Directories

```bash
# Create data directories
sudo mkdir -p /var/lib/rag-system/{vectors,keys}
sudo mkdir -p /var/log/rag-system

# Set permissions
sudo chown -R $USER:$USER /var/lib/rag-system
sudo chown -R $USER:$USER /var/log/rag-system
sudo chmod -R 700 /var/lib/rag-system
sudo chmod -R 700 /var/log/rag-system
```

---

## PHASE 4: CONFIGURATION

### Security Configuration

1. **Generate Encryption Keys**

```bash
python3 -c "import secrets; print(secrets.token_hex(32))" > /var/lib/rag-system/keys/master.key
chmod 600 /var/lib/rag-system/keys/master.key
```

2. **Configure User Access**

Edit `src/config.py` or environment variables to set:
- Classification levels
- User clearances
- Access control policies

### Network Isolation

```bash
# Configure firewall (requires root)
sudo bash scripts/setup_firewall.sh
```

This will:
- Block all outbound network traffic
- Allow only localhost communication
- Save firewall rules persistently

### Verify Configuration

```bash
# Test configuration
python3 -c "from src.config import config; config.create_directories(); print('✓ Configuration valid')"
```

---

## PHASE 5: SECURITY HARDENING

### 1. Network Verification

```bash
python3 -c "
from src.security import NetworkIsolationVerifier
results = NetworkIsolationVerifier.verify_all()
for check in results['checks']:
    print(f\"{'✓' if check['passed'] else '✗'} {check['name']}: {check['details']}\")
"
```

All checks should pass (✓).

### 2. File System Security

```bash
# Restrict permissions
sudo chmod 700 /opt/rag-system
sudo chmod 700 /var/lib/rag-system
sudo chmod 700 /var/log/rag-system

# Set immutable flag on critical files (optional)
sudo chattr +i /opt/rag-system/src/config.py
```

### 3. Audit Logging

```bash
# Ensure audit log is enabled
grep "ENABLE_AUDIT_LOG=true" .env

# Set up log rotation
sudo bash -c 'cat > /etc/logrotate.d/rag-system << EOF
/var/log/rag-system/*.log {
    daily
    rotate 90
    compress
    delaycompress
    missingok
    notifempty
    create 0600 $USER $USER
}
EOF'
```

### 4. SELinux/AppArmor (Optional)

For RHEL/CentOS with SELinux:
```bash
# Set appropriate SELinux context
sudo semanage fcontext -a -t usr_t "/opt/rag-system(/.*)?"
sudo restorecon -R /opt/rag-system
```

---

## PHASE 6: TESTING

### 1. Basic Functionality Test

```bash
# Run main application (without LLM)
python3 main.py
```

Expected output:
```
==================================================
SECURITY VERIFICATION
==================================================
✓ DNS Resolution: DNS resolution disabled
✓ Internet Connectivity: No internet connectivity detected
✓ Localhost Binding: Localhost binding available
...
```

### 2. Document Ingestion Test

```bash
python3 << 'EOF'
import sys
sys.path.insert(0, 'src')

from main import OfflineRAGSystem
from pathlib import Path

system = OfflineRAGSystem()
system.initialize(skip_llm=True)

# Ingest sample documents
doc_path = Path("data/documents")
system.ingest_documents(doc_path, user_id="admin")

print("✓ Ingestion test passed")
EOF
```

### 3. Run Test Suite

```bash
# Install pytest if not already installed
pip3 install pytest --no-index --find-links=wheels/

# Run tests
pytest tests/ -v
```

### 4. Security Tests

```bash
# Run security validation
pytest tests/test_security.py -v

# Run hallucination detection tests
pytest tests/test_validation.py -v
```

---

## PHASE 7: OPERATIONS

### Starting the System

#### Interactive Mode

```bash
cd /opt/rag-system
python3 main.py
```

#### Docker Mode

```bash
# Build image (on internet-connected machine)
docker build -t offline-rag-system .

# Transfer image to air-gapped system
docker save offline-rag-system > rag-system-image.tar
# ... transfer ...
docker load < rag-system-image.tar

# Run with docker-compose
docker-compose up -d
```

### Ingesting Documents

```bash
python3 << 'EOF'
from main import OfflineRAGSystem
from pathlib import Path

system = OfflineRAGSystem()
system.initialize()

# Ingest documents
system.ingest_documents(
    Path("/path/to/classified/documents"),
    user_id="admin"
)
EOF
```

### Querying the System

```python
from main import OfflineRAGSystem

system = OfflineRAGSystem()
system.initialize()

# Query
result = system.query(
    "What is the radar range?",
    user_id="analyst_ts"
)

print(result)
```

### Monitoring

```bash
# View system logs
tail -f /var/log/rag-system/system.log

# View audit logs (requires decryption key)
python3 -c "
from src.security import AuditLogger
from pathlib import Path

logger = AuditLogger(Path('/var/log/rag-system/audit.log'))
events = logger.read_events(limit=10)
for event in events:
    print(f'{event.timestamp} - {event.event_type.value} - {event.user_id}')
"
```

---

## TROUBLESHOOTING

### Issue: Models Not Found

**Symptoms:**
```
FileNotFoundError: Model not found at /opt/models/...
```

**Solution:**
```bash
# Verify model paths
ls -l models/embeddings/
ls -l models/llm/

# Update .env file with correct paths
nano .env
```

### Issue: Network Access Detected

**Symptoms:**
```
✗ Internet Connectivity: Connection successful
```

**Solution:**
```bash
# Re-run firewall setup
sudo bash scripts/setup_firewall.sh

# Verify iptables rules
sudo iptables -L -n
```

### Issue: Permission Denied

**Symptoms:**
```
PermissionError: [Errno 13] Permission denied
```

**Solution:**
```bash
# Fix directory permissions
sudo chown -R $USER:$USER /var/lib/rag-system
sudo chmod -R 700 /var/lib/rag-system
```

### Issue: Out of Memory

**Symptoms:**
```
RuntimeError: Failed to allocate memory
```

**Solution:**
```bash
# Reduce LLM context length in .env
LLM_CONTEXT_LENGTH=2048  # Reduce from 4096

# Or use smaller model
# Switch from 7B to 3B model
```

### Issue: Slow Performance

**Solutions:**
1. **Increase CPU threads:**
   ```env
   LLM_THREADS=16  # Increase from 8
   ```

2. **Use GPU acceleration:**
   ```env
   # Install CUDA-enabled llama-cpp-python
   # Set GPU layers
   N_GPU_LAYERS=32
   ```

3. **Reduce embedding batch size:**
   - Modify `batch_size` in embedding generation

---

## MAINTENANCE

### Regular Tasks

1. **Daily:**
   - Check system logs for errors
   - Verify disk space
   - Review audit logs

2. **Weekly:**
   - Backup vector database
   - Backup encryption keys (secure location)
   - Review access logs

3. **Monthly:**
   - Full system audit
   - Security scan
   - Performance review

### Backup Procedures

```bash
# Backup vector database
tar -czf backup-vectors-$(date +%Y%m%d).tar.gz /var/lib/rag-system/vectors/

# Backup metadata database
cp /var/lib/rag-system/metadata.db backup-metadata-$(date +%Y%m%d).db

# Backup encryption keys (CRITICAL)
# Store in secure location, separate from data
cp /var/lib/rag-system/keys/master.key backup-key-$(date +%Y%m%d).key
```

### Updates

For security updates or bug fixes:
1. Prepare update package on internet-connected machine
2. Transfer to air-gapped system
3. Test in staging environment
4. Apply to production
5. Verify functionality

---

## SECURITY CHECKLISTS

### Pre-Deployment Checklist

- [ ] All models downloaded and verified
- [ ] Network isolation configured
- [ ] Firewall rules applied
- [ ] Encryption keys generated
- [ ] File permissions set correctly
- [ ] Audit logging enabled
- [ ] User access configured
- [ ] Test suite passed
- [ ] Security scan completed
- [ ] Documentation reviewed

### Operational Checklist

- [ ] Daily log review
- [ ] Weekly backup verification
- [ ] Monthly security audit
- [ ] Quarterly penetration test
- [ ] Annual certification review

---

## SUPPORT

### Documentation

- Architecture: `ARCHITECTURE.md`
- API Reference: `docs/API.md` (if created)
- Security Guide: Section 3 of `ARCHITECTURE.md`

### Logs

- System logs: `/var/log/rag-system/system.log`
- Audit logs: `/var/log/rag-system/audit.log`
- Error logs: Check system log for ERROR level messages

---

**END OF DEPLOYMENT GUIDE**
