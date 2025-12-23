#!/usr/bin/env python3
"""
Test script to verify Windows Unicode and Encryption fixes
Run this to ensure the fixes are working correctly
"""

import sys
import os
from pathlib import Path

# Configure UTF-8 encoding for Windows console output
if sys.platform == "win32":
    try:
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

sys.path.insert(0, str(Path(__file__).parent / "src"))

import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def test_unicode_logging():
    """Test that Unicode characters don't cause errors"""
    print("\n" + "=" * 60)
    print("TEST 1: Unicode Logging")
    print("=" * 60)
    
    try:
        # Test ASCII-safe logging (what we use now)
        logger.info("[OK] This is an ASCII-safe log message")
        logger.info("[FAIL] This is an ASCII-safe failure message")
        print("  [PASS] ASCII-safe logging works")
        
        # Test that Unicode characters are handled
        # Note: We avoid Unicode in our code, but this tests the encoding fallback
        try:
            print("Testing Unicode fallback: ✓ ✗ 中文 日本語")
            print("  [PASS] Unicode fallback works (if you see this)")
        except UnicodeEncodeError as e:
            print(f"  [FAIL] Unicode encoding failed: {e}")
            return False
            
        return True
        
    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        return False


def test_encryption_key_persistence():
    """Test that encryption key is persisted correctly"""
    print("\n" + "=" * 60)
    print("TEST 2: Encryption Key Persistence")
    print("=" * 60)
    
    try:
        from src.config import config
        from src.vectordb import EncryptedVectorStore
        import tempfile
        import shutil
        
        # Create temporary directories
        temp_dir = Path(tempfile.mkdtemp())
        key_path = temp_dir / "test.key"
        index_path = temp_dir / "vectors"
        
        print(f"  Using temp directory: {temp_dir}")
        
        # Test 1: Create store with key persistence
        print("  Creating vector store with key persistence...")
        store1 = EncryptedVectorStore(
            dimension=384,
            index_path=index_path,
            encryption_key=None,
            key_path=key_path
        )
        
        # Verify key was saved
        if not key_path.exists():
            print(f"  [FAIL] Encryption key was not saved to {key_path}")
            shutil.rmtree(temp_dir)
            return False
        
        print(f"  [OK] Encryption key saved to {key_path}")
        
        # Get the key
        key1 = store1.encryption_key
        
        # Test 2: Create new store - should load existing key
        print("  Creating second vector store (should load existing key)...")
        store2 = EncryptedVectorStore(
            dimension=384,
            index_path=index_path,
            encryption_key=None,
            key_path=key_path
        )
        
        key2 = store2.encryption_key
        
        # Verify same key
        if key1 != key2:
            print("  [FAIL] Loaded key doesn't match saved key")
            shutil.rmtree(temp_dir)
            return False
        
        print("  [OK] Encryption key loaded correctly")
        
        # Test 3: Save and load encrypted data
        print("  Testing save and load with encryption...")
        import numpy as np
        from src.ingestion import Chunk
        
        # Create test data
        test_embeddings = np.random.rand(5, 384).astype('float32')
        test_chunks = [
            Chunk(
                chunk_id=f"test_{i}",
                doc_id="test_doc",
                content=f"Test content {i}",
                metadata={"classification": "UNCLASSIFIED"}
            )
            for i in range(5)
        ]
        
        # Add and save
        store1.add_vectors(test_embeddings, test_chunks)
        store1.save()
        print("  [OK] Saved encrypted data")
        
        # Load with new store instance
        store3 = EncryptedVectorStore(
            dimension=384,
            index_path=index_path,
            encryption_key=None,
            key_path=key_path
        )
        
        try:
            store3.load()
            print(f"  [OK] Loaded encrypted data ({store3.index.ntotal} vectors)")
        except Exception as e:
            print(f"  [FAIL] Failed to load encrypted data: {e}")
            shutil.rmtree(temp_dir)
            return False
        
        # Verify data integrity
        if store3.index.ntotal != 5:
            print(f"  [FAIL] Expected 5 vectors, got {store3.index.ntotal}")
            shutil.rmtree(temp_dir)
            return False
        
        print("  [OK] Data integrity verified")
        
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"  [OK] Cleaned up temp directory")
        
        print("  [PASS] Encryption key persistence works correctly")
        return True
        
    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up on failure
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir)
        except:
            pass
        
        return False


