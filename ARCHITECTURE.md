# OFFLINE PRIVATE LLM-RAG SYSTEM
## Defense-Grade Architecture for Air-Gapped Environments

**Classification Level:** UNCLASSIFIED (System Design)  
**Date:** 2025-12-22  
**Version:** 1.0

---

## EXECUTIVE SUMMARY

This document describes an end-to-end offline LLM-RAG (Large Language Model - Retrieval Augmented Generation) system designed for defense and intelligence applications requiring:
- **Zero network connectivity**
- **Zero data exfiltration risk**
- **Complete auditability**
- **Classification-level data handling**

---

## 1. SYSTEM ARCHITECTURE

```
┌─────────────────────────────────────────────────────────────────┐
│                      AIR-GAPPED PERIMETER                       │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    INGESTION LAYER                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐                │  │
│  │  │   PDFs   │  │   TXT    │  │  RADAR   │                │  │
│  │  │  Loader  │  │  Loader  │  │  Logs    │                │  │
│  │  └────┬─────┘  └────┬─────┘  └────┬─────┘                │  │
│  │       └────────────┬──────────────┘                       │  │
│  │                    │                                       │  │
│  │              ┌─────▼─────┐                                │  │
│  │              │  Chunker  │  (512 tokens, 50 overlap)      │  │
│  │              │ & Metadata│                                │  │
│  │              └─────┬─────┘                                │  │
│  └────────────────────┼───────────────────────────────────────┘  │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────────┐  │
│  │                  EMBEDDING LAYER                           │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  all-MiniLM-L6-v2 (Offline)                         │  │  │
│  │  │  - 384 dimensions                                   │  │  │
│  │  │  - 22M parameters                                   │  │  │
│  │  │  - No external API                                  │  │  │
│  │  └───────────────────┬─────────────────────────────────┘  │  │
│  └────────────────────┼─────────────────────────────────────┘  │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────────┐  │
│  │                VECTOR DATABASE LAYER                       │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  FAISS (IndexFlatIP)                                │  │  │
│  │  │  - AES-256 encryption at rest                       │  │  │
│  │  │  - Metadata filtering                               │  │  │
│  │  │  - Classification-aware                             │  │  │
│  │  └───────────────────┬─────────────────────────────────┘  │  │
│  └────────────────────┼─────────────────────────────────────┘  │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────────┐  │
│  │                  RETRIEVAL LAYER                           │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐    │  │
│  │  │  Semantic    │→ │  Re-ranking  │→ │  Metadata    │    │  │
│  │  │  Search      │  │  (Optional)  │  │  Filtering   │    │  │
│  │  │  (Top-K=5)   │  │              │  │              │    │  │
│  │  └──────────────┘  └──────────────┘  └──────┬───────┘    │  │
│  └───────────────────────────────────────────────┼───────────┘  │
│                                                   │              │
│  ┌────────────────────────────────────────────────▼───────────┐  │
│  │                    LLM INFERENCE LAYER                     │  │
│  │  ┌─────────────────────────────────────────────────────┐  │  │
│  │  │  LLaMA-3.2-3B-Instruct (Offline)                    │  │  │
│  │  │  - Quantized to 4-bit (GGUF)                        │  │  │
│  │  │  - llama.cpp backend                                │  │  │
│  │  │  - Strict context-only prompting                    │  │  │
│  │  └───────────────────┬─────────────────────────────────┘  │  │
│  └────────────────────┼─────────────────────────────────────┘  │
│                       │                                          │
│  ┌────────────────────▼───────────────────────────────────────┐  │
│  │                 ORCHESTRATION LAYER                        │  │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐  │  │
│  │  │  Query   │  │ Context  │  │ Prompt   │  │ Response │  │  │
│  │  │ Validator│→ │ Assembly │→ │ Template │→ │Generator │  │  │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘  │  │
│  └────────────────────────────────────────────────────────────┘  │
│                                                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  SECURITY & AUDIT LAYER                   │  │
│  │  - Role-based access control (RBAC)                      │  │
│  │  - Query logging (encrypted)                             │  │
│  │  - Classification enforcement                            │  │
│  │  - Network isolation verification                        │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

---

## 2. COMPONENT SPECIFICATIONS

### 2.1 DATA INGESTION

**Purpose:** Load and prepare documents for embedding

**Supported Formats:**
- PDF (PyPDF2, pdfplumber)
- Text files (.txt, .log, .md)
- Radar logs (custom parsers)
- Structured data (CSV, JSON)

**Chunking Strategy:**
- **Method:** Recursive character splitting
- **Chunk size:** 512 tokens (~2048 characters)
- **Overlap:** 50 tokens (~200 characters)
- **Rationale:** Balance between context preservation and retrieval precision

**Metadata Schema:**
```json
{
  "doc_id": "UUID",
  "source_file": "path/to/document.pdf",
  "classification": "UNCLASSIFIED|CONFIDENTIAL|SECRET|TOP_SECRET",
  "ingest_date": "ISO8601 timestamp",
  "page_number": "integer",
  "chunk_index": "integer",
  "document_type": "pdf|text|radar_log|mission_report",
  "originator": "unit/system identifier",
  "checksum": "SHA256 hash"
}
```

### 2.2 EMBEDDING GENERATION

**Model:** `all-MiniLM-L6-v2` (sentence-transformers)

**Justification:**
- ✅ Small (22M parameters, ~90MB)
- ✅ Fast inference (CPU-friendly)
- ✅ Good semantic understanding
- ✅ Fully offline via Hugging Face Hub cache
- ✅ 384-dimensional embeddings (efficient storage)
- ✅ Apache 2.0 license (permissive)

**Alternative:** `all-mpnet-base-v2` (better quality, 110M params)

**Offline Deployment:**
1. Pre-download model weights
2. Store in air-gapped model registry
3. Load from local path only
4. Disable all telemetry

### 2.3 VECTOR DATABASE

**Technology:** FAISS (Facebook AI Similarity Search)

**Index Type:** `IndexFlatIP` (Inner Product)
- Exact search (no approximation for security)
- Full reproducibility
- No external dependencies

**Security Features:**
- AES-256-GCM encryption for index files
- Key management via hardware security module (HSM)
- Access control via file permissions
- Tamper detection (checksums)

**Storage Layout:**
```
/var/lib/rag-system/
├── vectors/
│   ├── index.faiss.enc          # Encrypted FAISS index
│   ├── metadata.db.enc          # Encrypted SQLite metadata
│   └── checksums.sha256         # Integrity verification
└── keys/
    └── master.key               # Encrypted with HSM
