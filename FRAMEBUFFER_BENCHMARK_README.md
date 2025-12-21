# MicroPython Framebuffer Performance Benchmark Suite

This benchmark suite compares the performance of MicroPython's built-in C framebuffer module against pure MicroPython implementations using `@micropython.native` and `@micropython.viper` decorators.

## Files

- **`fb_opt.py`**: Pure MicroPython framebuffer implementations
  - `FrameBufferPure`: Uses `@micropython.viper` for maximum optimization
  - `FrameBufferNative`: Uses `@micropython.native` for moderate optimization

- **`test.py`**: Comprehensive benchmarking suite with verification

## Features

### Implemented Operations

Both pure Python implementations support:
- `pixel(x, y, c)` - Get/set individual pixels
- `fill(c)` - Fill entire framebuffer
- `hline(x, y, w, c)` - Draw horizontal line
- `vline(x, y, h, c)` - Draw vertical line
- `rect(x, y, w, h, c, fill)` - Draw rectangle (outline or filled)
- `fill_rect(x, y, w, h, c)` - Fill rectangle
- `line(x0, y0, x1, y1, c)` - Draw line (Bresenham's algorithm)

### Supported Formats

- `MONO_VLSB` - Monochrome, vertical LSB (most common for OLED displays)
- `RGB565` - 16-bit RGB color
- `GS8` - 8-bit grayscale

### Benchmark Tests

The suite includes 10 comprehensive tests:

1. **Single pixel writes** - Individual pixel operations
2. **Horizontal lines** - Full-width hline performance
3. **Vertical lines** - Full-height vline performance
4. **Fill operation** - Full buffer fill
5. **Fill rectangle** - 50x50 filled rectangle
6. **Rectangle outline** - 50x50 outline
7. **Line drawing** - Diagonal line across display
8. **Grid pattern** - Complex pattern with multiple lines
9. **Scatter pattern** - 100 random pixel writes
10. **Horizontal stripes** - Multiple horizontal lines

### Output Verification

Each test automatically verifies that all three implementations produce **identical output**, ensuring functional correctness alongside performance measurement.

## Usage

### Quick Test

Run a quick verification to ensure all implementations work correctly:

```python
import fb_benchmark

# Run quick test (verifies all operations produce matching output)
if fb_benchmark.quick_test():
    print("All implementations working correctly!")
```

### Full Benchmark Suite

Run comprehensive benchmarks:

```python
import fb_benchmark

# Run all benchmarks with standard configurations
fb_benchmark.run_standard_benchmarks()
```

### Custom Configuration

Run benchmarks with specific framebuffer size and format:

```python
import fb_benchmark
import framebuffer as fb

# Create benchmark runner
runner = fb_benchmark.BenchmarkRunner(
    width=200,
    height=100,
    format=fb.MONO_VLSB
)

# Run all benchmarks
runner.run_all_benchmarks()
```

### Individual Operation Benchmark

Benchmark a specific operation:

```python
runner = fb_benchmark.BenchmarkRunner(width=200, height=100)

# Benchmark horizontal lines
runner.benchmark_operation(
    name="hline test",
    setup_func=lambda fb, buf: lambda: fb.hline(0, 50, 200, 1),
    iterations=1000
)
```

## Example Output

```
============================================================
# FRAMEBUFFER PERFORMANCE BENCHMARK SUITE
# Resolution: 200x100
# Format: MONO_VLSB
# Buffer size: 5000 bytes
============================================================

============================================================
Benchmarking: hline() - horizontal line
============================================================
Iterations: 1000

Results:
  C (built-in):          12500 µs  (baseline)
  Viper:                 45000 µs  (0.28x)
  Native:                52000 µs  (0.24x)

Output verification: ✓ PASS

...

============================================================
# BENCHMARK SUMMARY
============================================================

Test                                     C (µs)       Viper        Native       V-Speed    N-Speed    Match
------------------------------------------------------------------------------------------------------------------------
hline() - horizontal line                12500        45000        52000        0.28       0.24       ✓
...
------------------------------------------------------------------------------------------------------------------------
AVERAGE SPEEDUP:                                                                0.32       0.28

Overall verification: ✓ ALL TESTS PASSED
```

## Understanding Results

### Speedup Values

- **> 1.0x**: Pure Python implementation is faster (rare but possible for simple ops)
- **< 1.0x**: C implementation is faster (expected for most operations)
- **~0.3-0.5x**: Typical range for viper-optimized code
- **~0.2-0.4x**: Typical range for native-optimized code

### Why C is Usually Faster

The built-in C framebuffer is typically faster because:
1. Direct memory access without Python overhead
2. Optimized C compiler output
3. No type checking or bounds checking overhead
4. Better CPU cache utilization

### When Python Might Be Competitive

Pure Python implementations can be competitive for:
- Very simple operations (single pixel writes)
- Small framebuffers where setup overhead dominates
- Operations that are memory-bound rather than CPU-bound

## Hardware Compatibility

This benchmark is designed for:
- **RP2040** (Raspberry Pi Pico)
- **RP2350** (Raspberry Pi Pico 2)
- **ESP32** series
- Any MicroPython platform with framebuffer support

## Customization

### Adding New Tests

Add custom benchmark tests:

```python
def my_custom_test(fb, buf):
    def operation():
        # Your custom drawing code
        fb.fill(0)
        fb.rect(10, 10, 50, 50, 1)
        fb.line(0, 0, 100, 50, 1)
    return operation

runner.benchmark_operation(
    name="My Custom Test",
    setup_func=my_custom_test,
    iterations=500
)
```

### Testing Different Sizes

```python
# Small framebuffer (minimal memory)
runner = fb_benchmark.BenchmarkRunner(20, 20, fb.MONO_VLSB)
runner.run_all_benchmarks()

# Medium framebuffer
runner = fb_benchmark.BenchmarkRunner(128, 64, fb.MONO_VLSB)
runner.run_all_benchmarks()

# Large framebuffer
runner = fb_benchmark.BenchmarkRunner(320, 240, fb.RGB565)
runner.run_all_benchmarks()
```

## Memory Requirements

Approximate memory usage per configuration:

| Resolution | MONO_VLSB | RGB565  | GS8    |
|------------|-----------|---------|--------|
| 20x20      | 80 bytes  | 800 B   | 400 B  |
| 128x64     | 1 KB      | 16 KB   | 8 KB   |
| 200x100    | 2.5 KB    | 40 KB   | 20 KB  |
| 320x240    | 9.6 KB    | 150 KB  | 75 KB  |

Note: The benchmark creates 3 framebuffers simultaneously (C, Viper, Native), so multiply by 3 for total memory usage.

## Performance Tips

When using pure Python framebuffers in production:

1. **Use `@micropython.viper`** for best performance
2. **Batch operations** - use `hline`/`vline` instead of individual pixels
3. **Minimize bounds checking** - know your safe regions
4. **Profile first** - the C module is usually fast enough
5. **Consider native for code clarity** - if performance is acceptable

## License

Public domain / MIT - use freely in your projects!

## Contributing

Found a bug or want to add tests? Contributions welcome!
