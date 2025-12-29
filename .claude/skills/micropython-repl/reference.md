# MicroPython REPL Tool - Advanced Reference

This document provides detailed information about mpy-repl-tool commands and advanced usage patterns.

## Command Reference

### Connection String

All commands use the RFC2217 connection protocol:
```
-p rfc2217://host.docker.internal:2217
```

Alternative connection methods (if supported):
- Serial: `-p /dev/ttyUSB0` or `-p COM3`
- Network: `-p socket://192.168.1.100:23`

### File Operations

#### push - Upload Files

```bash
# Push single file to root
python -m there -p rfc2217://host.docker.internal:2217 push file.py /

# Push multiple files
python -m there -p rfc2217://host.docker.internal:2217 push file1.py file2.py /

# Push with wildcards
python -m there -p rfc2217://host.docker.internal:2217 push *.py /

# Push to subdirectory (create if needed)
python -m there -p rfc2217://host.docker.internal:2217 push module.py /lib/

# Push entire directory recursively
python -m there -p rfc2217://host.docker.internal:2217 push src/ /
```

#### pull - Download Files

```bash
# Download file
python -m there -p rfc2217://host.docker.internal:2217 pull /main.py main_backup.py

# Download multiple files
python -m there -p rfc2217://host.docker.internal:2217 pull /boot.py /main.py .
```

#### cat - View File Contents

```bash
# Display file contents
python -m there -p rfc2217://host.docker.internal:2217 cat /main.py

# Save to local file
python -m there -p rfc2217://host.docker.internal:2217 cat /main.py > local_copy.py

# View multiple files
python -m there -p rfc2217://host.docker.internal:2217 cat /boot.py /main.py
```

#### ls - List Files

```bash
# List root directory
python -m there -p rfc2217://host.docker.internal:2217 ls

# List specific directory
python -m there -p rfc2217://host.docker.internal:2217 ls /lib

# Detailed listing
python -m there -p rfc2217://host.docker.internal:2217 ls -l

# Recursive listing
python -m there -p rfc2217://host.docker.internal:2217 ls -R
```

#### rm - Remove Files

```bash
# Remove single file
python -m there -p rfc2217://host.docker.internal:2217 rm /old_file.py

# Remove multiple files
python -m there -p rfc2217://host.docker.internal:2217 rm /file1.py /file2.py

# Remove directory (if empty)
python -m there -p rfc2217://host.docker.internal:2217 rmdir /old_lib
```

### Code Execution

#### run - Execute File on Board

```bash
# Run a file that exists on the board
python -m there -p rfc2217://host.docker.internal:2217 run /main.py

# Run with output capture
python -m there -p rfc2217://host.docker.internal:2217 run /test.py > test_output.txt
```

#### eval - Evaluate Python Expression

```bash
# Simple expression
python -m there -p rfc2217://host.docker.internal:2217 eval "1 + 1"

# Call a function
python -m there -p rfc2217://host.docker.internal:2217 eval "print('Hello')"

# Import and use module (if already on board)
python -m there -p rfc2217://host.docker.internal:2217 eval "import machine; machine.freq()"

# Multi-line execution
python -m there -p rfc2217://host.docker.internal:2217 eval "
import gc
gc.collect()
print(gc.mem_free())
"
```

#### exec - Execute Local File Remotely

```bash
# Execute a local file without uploading it permanently
python -m there -p rfc2217://host.docker.internal:2217 exec local_script.py

# Execute with arguments (script must handle sys.argv)
python -m there -p rfc2217://host.docker.internal:2217 exec script.py arg1 arg2
```

### Interactive Sessions

#### repl - Start Interactive REPL

```bash
# Start REPL session
python -m there -p rfc2217://host.docker.internal:2217 repl

# Exit REPL: Ctrl+] or Ctrl+D
```

Within the REPL, you can:
- Execute Python statements interactively
- Import modules
- Test functions
- Debug code in real-time

### Board Control

#### reset - Soft Reset Board

