"""
Performance benchmark comparing C framebuf vs pure Python viper implementation

Tests common operations on realistic display sizes:
- MONO_VLSB 128x64 (SSD1306 OLED)
- RGB565 64x64 (Color display)
- GS8 128x128 (Grayscale display)
- MONO_HLSB 128x64 (Horizontal layout)
"""

import time
import framebuf
import framebuf_pure

# Global list to collect all benchmark results
results = []

# Helper function to measure execution time
def benchmark(func, iterations=100):
    """Run function multiple times and return average time in microseconds"""
    start = time.ticks_us()
    for _ in range(iterations):
        func()
    end = time.ticks_us()
    elapsed = time.ticks_diff(end, start)
    return elapsed / iterations


def format_time(us):
    """Format microseconds to readable string"""
    if us < 1000:
        return f"{us:.1f} µs"
    elif us < 1000000:
        return f"{us/1000:.1f} ms"
    else:
        return f"{us/1000000:.2f} s"


def benchmark_mono_vlsb():
    """Benchmark MONO_VLSB 128x64 (SSD1306 display)"""
    print("\n" + "="*70)
    print("MONO_VLSB 128x64 (SSD1306 OLED Display)")
    print("="*70)

    w, h = 128, 64
    size = ((h + 7) // 8) * w  # 1024 bytes

    # Create buffers
    buf_c = bytearray(size)
    buf_py = bytearray(size)

    fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    print(f"Buffer size: {size} bytes\n")

    # Benchmark fill
    print("Operation: fill(1)")
    time_c = benchmark(lambda: fb_c.fill(1), 100)
    time_py = benchmark(lambda: fb_py.fill(1), 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "fill(1)", time_c, time_py, ratio))

    # Benchmark horizontal line
    print("\nOperation: hline(0, 32, 128, 1)")
    time_c = benchmark(lambda: fb_c.hline(0, 32, 128, 1), 1000)
    time_py = benchmark(lambda: fb_py.hline(0, 32, 128, 1), 1000)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "hline", time_c, time_py, ratio))

    # Benchmark vertical line
    print("\nOperation: vline(64, 0, 64, 1)")
    time_c = benchmark(lambda: fb_c.vline(64, 0, 64, 1), 1000)
    time_py = benchmark(lambda: fb_py.vline(64, 0, 64, 1), 1000)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "vline", time_c, time_py, ratio))

    # Benchmark pixel set (1000 random pixels)
    print("\nOperation: 100x pixel(x, y, 1) - scattered pixels")
    def set_pixels_c():
        for i in range(100):
            fb_c.pixel((i * 37) % 128, (i * 23) % 64, 1)

    def set_pixels_py():
        for i in range(100):
            fb_py.pixel((i * 37) % 128, (i * 23) % 64, 1)

    time_c = benchmark(set_pixels_c, 100)
    time_py = benchmark(set_pixels_py, 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "pixel_set", time_c, time_py, ratio))

    # Benchmark pixel read
    print("\nOperation: 100x pixel(x, y) - read pixels")
    def read_pixels_c():
        total = 0
        for i in range(100):
            total += fb_c.pixel((i * 37) % 128, (i * 23) % 64)  # C: 2 args = GET
        return total

    def read_pixels_py():
        total = 0
        for i in range(100):
            total += fb_py.pixel((i * 37) % 128, (i * 23) % 64, -1)  # Viper: 3rd arg -1 = GET
        return total

    time_c = benchmark(read_pixels_c, 100)
    time_py = benchmark(read_pixels_py, 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "pixel_get", time_c, time_py, ratio))

    # Benchmark blit - 8x8 sprite
    print("\nOperation: blit(sprite_8x8, x, y) - copy 8x8 sprite")
    sprite_size = ((8 + 7) // 8) * 8
    sprite_buf_c = bytearray(sprite_size)
    sprite_buf_py = bytearray(sprite_size)
    sprite_c = framebuf.FrameBuffer(sprite_buf_c, 8, 8, framebuf.MONO_VLSB)
    sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 8, 8, framebuf_pure.MONO_VLSB)
    sprite_c.fill(1)
    sprite_py.fill(1)

    time_c = benchmark(lambda: fb_c.blit(sprite_c, 60, 28), 500)
    time_py = benchmark(lambda: fb_py.blit(sprite_py, 60, 28), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "blit_8x8", time_c, time_py, ratio))

    # Benchmark blit with transparency
    print("\nOperation: blit(sprite_8x8, x, y, key=0) - with transparency")
    time_c = benchmark(lambda: fb_c.blit(sprite_c, 60, 28, 0), 500)
    time_py = benchmark(lambda: fb_py.blit(sprite_py, 60, 28, 0), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_VLSB", "blit_key", time_c, time_py, ratio))


def benchmark_rgb565():
    """Benchmark RGB565 64x64 (Color display)"""
    print("\n" + "="*70)
    print("RGB565 64x64 (Color Display)")
    print("="*70)

    w, h = 64, 64
    size = w * h * 2  # 8,192 bytes

    # Create buffers
    buf_c = bytearray(size)
    buf_py = bytearray(size)

    fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.RGB565)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    print(f"Buffer size: {size} bytes\n")

    # Benchmark fill
    print("Operation: fill(0xF800) - red")
    time_c = benchmark(lambda: fb_c.fill(0xF800), 100)
    time_py = benchmark(lambda: fb_py.fill(0xF800), 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("RGB565", "fill", time_c, time_py, ratio))

    # Benchmark horizontal line
    print("\nOperation: hline(0, 32, 64, 0x07E0) - green line")
    time_c = benchmark(lambda: fb_c.hline(0, 32, 64, 0x07E0), 500)
    time_py = benchmark(lambda: fb_py.hline(0, 32, 64, 0x07E0), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("RGB565", "hline", time_c, time_py, ratio))

    # Benchmark vertical line
    print("\nOperation: vline(32, 0, 64, 0x001F) - blue line")
    time_c = benchmark(lambda: fb_c.vline(32, 0, 64, 0x001F), 500)
    time_py = benchmark(lambda: fb_py.vline(32, 0, 64, 0x001F), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("RGB565", "vline", time_c, time_py, ratio))

    # Benchmark pixel operations
    print("\nOperation: 100x pixel(x, y, color) - scattered pixels")
    def set_pixels_c():
        for i in range(100):
            fb_c.pixel((i * 37) % 64, (i * 47) % 64, 0xFFFF)

    def set_pixels_py():
        for i in range(100):
            fb_py.pixel((i * 37) % 64, (i * 47) % 64, 0xFFFF)

    time_c = benchmark(set_pixels_c, 100)
    time_py = benchmark(set_pixels_py, 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("RGB565", "pixel_set", time_c, time_py, ratio))

    # Benchmark blit - 16x16 sprite
    print("\nOperation: blit(sprite_16x16, x, y) - copy 16x16 sprite")
    sprite_size = 16 * 16 * 2
    sprite_buf_c = bytearray(sprite_size)
    sprite_buf_py = bytearray(sprite_size)
    sprite_c = framebuf.FrameBuffer(sprite_buf_c, 16, 16, framebuf.RGB565)
    sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 16, 16, framebuf_pure.RGB565)
    sprite_c.fill(0x07E0)  # Green
    sprite_py.fill(0x07E0)

    time_c = benchmark(lambda: fb_c.blit(sprite_c, 24, 24), 300)
    time_py = benchmark(lambda: fb_py.blit(sprite_py, 24, 24), 300)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("RGB565", "blit_16x16", time_c, time_py, ratio))

    # Benchmark cross-format blit with palette (MONO -> RGB565)
    print("\nOperation: blit(mono_8x8, palette) - cross-format with palette")
    mono_size = ((8 + 7) // 8) * 8
    mono_buf_c = bytearray(mono_size)
    mono_buf_py = bytearray(mono_size)
    mono_c = framebuf.FrameBuffer(mono_buf_c, 8, 8, framebuf.MONO_HLSB)
    mono_py = framebuf_pure.FrameBuffer(mono_buf_py, 8, 8, framebuf_pure.MONO_HLSB)
    mono_c.fill(1)
    mono_py.fill(1)

    # Create palette (2 colors for monochrome)
    pal_buf_c = bytearray(2 * 2)
    pal_buf_py = bytearray(2 * 2)
    pal_c = framebuf.FrameBuffer(pal_buf_c, 2, 1, framebuf.RGB565)
    pal_py = framebuf_pure.FrameBuffer(pal_buf_py, 2, 1, framebuf_pure.RGB565)
    pal_c.pixel(0, 0, 0x0000)  # Black
    pal_c.pixel(1, 0, 0xF800)  # Red
    pal_py.pixel(0, 0, 0x0000)
    pal_py.pixel(1, 0, 0xF800)

    time_c = benchmark(lambda: fb_c.blit(mono_c, 28, 28, -1, pal_c), 300)
    time_py = benchmark(lambda: fb_py.blit(mono_py, 28, 28, -1, pal_py), 300)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("RGB565", "blit_palette", time_c, time_py, ratio))