```

### 2.4 RETRIEVAL PIPELINE

**Process:**
1. **Query Embedding:** Convert user query to 384-dim vector
2. **Semantic Search:** FAISS similarity search (top-K=5)
3. **Metadata Filtering:** 
   - Classification level check
   - User clearance verification
   - Date range filtering
4. **Re-ranking (Optional):** Cross-encoder for precision
5. **Context Assembly:** Concatenate retrieved chunks

**Similarity Metric:** Cosine similarity (via inner product on normalized vectors)

### 2.5 LLM INFERENCE

**Model:** LLaMA 3.2 3B Instruct (Meta)

**Justification:**
- ✅ State-of-art quality for size
- ✅ Instruction-tuned
- ✅ 3B parameters (CPU-runnable)
- ✅ Quantizable to 4-bit (GGUF format)
- ✅ Open weights

**Inference Engine:** llama.cpp
- Pure C++ implementation
- No Python dependencies for inference
- CPU/GPU support
- Memory-efficient

**Quantization:** Q4_K_M (4-bit, medium quality)
- ~2GB model size
- 16GB RAM sufficient
- Minimal quality loss

**Alternative Models:**
- Mistral-7B-Instruct-v0.3 (better quality, more resources)
- Qwen2.5-3B-Instruct (competitive with LLaMA)

### 2.6 RAG ORCHESTRATION

**Prompt Template:**
```
SYSTEM:
You are a secure AI assistant operating in an air-gapped defense system.

