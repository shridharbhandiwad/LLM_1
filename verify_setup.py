#!/usr/bin/env python3
"""
Quick verification script to test Windows compatibility fixes
Run this to verify the setup is correct
"""

import sys
from pathlib import Path

def test_imports():
    """Test that basic imports work"""
    print("Testing imports...")
    try:
        from src.config import config
        print("  ✓ Config module imported")
    except Exception as e:
        print(f"  ✗ Config import failed: {e}")
        return False
    
    try:
        from src.embedding import download_model_for_offline_use
        print("  ✓ Embedding module imported")
    except Exception as e:
        print(f"  ✗ Embedding import failed: {e}")
        return False
    
    return True


def test_paths():
    """Test that paths are resolved correctly"""
    print("\nTesting path configuration...")
    try:
        from src.config import config
        
        print(f"  Base path: {config.base_path}")
        print(f"  Model path: {config.model_path}")
        print(f"  Data path: {config.data_path}")
        print(f"  Log path: {config.log_path}")
        print(f"  Embedding model path: {config.embedding_model_path}")
        
        # Verify paths are absolute and resolved
        if not config.base_path.is_absolute():
            print("  ✗ Base path is not absolute")
            return False
        
        print("  ✓ All paths resolved correctly")
        return True
        
    except Exception as e:
        print(f"  ✗ Path test failed: {e}")
        return False


def test_dependencies():
    """Test that required dependencies are available"""
    print("\nTesting dependencies...")
    
    deps = {
        'torch': 'PyTorch',
        'sentence_transformers': 'Sentence Transformers',
        'transformers': 'Transformers',
        'numpy': 'NumPy',
        'pathlib': 'Pathlib'
    }
    
    missing = []
    for module, name in deps.items():
        try:
            __import__(module)
            print(f"  ✓ {name} installed")
        except ImportError:
            print(f"  ✗ {name} not installed")
            missing.append(name)
    
    if missing:
        print(f"\n  Missing dependencies: {', '.join(missing)}")
        print("  Install with: pip install -r requirements.txt")
        return False
    
    return True


def test_directory_creation():
    """Test that directories can be created"""
    print("\nTesting directory creation...")
    try:
        from src.config import config
        
        # Try creating directories
        config.create_directories()
        
        # Verify they exist
        dirs_to_check = [
            config.model_path,
            config.data_path,
            config.log_path
        ]
        
        for dir_path in dirs_to_check:
            if not dir_path.exists():
                print(f"  ✗ Directory not created: {dir_path}")
                return False
            print(f"  ✓ Directory exists: {dir_path.name}")
        
        print("  ✓ All directories created successfully")
        return True
        
    except Exception as e:
        print(f"  ✗ Directory creation failed: {e}")
        return False


def main():
    """Run all verification tests"""
    print("=" * 60)
    print("SETUP VERIFICATION")
    print("=" * 60)
    print()
    
    results = []
    
    # Run tests
    results.append(("Imports", test_imports()))
    results.append(("Paths", test_paths()))
    results.append(("Dependencies", test_dependencies()))
    results.append(("Directory Creation", test_directory_creation()))
    
    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    
    for test_name, passed in results:
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(result[1] for result in results)
    
    if all_passed:
        print("\n✓ All tests passed! Setup is correct.")
        print("\nNext steps:")
        print("  1. Run: python scripts/download_models.py")
        print("  2. See WINDOWS_SETUP.md for more information")
        return 0
    else:
        print("\n✗ Some tests failed. Please fix the issues above.")
        print("\nCommon fixes:")
        print("  - Install dependencies: pip install -r requirements.txt")
        print("  - Check file permissions")
        print("  - See WINDOWS_SETUP.md for troubleshooting")
        return 1


if __name__ == "__main__":
    sys.exit(main())
