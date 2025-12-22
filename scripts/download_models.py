#!/usr/bin/env python3
"""
Model Download Script
Downloads models on internet-connected machine for offline transfer

RUN THIS SCRIPT ON AN INTERNET-CONNECTED MACHINE
Then transfer the models directory to your air-gapped system
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.config import config
from src.embedding import download_model_for_offline_use


def download_embedding_model():
    """Download embedding model"""
    print("=" * 60)
    print("DOWNLOADING EMBEDDING MODEL")
    print("=" * 60)
    
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    target_path = config.embedding_model_path
    
    print(f"Model: {model_name}")
    print(f"Target: {target_path}")
    print()
    
    try:
        download_model_for_offline_use(model_name, target_path)
        print("\n✓ Embedding model downloaded successfully")
        print(f"  Location: {target_path}")
    except Exception as e:
        print(f"\n✗ Failed to download embedding model: {e}")
        return False
    
    return True


def download_llm_model():
    """Instructions for downloading LLM model"""
    print("\n" + "=" * 60)
    print("LLM MODEL DOWNLOAD")
    print("=" * 60)
    
    print("\nThe LLM model must be downloaded manually in GGUF format.")
    print("\nRecommended models:")
    print("  1. LLaMA-3.2-3B-Instruct (Q4_K_M)")
    print("     https://huggingface.co/meta-llama/Llama-3.2-3B-Instruct")
    print("     Quantized GGUF: https://huggingface.co/bartowski/Llama-3.2-3B-Instruct-GGUF")
    print()
    print("  2. Mistral-7B-Instruct-v0.3 (Q4_K_M)")
    print("     https://huggingface.co/mistralai/Mistral-7B-Instruct-v0.3")
    print()
    print("  3. Qwen2.5-3B-Instruct (Q4_K_M)")
    print("     https://huggingface.co/Qwen/Qwen2.5-3B-Instruct")
    print()
    print("Download instructions:")
    print("  1. Go to the model page on HuggingFace")
    print("  2. Download the GGUF file (Q4_K_M variant recommended)")
    print("  3. Place it at:")
    print(f"     {config.llm_model_path}")
    print()
    print("Example using huggingface-cli:")
    print("  huggingface-cli download bartowski/Llama-3.2-3B-Instruct-GGUF \\")
    print(f"    --local-dir {config.model_path / 'llm'} \\")
    print("    --include '*Q4_K_M.gguf'")
    print()


def main():
    """Main download script"""
    print("\n" + "=" * 60)
    print("OFFLINE RAG SYSTEM - MODEL DOWNLOAD")
    print("=" * 60)
    print("\nThis script downloads models for offline use.")
    print("Run this on an INTERNET-CONNECTED machine.")
    print("Then transfer the models directory to your air-gapped system.")
    print()
    
    # Create model directories
    config.create_directories()
    
    # Download embedding model
    success = download_embedding_model()
    
    if not success:
        print("\n✗ Model download failed")
        return 1
    
    # LLM download instructions
    download_llm_model()
    
    print("\n" + "=" * 60)
    print("NEXT STEPS")
    print("=" * 60)
    print("\n1. Verify embedding model:")
    print(f"   ls {config.embedding_model_path}")
    print()
    print("2. Download LLM model (see instructions above)")
    print()
    print("3. Transfer models directory to air-gapped system:")
    print(f"   tar -czf models.tar.gz {config.model_path}")
    print("   # Transfer models.tar.gz to air-gapped system")
    print("   # Extract: tar -xzf models.tar.gz")
    print()
    print("4. Run system on air-gapped machine:")
    print("   python main.py")
    print()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