CRITICAL RULES:
1. Answer ONLY using information from the provided CONTEXT below
2. If the answer is not in the CONTEXT, respond: "Insufficient information in provided documents"
3. NEVER use external knowledge or training data
4. Always cite source documents using [Source: filename, page X]
5. If classification levels conflict, defer to highest classification

CONTEXT:
{retrieved_documents}

USER QUERY:
{user_question}

ASSISTANT:
```

**Safety Mechanisms:**
- Context-only constraint
- Hallucination detection
- Source attribution requirement
- Classification enforcement

---

## 3. SECURITY CONTROLS

### 3.1 Network Isolation

**Requirements:**
- ✅ No network interfaces enabled (except localhost)
- ✅ Firewall rules: DROP all outbound
- ✅ DNS disabled
- ✅ NTP disabled (use local time)
- ✅ Package updates via offline repository only

**Verification:**
```bash
# Block all external network
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -j DROP
```

### 3.2 Access Control

**RBAC Model:**
```
Roles:
- ADMIN: Full system access
- ANALYST_TS: Top Secret clearance
- ANALYST_S: Secret clearance
- ANALYST_C: Confidential clearance
- OPERATOR: Query only, UNCLASSIFIED

Permissions:
- ingest_documents
- query_system
- view_logs
- manage_users
```

### 3.3 Audit Logging

**Logged Events:**
- All queries (encrypted)
- Document ingestion
- Access attempts
- Configuration changes
- Retrieval results

**Log Format:**
```json
{
  "timestamp": "2025-12-22T10:30:00Z",
  "event_type": "query",
  "user_id": "analyst_001",
  "clearance": "SECRET",
  "query_hash": "SHA256",
  "retrieved_docs": ["doc_id1", "doc_id2"],
  "classification_max": "SECRET"
}
```

### 3.4 Data Protection

- **At Rest:** AES-256-GCM encryption
- **In Memory:** Secure memory wiping after use
- **In Transit:** N/A (offline system)

---

## 4. HARDWARE REQUIREMENTS

### Minimum Configuration:
- **CPU:** 8 cores (x86_64)
- **RAM:** 16GB
- **Storage:** 100GB SSD
- **GPU:** None required (CPU inference)

### Recommended Configuration:
- **CPU:** 16 cores
- **RAM:** 32GB
- **Storage:** 500GB NVMe SSD
- **GPU:** NVIDIA GPU with 8GB VRAM (optional, 10x speedup)

### Storage Breakdown:
- Model weights: 5GB
- Vector database: 10GB per 100K documents
- Logs: 1GB per year
- OS and dependencies: 20GB

---

## 5. DEPLOYMENT PLAN

### 5.1 Offline Installation

**Prerequisites:**
1. Air-gapped server (RHEL 8/9 or Ubuntu 22.04 LTS)
2. Offline package repository
3. Pre-downloaded model weights
4. Installation media (USB drive)

**Installation Steps:**
```bash
# 1. Install system dependencies (offline repo)
yum install python3.11 sqlite gcc g++ cmake

# 2. Install Python packages (from local wheel archive)
pip3 install --no-index --find-links=/mnt/usb/wheels/ \
  torch sentence-transformers faiss-cpu pdfplumber flask

# 3. Deploy application
tar -xzf rag-system.tar.gz -C /opt/
cd /opt/rag-system
python3 setup.py install

# 4. Configure security
./scripts/setup-firewall.sh
./scripts/setup-encryption.sh

# 5. Start services
systemctl enable rag-system
systemctl start rag-system
```

### 5.2 Docker Deployment (Alternative)

```dockerfile
FROM ubuntu:22.04

