# Streamlit Cloud Deployment Guide for Excel Processing Apps

## Overview
This guide addresses common issues when deploying Excel processing applications to Streamlit Cloud, with specific solutions for file upload failures, memory limitations, and performance optimization.

## Common Issues and Solutions

### 1. File Upload Failures

#### **Issue**: Excel files fail to upload or process on Streamlit Cloud
#### **Causes**:
- File path permissions on cloud infrastructure
- Memory limitations with large files
- Temporary file handling differences between local and cloud
- Network timeouts during upload

#### **Solutions Implemented**:

```python
# Robust file handling with proper error reporting
def safe_file_handler(uploaded_file) -> Tuple[Optional[str], str]:
    """
    Safely handle uploaded file with proper error handling for Streamlit Cloud.
    """
    try:
        # Check file size (limit to 50MB for safety)
        file_size = len(uploaded_file.getvalue())
        if file_size > 50 * 1024 * 1024:  # 50MB limit
            return None, "File size exceeds 50MB limit. Please use a smaller file."
        
        # Use tempfile for cross-platform compatibility
        with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', prefix='formgen_') as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            temp_path = tmp_file.name
            
        # Validate file immediately after creation
        with openpyxl.load_workbook(temp_path, read_only=True, data_only=True) as wb:
            sheet_names = wb.sheetnames
            
        return temp_path, ""
        
    except MemoryError:
        return None, "File too large to process. Please reduce file size."
    except Exception as e:
        return None, f"Error processing file: {str(e)}"
```

### 2. Memory Management

#### **Issue**: Out of memory errors when processing large Excel files
#### **Causes**:
- Streamlit Cloud has ~1GB memory limit
- Loading entire Excel files into memory
- Multiple DataFrames created simultaneously
- Not releasing memory after processing

#### **Solutions Implemented**:

```python
# Memory-optimized Excel reading
wb = openpyxl.load_workbook(filepath, read_only=True, data_only=True, keep_links=False)
ws = wb[sheet_name]

# Always close workbooks to free memory
wb.close()

# File size warnings
if file_size > 100 * 1024 * 1024:  # 100MB warning
    logger.warning(f"Large file detected. Processing may be slow.")

# Memory error handling
except MemoryError:
    raise MemoryError("Insufficient memory to process file. Try reducing file size.")
```

### 3. Temporary File Management

#### **Issue**: Files saved to local directories fail on cloud
#### **Causes**:
- Write permissions in cloud environment
- Persistent storage expectations
- File cleanup not implemented

#### **Solutions Implemented**:

```python
# Use system temp directory instead of custom paths
with tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx', prefix='formgen_') as tmp_file:
    tmp_file.write(uploaded_file.getvalue())
    temp_path = tmp_file.name

# Proper cleanup mechanism
def cleanup_temp_file(file_path: Optional[str]) -> None:
    if file_path and os.path.exists(file_path):
        try:
            os.unlink(file_path)
            logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Could not clean up temp file: {str(e)}")

# Session-based cleanup
def cleanup_session_temp_files():
    if 'temp_files_to_cleanup' in st.session_state:
        for temp_file in st.session_state.temp_files_to_cleanup:
            cleanup_temp_file(temp_file)
        st.session_state.temp_files_to_cleanup = []
```

### 4. Enhanced Error Handling

#### **Issue**: Generic error messages don't help users troubleshoot
#### **Solutions**:

```python
# Specific error types with actionable solutions
try:
    wb = openpyxl.load_workbook(temp_file_path, read_only=True, data_only=True)
except zipfile.BadZipFile:
    st.error("❌ Invalid Excel file format")
    st.info("💡 **Solutions:**")
    st.info("• Save your file as 'Excel Workbook (.xlsx)' format")
    st.info("• Try opening and re-saving the file in Excel")
except MemoryError:
    st.error("❌ File too large to process")
    st.info("💡 **Solutions:**")
    st.info("• Reduce the file size by removing unnecessary data")
    st.info("• Split large files into smaller ones")
except PermissionError:
    st.error("❌ Permission denied")
    st.info("💡 Please try uploading the file again")
```

### 5. Performance Optimizations

#### **Implementations**:

```python
# Progress indicators for long operations
progress_bar = st.progress(0)
status_text = st.empty()

# Chunked processing for large datasets
def process_large_sheet(df, chunk_size=1000):
    for i in range(0, len(df), chunk_size):
        chunk = df.iloc[i:i+chunk_size]
        # Process chunk
        yield chunk

# Logging for debugging
logger.info(f"Processing file size: {file_size / (1024*1024):.2f} MB")
logger.info(f"Created DataFrame with {len(df)} rows and {len(df.columns)} columns")
```

## Configuration Files

### `.streamlit/config.toml`
```toml
[server]
maxUploadSize = 50
maxMessageSize = 200
runOnSave = false
fileWatcherType = "none"

[browser]
gatherUsageStats = false
showErrorDetails = true

[global]
suppressDeprecationWarnings = true
```

## Best Practices for Streamlit Cloud

### 1. File Handling
- ✅ Use `tempfile.NamedTemporaryFile()` for temporary files
- ✅ Always set file size limits (recommend 50MB max)
- ✅ Validate files immediately after upload
- ✅ Implement proper cleanup mechanisms
- ❌ Don't write to custom directories like `uploads/`
- ❌ Don't assume files persist between sessions

### 2. Memory Management
- ✅ Use `read_only=True` when loading Excel files
- ✅ Close file handles explicitly with `wb.close()`
- ✅ Process data in chunks for large files
- ✅ Clear variables after use with `del variable`
- ❌ Don't load multiple large files simultaneously
- ❌ Don't keep large DataFrames in memory longer than needed

### 3. Error Handling
- ✅ Catch specific exception types
- ✅ Provide actionable error messages
- ✅ Log errors for debugging
- ✅ Implement fallback strategies
- ❌ Don't use generic `except:` clauses
- ❌ Don't expose internal error details to users

### 4. User Experience
- ✅ Show progress indicators for long operations
- ✅ Provide clear status messages
- ✅ Implement retry mechanisms
- ✅ Validate input early and often
- ❌ Don't block UI during processing
- ❌ Don't leave users guessing about progress

### 5. Debugging
- ✅ Use structured logging
- ✅ Log file sizes and processing metrics
- ✅ Capture performance data
- ✅ Monitor resource usage
- ❌ Don't rely only on print statements
- ❌ Don't log sensitive data

## Testing for Cloud Deployment

### Local Testing
1. Test with large files (>10MB)
2. Test with corrupted files
3. Test with files having special characters
4. Test memory limits by processing multiple files
5. Test network interruptions

### Cloud Testing
1. Deploy to Streamlit Cloud staging
2. Test file upload limits
3. Monitor memory usage in logs
4. Test error recovery scenarios
5. Verify cleanup mechanisms work

## Monitoring and Maintenance

### Key Metrics to Monitor
- File upload success rate
- Average processing time
- Memory usage patterns
- Error frequencies
- User abandonment points

### Regular Maintenance
- Review error logs weekly
- Update file size limits based on usage
- Optimize memory usage for common file types
- Update error messages based on user feedback

## Troubleshooting Common Issues

### Issue: "File not found" after upload
**Solution**: Check temporary file handling and ensure proper file path management

### Issue: "Out of memory" errors
**Solution**: Implement file size limits and memory-optimized processing

### Issue: "Permission denied" errors
**Solution**: Use system temporary directories instead of custom paths

### Issue: Slow processing times
**Solution**: Implement progress indicators and consider chunked processing

### Issue: Files appear corrupted
**Solution**: Validate file format immediately after upload and provide specific error messages