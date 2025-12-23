# Windows Unicode Encoding and Vector Store Decryption Fix

## Issues Resolved

This fix addresses two critical issues that occur on Windows systems:

### 1. Unicode Encoding Error (UnicodeEncodeError)

**Problem:**
```
UnicodeEncodeError: 'charmap' codec can't encode character '\u2713' in position 44: character maps to <undefined>
```

Windows console uses cp1252 encoding by default, which cannot encode Unicode characters like the checkmark symbol (✓, U+2713) used in log messages.

**Root Cause:**
- Log messages contained Unicode checkmark characters
- Windows console stdout/stderr defaults to cp1252 encoding
- Python's logging handlers tried to write UTF-8 characters to cp1252 stream

**Solution:**
1. **UTF-8 Console Configuration**: Added code to configure Windows console to use UTF-8 encoding
2. **File Handler Encoding**: Explicitly set UTF-8 encoding for file log handlers
3. **Backward Compatibility**: All checkmark characters already replaced with `[OK]` for ASCII safety

### 2. Vector Store Decryption Error (InvalidTag)

**Problem:**
```
cryptography.exceptions.InvalidTag
```

The system was generating a new encryption key on every initialization but trying to decrypt existing data encrypted with a different key.

**Root Cause:**
- `EncryptedVectorStore` generated a new random key when `encryption_key=None`
- No persistence mechanism for the encryption key
- On subsequent runs, new key couldn't decrypt old data
- Result: `InvalidTag` exception during decryption

**Solution:**
1. **Key Persistence**: Encryption key now saved to disk at `data/keys/master.key`
2. **Key Loading**: On initialization, checks for existing key file before generating new one
3. **Secure Storage**: Key file created with restricted permissions (0600 on Unix)
4. **Better Error Messages**: Clear error message when decryption fails with recovery instructions

## Changes Made

### File: `main.py`

#### UTF-8 Console Configuration (Lines 7-18)
```python
# Configure UTF-8 encoding for Windows console output
if sys.platform == "win32":
    # Set console output to UTF-8 on Windows
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass  # If this fails, we'll fall back to default encoding
```

#### File Handler UTF-8 Encoding (Line 38)
```python
logging.FileHandler(config.log_path / "system.log", encoding='utf-8')
```

#### Vector Store Initialization with Key Path (Lines 116-129)
```python
self.vector_store = EncryptedVectorStore(
    dimension=self.config.embedding_dimension,
    index_path=self.config.vector_db_path,
    encryption_key=None,  # Will load from disk or generate new
    key_path=self.config.encryption_key_path
)

# Try to load existing index
try:
    self.vector_store.load()
    logger.info(f"[OK] Loaded existing index: {self.vector_store.index.ntotal} vectors")
except FileNotFoundError:
    logger.info("No existing index found. Will create new index.")
except RuntimeError as e:
    logger.error(f"Failed to load vector store: {e}")
    raise
```

### File: `src/vectordb/vector_store.py`

#### Enhanced Constructor with Key Persistence (Lines 217-258)
```python
def __init__(self, dimension: int, index_path: Optional[Path] = None,
             encryption_key: Optional[bytes] = None,
             key_path: Optional[Path] = None):
    """
    Initialize encrypted vector store
    
    Args:
        dimension: Embedding dimension
        index_path: Path to save/load index
        encryption_key: 32-byte encryption key (AES-256)
        key_path: Path to save/load encryption key
    """
    super().__init__(dimension, index_path)
    
    self.key_path = key_path
    
    # Try to load existing key from disk
    if encryption_key is None and key_path is not None and key_path.exists():
        try:
            with open(key_path, 'rb') as f:
                encryption_key = f.read()
            logger.info(f"Loaded encryption key from {key_path}")
        except Exception as e:
            logger.error(f"Failed to load encryption key: {e}")
    
    if encryption_key is None:
        # Generate key if not provided and not on disk
        import secrets
        encryption_key = secrets.token_bytes(32)
        logger.warning("Generated new encryption key. Save this securely!")
        
        # Save the key to disk if path provided
        if key_path is not None:
            try:
                key_path.parent.mkdir(parents=True, exist_ok=True)
                with open(key_path, 'wb') as f:
                    f.write(encryption_key)
                # Set secure permissions on Unix-like systems
                import os
                if os.name != 'nt':
                    os.chmod(key_path, 0o600)
                logger.info(f"Saved encryption key to {key_path}")
            except Exception as e:
                logger.error(f"Failed to save encryption key: {e}")
    
    if len(encryption_key) != 32:
        raise ValueError("Encryption key must be 32 bytes for AES-256")
    
    self.encryption_key = encryption_key
```