def benchmark_gs8():
    """Benchmark GS8 128x128 (Grayscale display)"""
    print("\n" + "="*70)
    print("GS8 128x128 (8-bit Grayscale Display)")
    print("="*70)

    w, h = 128, 128
    size = w * h  # 16,384 bytes

    # Create buffers
    buf_c = bytearray(size)
    buf_py = bytearray(size)

    fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS8)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    print(f"Buffer size: {size} bytes\n")

    # Benchmark fill
    print("Operation: fill(128)")
    time_c = benchmark(lambda: fb_c.fill(128), 50)
    time_py = benchmark(lambda: fb_py.fill(128), 50)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("GS8", "fill", time_c, time_py, ratio))

    # Benchmark horizontal line
    print("\nOperation: hline(0, 64, 128, 255)")
    time_c = benchmark(lambda: fb_c.hline(0, 64, 128, 255), 500)
    time_py = benchmark(lambda: fb_py.hline(0, 64, 128, 255), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("GS8", "hline", time_c, time_py, ratio))

    # Benchmark vertical line
    print("\nOperation: vline(64, 0, 128, 200)")
    time_c = benchmark(lambda: fb_c.vline(64, 0, 128, 200), 500)
    time_py = benchmark(lambda: fb_py.vline(64, 0, 128, 200), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("GS8", "vline", time_c, time_py, ratio))

    # Benchmark pixel operations
    print("\nOperation: 100x pixel(x, y, gray) - scattered pixels")
    def set_pixels_c():
        for i in range(100):
            fb_c.pixel((i * 67) % 128, (i * 97) % 128, i % 256)

    def set_pixels_py():
        for i in range(100):
            fb_py.pixel((i * 67) % 128, (i * 97) % 128, i % 256)

    time_c = benchmark(set_pixels_c, 100)
    time_py = benchmark(set_pixels_py, 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("GS8", "pixel_set", time_c, time_py, ratio))

    # Benchmark blit - 16x16 sprite
    print("\nOperation: blit(sprite_16x16, x, y) - copy 16x16 sprite")
    sprite_size = 16 * 16
    sprite_buf_c = bytearray(sprite_size)
    sprite_buf_py = bytearray(sprite_size)
    sprite_c = framebuf.FrameBuffer(sprite_buf_c, 16, 16, framebuf.GS8)
    sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 16, 16, framebuf_pure.GS8)
    sprite_c.fill(200)
    sprite_py.fill(200)

    time_c = benchmark(lambda: fb_c.blit(sprite_c, 56, 56), 300)
    time_py = benchmark(lambda: fb_py.blit(sprite_py, 56, 56), 300)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("GS8", "blit_16x16", time_c, time_py, ratio))