# Install dependencies (from local cache)
COPY packages/ /tmp/packages/
RUN dpkg -i /tmp/packages/*.deb

# Copy models
COPY models/ /opt/models/

# Copy application
COPY src/ /opt/rag-system/

# Network isolation
RUN echo "net.ipv4.ip_forward = 0" >> /etc/sysctl.conf

CMD ["/opt/rag-system/run.sh"]
```

---

## 6. TESTING & VALIDATION

### 6.1 Data Leakage Tests

**Test Cases:**
1. **Network Monitoring:** Verify zero outbound traffic
2. **DNS Queries:** Confirm no DNS lookups
3. **Model Loading:** Ensure local paths only
4. **API Calls:** No HTTP/HTTPS requests

**Tools:**
```bash
# Monitor network activity
tcpdump -i any -w traffic.pcap
# Should show ZERO packets

# Check for DNS queries
journalctl -u systemd-resolved | grep -i query
# Should be empty

# Strace for network syscalls
strace -e trace=network python3 main.py
# Should show no connect() calls
```

### 6.2 Hallucination Detection

**Test Cases:**
1. Query about information NOT in documents
2. Query requiring external knowledge
3. Query with contradictory context

**Expected Behavior:**
- Response: "Insufficient information in provided documents"
- No fabricated information
- Source citations for all claims

**Validation Script:**
```python
def test_hallucination():
    # Ingest known documents
    ingest_document("test_doc.pdf")
    
    # Query outside corpus
    response = query("What is the capital of France?")
    
    assert "Insufficient information" in response
    assert "Paris" not in response
```

### 6.3 RAG Correctness

**Metrics:**
- **Precision:** % of retrieved docs relevant
- **Recall:** % of relevant docs retrieved
- **Answer Accuracy:** Manual evaluation
- **Source Attribution:** % of claims with citations

### 6.4 Red Team Scenarios

1. **Prompt Injection:** Attempt to bypass system instructions
2. **Classification Escalation:** Try to access higher-classified docs
3. **Data Exfiltration:** Attempt to leak data
4. **DoS:** Overwhelm system with queries

---

## 7. SECURITY CHECKLIST

### Pre-Deployment:
- [ ] All dependencies installed offline
- [ ] Models downloaded and verified (checksums)
- [ ] Network interfaces disabled
- [ ] Firewall rules configured
- [ ] Encryption keys generated
- [ ] User accounts and roles created
- [ ] Audit logging enabled
- [ ] Security scan completed

### Post-Deployment:
- [ ] Network isolation verified (tcpdump)
- [ ] Access control tested
- [ ] Audit logs reviewed
- [ ] Performance baseline established
- [ ] Backup procedures tested
- [ ] Incident response plan documented

### Operational:
- [ ] Weekly log review
- [ ] Monthly security audit
- [ ] Quarterly penetration test
- [ ] Annual certification review

---

## 8. ASSUMPTIONS & LIMITATIONS

### Assumptions:
- Server is physically secured
- Users are vetted and cleared
- Documents are pre-classified correctly
- Network isolation is maintained

### Limitations:
- **Model Size:** 3B parameter model (quality vs. resource tradeoff)
- **Language:** English only (can add multilingual models)
- **Document Types:** Limited format support initially
- **Concurrent Users:** 5-10 simultaneous queries
- **Index Size:** Up to 1M documents (can scale with better hardware)

### Known Risks:
- **Prompt Injection:** Partially mitigated, requires ongoing monitoring
- **Insider Threat:** Relies on physical and personnel security
- **Model Bias:** Inherent in pre-trained models
- **Hallucination:** Minimized but not eliminated

---

## 9. MAINTENANCE & UPDATES

### Model Updates:
- New models must be vetted offline
- Regression testing required
- Change management process

### Software Updates:
- Security patches via offline repository
- Tested in staging environment first
- Rollback plan required

---

## 10. APPENDICES

### A. Glossary
- **RAG:** Retrieval Augmented Generation
- **FAISS:** Facebook AI Similarity Search
- **GGUF:** GPT-Generated Unified Format (quantization)
- **HSM:** Hardware Security Module

### B. References
- NIST SP 800-53 (Security Controls)
- ISO 27001 (Information Security)
- DoD Instruction 8510.01 (Cybersecurity)

### C. Contact
- System Architect: [REDACTED]
- Security Officer: [REDACTED]
- Project Lead: [REDACTED]

---

**END OF DOCUMENT**