#### Enhanced Load Method with Error Handling (Lines 294-343)
```python
def load(self, path: Optional[Path] = None):
    """Load encrypted index from disk"""
    load_path = path or self.index_path
    if load_path is None:
        raise ValueError("No load path specified")
    
    load_path = Path(load_path)
    
    # Load and decrypt FAISS index
    index_file = load_path / "index.faiss.enc"
    if not index_file.exists():
        raise FileNotFoundError(f"Index file not found: {index_file}")
    
    try:
        with open(index_file, 'rb') as f:
            encrypted_index = f.read()
        
        index_bytes = self._decrypt(encrypted_index)
        self.index = faiss.deserialize_index(index_bytes)
        
        # Load and decrypt metadata
        metadata_file = load_path / "metadata.pkl.enc"
        with open(metadata_file, 'rb') as f:
            encrypted_metadata = f.read()
        
        metadata_bytes = self._decrypt(encrypted_metadata)
        data = pickle.loads(metadata_bytes)
        
        self.metadata = data["metadata"]
        self.chunk_ids = data["chunk_ids"]
        self.dimension = data["dimension"]
        
        logger.info(f"Loaded encrypted index from {load_path}. Total vectors: {self.index.ntotal}")
        
    except Exception as e:
        from cryptography.exceptions import InvalidTag
        if isinstance(e, InvalidTag):
            logger.error(f"Decryption failed: encryption key mismatch or corrupted data")
            logger.error(f"To fix: Delete the encrypted index files in {load_path} or provide the correct key")
            logger.info(f"You can delete: {index_file} and {load_path / 'metadata.pkl.enc'}")
            raise RuntimeError("Vector store decryption failed. The encryption key doesn't match the stored data. "
                             "This may happen if the key file was regenerated. "
                             f"To start fresh, delete the encrypted files in {load_path}") from e
        else:
            raise
```

## Usage

### First Time Setup

1. Run the application - it will automatically generate and save an encryption key:
   ```bash
   python main.py
   ```

2. The encryption key is saved to `data/keys/master.key` (configured in `src/config.py`)

3. **IMPORTANT**: Back up this key file securely if you want to preserve encrypted data

### If You Get a Decryption Error

If you see `cryptography.exceptions.InvalidTag`, the encryption key doesn't match the encrypted data. Options:

**Option 1: Start Fresh (Recommended for Development)**
```bash
# Delete encrypted vector store files
rm data/vectors/index.faiss.enc
rm data/vectors/metadata.pkl.enc
# Optionally delete the key to generate a new one
rm data/keys/master.key
```

**Option 2: Restore the Correct Key**
- If you have a backup of the original `master.key`, restore it to `data/keys/master.key`

**Option 3: Delete Everything and Re-ingest**
```bash
# Clean slate
rm -rf data/vectors/
rm -rf data/keys/
# Re-run ingestion
python main.py
```

## Security Notes

1. **Key Storage**: The encryption key is stored in `data/keys/master.key`
   - On Unix systems: File permissions set to 0600 (owner read/write only)
   - On Windows: Relies on NTFS file permissions

2. **Key Backup**: For production systems, back up the encryption key securely
   - Store in secure key management system
   - Keep offline backup in secure location
   - Do not commit to version control

3. **Key Rotation**: To rotate keys:
   - Export/decrypt data with old key
   - Generate new key (delete `master.key`)
   - Re-encrypt data with new key

## Testing

Test the fix on Windows:

```bash
# Should not produce Unicode errors
python main.py

# Check that key is persisted
ls data/keys/master.key

# Run again - should load existing key
python main.py
```

Verify logs show:
- `Loaded encryption key from data/keys/master.key` (on second run)
- No `UnicodeEncodeError` in output
- No `InvalidTag` errors

## Backward Compatibility

- **Existing installations**: If encrypted data exists but no key file, system will generate new key and fail to load old data (by design for security)
- **Solution**: Users must delete old encrypted files and re-ingest documents
- **Alternative**: Manually create key file with original key bytes if known

## Platform Support

- **Windows**: Full support with UTF-8 console configuration
- **Linux/Unix**: Full support with secure file permissions
- **macOS**: Full support

## Related Files

- `main.py`: Application entry point with UTF-8 configuration
- `src/vectordb/vector_store.py`: Vector store with key persistence
- `src/config.py`: Configuration with key path defaults
- `data/keys/master.key`: Generated encryption key (not in repo)
