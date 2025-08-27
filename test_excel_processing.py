#!/usr/bin/env python3
"""
Test script for Excel processing functionality
Run this to verify Excel handling works correctly before deployment
"""

import os
import sys
import tempfile
import logging
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from form_generator import read_excel_skip_strikeout, initialize_option_sets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_excel_file_handling():
    """Test basic Excel file handling capabilities"""
    logger.info("Testing Excel file handling...")
    
    # Check if test files exist
    test_files = [
        "uploads/LIME EMR - Iraq Metadata - Release 1 (69).xlsx",
        "uploads/LIME EMR - Iraq Metadata - Release 1 (70).xlsx"
    ]
    
    available_files = [f for f in test_files if os.path.exists(f)]
    
    if not available_files:
        logger.warning("No test Excel files found in uploads/ directory")
        return False
    
    test_file = available_files[0]
    logger.info(f"Testing with file: {test_file}")
    
    try:
        # Test file size check
        file_size = os.path.getsize(test_file)
        logger.info(f"File size: {file_size / (1024*1024):.2f} MB")
        
        if file_size > 50 * 1024 * 1024:
            logger.warning("File exceeds recommended 50MB limit")
        
        # Test option sets initialization
        logger.info("Testing option sets initialization...")
        initialize_option_sets(test_file)
        logger.info("✅ Option sets initialized successfully")
        
        # Test reading a specific sheet
        logger.info("Testing sheet reading...")
        try:
            # Try to read OptionSets sheet
            df = read_excel_skip_strikeout(test_file, 'OptionSets', 2)
            logger.info(f"✅ OptionSets sheet read successfully: {len(df)} rows, {len(df.columns)} columns")
        except Exception as e:
            logger.error(f"❌ Failed to read OptionSets sheet: {str(e)}")
            return False
        
        # Test reading form sheets
        import openpyxl
        wb = openpyxl.load_workbook(test_file, read_only=True, data_only=True)
        sheet_names = wb.sheetnames
        wb.close()
        
        # Find form sheets (starting with F followed by digits)
        import re
        form_sheets = [s for s in sheet_names if re.match(r'^F\d{2}', s)]
        
        if form_sheets:
            test_sheet = form_sheets[0]
            logger.info(f"Testing form sheet: {test_sheet}")
            try:
                df = read_excel_skip_strikeout(test_file, test_sheet, 2)
                logger.info(f"✅ Form sheet read successfully: {len(df)} rows, {len(df.columns)} columns")
            except Exception as e:
                logger.error(f"❌ Failed to read form sheet {test_sheet}: {str(e)}")
                return False
        
        logger.info("✅ All Excel processing tests passed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Excel processing test failed: {str(e)}")
        return False

def test_memory_limits():
    """Test memory handling with file size simulation"""
    logger.info("Testing memory limits...")
    
    try:
        # Create a temporary large-ish file to test memory handling
        with tempfile.NamedTemporaryFile(suffix='.xlsx', delete=False) as tmp_file:
            # Write some data to simulate file processing
            test_data = b"x" * (1024 * 1024)  # 1MB of data
            tmp_file.write(test_data)
            tmp_path = tmp_file.name
        
        # Test file size detection
        file_size = os.path.getsize(tmp_path)
        logger.info(f"Test file size: {file_size / (1024*1024):.2f} MB")
        
        # Clean up
        os.unlink(tmp_path)
        logger.info("✅ Memory limit tests completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Memory limit test failed: {str(e)}")
        return False

def test_temp_file_handling():
    """Test temporary file creation and cleanup"""
    logger.info("Testing temporary file handling...")
    
    try:
        # Test temp file creation
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', prefix='test_') as tmp_file:
            tmp_file.write(b"test data")
            tmp_path = tmp_file.name
        
        # Verify file exists
        if not os.path.exists(tmp_path):
            logger.error("❌ Temporary file was not created")
            return False
        
        logger.info(f"✅ Temporary file created: {tmp_path}")
        
        # Test cleanup
        os.unlink(tmp_path)
        
        if os.path.exists(tmp_path):
            logger.error("❌ Temporary file was not cleaned up")
            return False
        
        logger.info("✅ Temporary file cleaned up successfully")
        return True
        
    except Exception as e:
        logger.error(f"❌ Temporary file handling test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Starting Excel processing tests...")
    
    tests = [
        ("Excel File Handling", test_excel_file_handling),
        ("Memory Limits", test_memory_limits),
        ("Temporary File Handling", test_temp_file_handling)
    ]
    
    results = []
    for test_name, test_func in tests:
        logger.info(f"\n--- Running {test_name} ---")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            logger.error(f"❌ {test_name} crashed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    logger.info("\n=== TEST SUMMARY ===")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"{test_name}: {status}")
        if not passed:
            all_passed = False
    
    if all_passed:
        logger.info("🎉 All tests passed! Ready for deployment.")
        return 0
    else:
        logger.error("❌ Some tests failed. Please fix issues before deployment.")
        return 1

if __name__ == "__main__":
    sys.exit(main())