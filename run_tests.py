#!/usr/bin/env python3
"""
Test runner for the OpenMRS Form Generator
"""
import subprocess
import sys
import os

def run_tests():
    """Run the test suite"""
    print("Running OpenMRS Form Generator Tests...")
    print("=" * 50)
    
    try:
        # Run pytest with verbose output
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_form_generator.py', 
            '-v', '--tb=short'
        ], cwd=os.path.dirname(os.path.abspath(__file__)))
        
        if result.returncode == 0:
            print("\n" + "=" * 50)
            print("✅ All tests passed successfully!")
        else:
            print("\n" + "=" * 50)
            print("❌ Some tests failed. Please check the output above.")
            
        return result.returncode
        
    except Exception as e:
        print(f"Error running tests: {e}")
        return 1

if __name__ == "__main__":
    exit_code = run_tests()
    sys.exit(exit_code)