def benchmark_mono_hlsb():
    """Benchmark MONO_HLSB 128x64"""
    print("\n" + "="*70)
    print("MONO_HLSB 128x64 (Horizontal layout)")
    print("="*70)

    w, h = 128, 64
    size = ((w + 7) // 8) * h  # 1024 bytes

    # Create buffers
    buf_c = bytearray(size)
    buf_py = bytearray(size)

    fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HLSB)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    print(f"Buffer size: {size} bytes\n")

    # Benchmark fill
    print("Operation: fill(1)")
    time_c = benchmark(lambda: fb_c.fill(1), 100)
    time_py = benchmark(lambda: fb_py.fill(1), 100)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_HLSB", "fill(1)", time_c, time_py, ratio))

    # Benchmark horizontal line (byte-spanning case - most complex)
    print("\nOperation: hline(5, 32, 118, 1) - byte spanning")
    time_c = benchmark(lambda: fb_c.hline(5, 32, 118, 1), 1000)
    time_py = benchmark(lambda: fb_py.hline(5, 32, 118, 1), 1000)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_HLSB", "hline", time_c, time_py, ratio))

    # Benchmark blit - 8x8 sprite
    print("\nOperation: blit(sprite_8x8, x, y) - copy 8x8 sprite")
    sprite_size = ((8 + 7) // 8) * 8
    sprite_buf_c = bytearray(sprite_size)
    sprite_buf_py = bytearray(sprite_size)
    sprite_c = framebuf.FrameBuffer(sprite_buf_c, 8, 8, framebuf.MONO_HLSB)
    sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 8, 8, framebuf_pure.MONO_HLSB)
    sprite_c.fill(1)
    sprite_py.fill(1)

    time_c = benchmark(lambda: fb_c.blit(sprite_c, 60, 28), 500)
    time_py = benchmark(lambda: fb_py.blit(sprite_py, 60, 28), 500)
    ratio = time_py / time_c
    print(f"  C impl:     {format_time(time_c)}")
    print(f"  Viper impl: {format_time(time_py)}")
    print(f"  Ratio:      {ratio:.2f}x {'slower' if ratio > 1 else 'faster'}")
    results.append(("MONO_HLSB", "blit_8x8", time_c, time_py, ratio))