```bash
# Soft reset (like Ctrl+D in REPL)
python -m there -p rfc2217://host.docker.internal:2217 reset
```

#### rtc - Set Real-Time Clock

```bash
# Set RTC to current system time
python -m there -p rfc2217://host.docker.internal:2217 rtc --set-rtc
```

### Utility Commands

#### df - Disk Space

```bash
# Show filesystem usage
python -m there -p rfc2217://host.docker.internal:2217 df
```

#### mount - Mount Filesystem

```bash
# Mount the filesystem (if needed)
python -m there -p rfc2217://host.docker.internal:2217 mount
```

## Advanced Usage Patterns

### Testing Workflow

```bash
# 1. Upload test file
python -m there -p rfc2217://host.docker.internal:2217 push test.py /

# 2. Execute tests
python -m there -p rfc2217://host.docker.internal:2217 eval "import test; test.run_all()"

# 3. Capture results
python -m there -p rfc2217://host.docker.internal:2217 cat /test_results.txt > results.txt

# 4. Clean up
python -m there -p rfc2217://host.docker.internal:2217 rm /test.py /test_results.txt
```

### Benchmarking

```bash
# Upload benchmark script
python -m there -p rfc2217://host.docker.internal:2217 push benchmark.py /

# Run with timing
time python -m there -p rfc2217://host.docker.internal:2217 run /benchmark.py

# Or use MicroPython's time module
python -m there -p rfc2217://host.docker.internal:2217 eval "
import time
import benchmark
start = time.ticks_ms()
benchmark.run()
print('Duration:', time.ticks_diff(time.ticks_ms(), start), 'ms')
"
```

### Memory Profiling

```bash
python -m there -p rfc2217://host.docker.internal:2217 eval "
import gc
gc.collect()
print('Free memory before:', gc.mem_free())
import my_module
print('Free memory after:', gc.mem_free())
"
```

### Module Development

```bash
# Push module to lib directory
python -m there -p rfc2217://host.docker.internal:2217 push my_module.py /lib/

# Test import
python -m there -p rfc2217://host.docker.internal:2217 eval "import my_module; my_module.test()"

# Update module
python -m there -p rfc2217://host.docker.internal:2217 push my_module.py /lib/

# Soft reset to reload
python -m there -p rfc2217://host.docker.internal:2217 reset
```

## Error Handling

### Common Errors

**OSError: [Errno 2] ENOENT**
- File or directory not found on the board
- Verify path with `ls` command

**MemoryError**
- Board ran out of RAM
- Use `gc.collect()` to free memory
- Reduce data size or optimize code

**ImportError**
- Module not found on board
- Ensure all dependencies are pushed
- Check PYTHONPATH and /lib directory

**Connection Refused/Timeout**
- RFC2217 server not running
- Check `host.docker.internal:2217` is accessible
- Verify network connectivity

### Debugging Tips

1. **Check board status**:
   ```bash
   python -m there -p rfc2217://host.docker.internal:2217 eval "print('Board is alive')"
   ```

2. **Verify file upload**:
   ```bash
   python -m there -p rfc2217://host.docker.internal:2217 ls -l / | grep myfile.py
   ```

3. **Check memory**:
   ```bash
   python -m there -p rfc2217://host.docker.internal:2217 eval "import gc; gc.collect(); print(gc.mem_free())"
   ```

4. **Test imports**:
   ```bash
   python -m there -p rfc2217://host.docker.internal:2217 eval "import sys; print(sys.path)"
   ```

## Performance Considerations

- **File transfer**: Larger files take longer; consider compression for big transfers
- **Code size**: MicroPython boards have limited flash storage
- **RAM usage**: Keep imports minimal and use `gc.collect()` regularly
- **Execution time**: Complex calculations may take longer on embedded hardware

## Integration with Project Files

This skill is designed to work with the existing MicroPython files in the workspace:

- [fb_opt.py](../../fb_opt.py) - Framebuffer optimization module
- [test.py](../../test.py) - Test suite
- [run.py](../../run.py) - Runner script

Use the push command to upload these files to the board for testing.