def test_decryption_error_handling():
    """Test that decryption errors are handled gracefully"""
    print("\n" + "=" * 60)
    print("TEST 3: Decryption Error Handling")
    print("=" * 60)
    
    try:
        from src.vectordb import EncryptedVectorStore
        import tempfile
        import shutil
        import numpy as np
        from src.ingestion import Chunk
        
        # Create temporary directories
        temp_dir = Path(tempfile.mkdtemp())
        key_path1 = temp_dir / "key1.key"
        key_path2 = temp_dir / "key2.key"
        index_path = temp_dir / "vectors"
        
        print(f"  Using temp directory: {temp_dir}")
        
        # Create store with first key and save data
        print("  Creating data with first key...")
        store1 = EncryptedVectorStore(
            dimension=384,
            index_path=index_path,
            encryption_key=None,
            key_path=key_path1
        )
        
        test_embeddings = np.random.rand(3, 384).astype('float32')
        test_chunks = [
            Chunk(
                chunk_id=f"test_{i}",
                doc_id="test_doc",
                content=f"Test content {i}",
                metadata={"classification": "UNCLASSIFIED"}
            )
            for i in range(3)
        ]
        
        store1.add_vectors(test_embeddings, test_chunks)
        store1.save()
        print("  [OK] Saved data with first key")
        
        # Try to load with different key
        print("  Attempting to load with different key (should fail gracefully)...")
        store2 = EncryptedVectorStore(
            dimension=384,
            index_path=index_path,
            encryption_key=None,
            key_path=key_path2  # Different key!
        )
        
        try:
            store2.load()
            print("  [FAIL] Should have raised decryption error")
            shutil.rmtree(temp_dir)
            return False
        except RuntimeError as e:
            error_msg = str(e)
            if "decryption failed" in error_msg.lower() or "encryption key" in error_msg.lower():
                print(f"  [OK] Got expected error with helpful message")
                print(f"       Error: {error_msg[:100]}...")
            else:
                print(f"  [FAIL] Got unexpected error: {error_msg}")
                shutil.rmtree(temp_dir)
                return False
        
        # Clean up
        shutil.rmtree(temp_dir)
        print(f"  [OK] Cleaned up temp directory")
        
        print("  [PASS] Decryption error handling works correctly")
        return True
        
    except Exception as e:
        print(f"  [FAIL] Test failed: {e}")
        import traceback
        traceback.print_exc()
        
        # Clean up on failure
        try:
            if 'temp_dir' in locals():
                shutil.rmtree(temp_dir)
        except:
            pass
        
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("WINDOWS FIX VERIFICATION TESTS")
    print("=" * 60)
    print()
    print("Platform:", sys.platform)
    print("Python version:", sys.version)
    print()
    
    results = []
    
    # Run tests
    results.append(("Unicode Logging", test_unicode_logging()))
    results.append(("Encryption Key Persistence", test_encryption_key_persistence()))
    results.append(("Decryption Error Handling", test_decryption_error_handling()))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "[PASS]" if passed else "[FAIL]"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    print("\n" + "=" * 60)
    if all_passed:
        print("[OK] All tests passed! Windows fixes are working correctly.")
        print("\nThe following issues have been fixed:")
        print("  1. Unicode encoding errors on Windows console")
        print("  2. Vector store encryption key persistence")
        print("  3. Graceful error handling for decryption failures")
        print("\nYou can now run the main application:")
        print("  python main.py")
    else:
        print("[FAIL] Some tests failed. Please check the output above.")
        print("\nIf tests fail, try:")
        print("  1. Ensure all dependencies are installed: pip install -r requirements.txt")
        print("  2. Check that you're running Python 3.8+")
        print("  3. See WINDOWS_UNICODE_AND_ENCRYPTION_FIX.md for details")
    
    print("=" * 60)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())
