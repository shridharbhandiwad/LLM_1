# Windows Setup Guide

This guide helps you set up the Offline RAG System on Windows.

## Prerequisites

1. **Python 3.8+** - Download from [python.org](https://www.python.org/downloads/)
   - ✅ Make sure to check "Add Python to PATH" during installation
   
2. **Git for Windows** (optional) - For cloning the repository
   - Download from [git-scm.com](https://git-scm.com/download/win)

## Installation Steps

### 1. Clone or Download the Project

```bash
# Using Git
git clone <repository-url>
cd LLM_1

# Or download and extract the ZIP file
```

### 2. Install Dependencies

Open Command Prompt or PowerShell in the project directory:

```bash
# Install all required packages
pip install -r requirements.txt
```

**Note:** This will download and install:
- PyTorch
- sentence-transformers
- transformers
- And other required packages

This may take several minutes depending on your internet connection.

### 3. Download Models

After installing dependencies, run the model download script:

```bash
python scripts/download_models.py
```

This will:
- Check that all dependencies are installed
- Create the necessary directories in your project folder
- Download the embedding model (sentence-transformers/all-MiniLM-L6-v2)
- Provide instructions for downloading the LLM model

### 4. Download LLM Model (Manual Step)

The script will provide instructions for downloading a quantized LLM model. Choose one:

**Option 1: Using HuggingFace CLI**
```bash
pip install huggingface-hub
huggingface-cli download bartowski/Llama-3.2-3B-Instruct-GGUF --include "*Q4_K_M.gguf" --local-dir models/llm
```

**Option 2: Manual Download**
1. Go to https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF
2. Download the file ending in `Q4_K_M.gguf`
3. Place it in the `models/llm/` directory

### 5. Configure Environment (Optional)

```bash
# Copy the example configuration
copy .env.example .env

# Edit .env if you need custom settings
notepad .env
```

**Note:** Default settings work for most cases. The system will automatically use paths relative to your project directory.

## Running the System

```bash
python main.py
```

Or use the Python API:

```python
from main import OfflineRAGSystem
from pathlib import Path

system = OfflineRAGSystem()
system.initialize()

# Ingest documents
system.ingest_documents(Path("data/documents"), user_id="admin")

# Query
response = system.query("What is the radar's maximum range?", user_id="analyst")
print(response)
```

## Troubleshooting

### Issue: "sentence-transformers not installed"

**Solution:** Install dependencies first
```bash
pip install -r requirements.txt
```

### Issue: "torch not found" or CUDA errors

**Solution:** PyTorch CPU version is included in requirements.txt. If you have a GPU and want to use it:
```bash
# For CUDA 11.8
pip install torch --index-url https://download.pytorch.org/whl/cu118

# For CUDA 12.1
pip install torch --index-url https://download.pytorch.org/whl/cu121
```

### Issue: Path-related errors

**Solution:** The system now uses relative paths automatically. Make sure you're running scripts from the project root directory:
```bash
cd path\to\LLM_1
python scripts\download_models.py
```

### Issue: Permission errors when creating directories

**Solution:** Run as Administrator or choose a directory where you have write permissions:
1. Right-click Command Prompt
2. Select "Run as Administrator"
3. Navigate to your project directory
4. Run the script again

### Issue: Model download is slow or fails

**Solution:**
- Ensure you have a stable internet connection
- The embedding model is ~90MB, be patient
- If download fails, try again - the script will resume where it left off
- Consider using a VPN if you're behind a firewall

## Windows-Specific Notes

1. **Paths**: The system automatically handles Windows paths (backslashes). No manual configuration needed.

2. **Antivirus**: Some antivirus software may flag ML models. Add an exception for the `models/` directory if needed.

3. **Firewall**: Windows Firewall may prompt when running the API server. Allow access for localhost connections.

4. **Long Paths**: If you encounter path length issues, enable long path support:
   - Open Registry Editor (regedit)
   - Navigate to: `HKEY_LOCAL_MACHINE\SYSTEM\CurrentControlSet\Control\FileSystem`
   - Set `LongPathsEnabled` to 1
   - Restart your computer

5. **PowerShell Execution Policy**: If scripts won't run:
   ```powershell
   Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
   ```

## Testing Installation

```bash
# Run tests to verify everything works
pytest tests/ -v

# Quick test
python -c "from src.config import config; print(f'Base path: {config.base_path}')"
```

## Getting Help

If you encounter issues:

1. Check this troubleshooting guide
2. Ensure all dependencies are installed: `pip list`
3. Verify Python version: `python --version` (should be 3.8+)
4. Check the error message carefully - it usually indicates what's missing

## Next Steps

- See `README.md` for general usage
- See `PROJECT_SUMMARY.md` for system architecture
- See `INDEX.md` for detailed documentation

---

**Note:** This system is designed for offline use after initial setup. Once models are downloaded, you can disconnect from the internet and the system will work completely offline.