def print_summary_table():
    """Print summary table of all benchmark results"""
    print("\n" + "="*70)
    print("PERFORMANCE SUMMARY TABLE")
    print("="*70)
    print(f"{'Format':<12} {'Operation':<12} {'C (µs)':<12} {'Viper (µs)':<12} {'Ratio':>8}")
    print("-"*70)

    for fmt, op, time_c, time_py, ratio in results:
        c_str = f"{time_c:.1f}" if time_c < 1000 else f"{time_c/1000:.1f}ms"
        py_str = f"{time_py:.1f}" if time_py < 1000 else f"{time_py/1000:.1f}ms"
        ratio_str = f"{ratio:.2f}x"
        print(f"{fmt:<12} {op:<12} {c_str:<12} {py_str:<12} {ratio_str:>8}")

    print("="*70)
    print("\nKey:")
    print("  Ratio < 1.0 = Viper is FASTER than C")
    print("  Ratio > 1.0 = Viper is SLOWER than C")
    print("="*70)


def run_all_benchmarks():
    """Run all benchmark suites"""
    global results
    results = []  # Reset results list

    print("\n" + "="*70)
    print("MicroPython FrameBuf Performance Benchmark")
    print("Comparing C implementation vs Pure Python Viper implementation")
    print("="*70)

    # Run benchmarks for each format
    benchmark_mono_vlsb()

    # RGB565 with memory-safe size
    try:
        benchmark_rgb565()
    except MemoryError:
        print("\n⚠ Skipping RGB565 64x64 - insufficient memory")

    try:
        benchmark_gs8()
    except MemoryError:
        print("\n⚠ Skipping GS8 128x128 - insufficient memory")

    benchmark_mono_hlsb()

    # Print summary table
    print_summary_table()

    print("\n" + "="*70)
    print("Benchmark Complete")
    print("="*70)
    print("\nNotes:")
    print("- Lower ratio is better (closer to C performance)")
    print("- Viper optimizations significantly improve pure Python speed")
    print("- Fill operations are memory-bandwidth limited")
    print("- Line operations benefit from loop optimization")
    print("- Blit operations are pixel-by-pixel, performance depends on sprite size")
    print("- Cross-format blit with palette involves extra color translation")
    print("="*70)


if __name__ == "__main__":
    run_all_benchmarks()
