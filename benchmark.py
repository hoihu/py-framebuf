"""
Comprehensive framebuf benchmark - C vs Pure Python (viper)

Tests all operations across multiple formats:
- Basic ops: pixel, hline, vline, fill, fill_rect, blit
- New methods: line, text, scroll, ellipse, poly
"""

import time
import framebuf
import framebufpy as framebuf_pure
from array import array

def benchmark(func, iterations=100):
    """Run function multiple times and return average time in microseconds"""
    start = time.ticks_us()
    for _ in range(iterations):
        func()
    end = time.ticks_us()
    return time.ticks_diff(end, start) / iterations

def format_time(us):
    """Format microseconds to readable string"""
    if us < 1000:
        return "%d µs" % int(us)
    elif us < 1000000:
        return "%.1f ms" % (us/1000)
    else:
        return "%.2f s" % (us/1000000)

def print_result(name, time_c, time_py):
    """Print benchmark result"""
    ratio = time_py / time_c
    print("  %-30s C: %10s  Py: %10s  (%.2fx)" % (
        name, format_time(time_c), format_time(time_py), ratio))

# =============================================================================
# MONO_VLSB 128x64 - Common OLED display format
# =============================================================================
print("\n" + "="*70)
print("MONO_VLSB 128x64 (SSD1306 OLED)")
print("="*70)

w, h = 128, 64
size = ((h + 7) // 8) * w
buf_c = bytearray(size)
buf_py = bytearray(size)
fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)
fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

print()
print_result("fill(1)",
    benchmark(lambda: fb_c.fill(1), 100),
    benchmark(lambda: fb_py.fill(1), 100))

print_result("pixel(50, 30, 1)",
    benchmark(lambda: fb_c.pixel(50, 30, 1), 1000),
    benchmark(lambda: fb_py.pixel(50, 30, 1), 1000))

print_result("hline(0, 32, 128, 1)",
    benchmark(lambda: fb_c.hline(0, 32, 128, 1), 500),
    benchmark(lambda: fb_py.hline(0, 32, 128, 1), 500))

print_result("vline(64, 0, 64, 1)",
    benchmark(lambda: fb_c.vline(64, 0, 64, 1), 500),
    benchmark(lambda: fb_py.vline(64, 0, 64, 1), 500))

print_result("fill_rect(10, 10, 50, 30, 1)",
    benchmark(lambda: fb_c.fill_rect(10, 10, 50, 30, 1), 200),
    benchmark(lambda: fb_py.fill_rect(10, 10, 50, 30, 1), 200))

# Blit test
sprite_buf_c = bytearray(8)
sprite_buf_py = bytearray(8)
sprite_c = framebuf.FrameBuffer(sprite_buf_c, 8, 8, framebuf.MONO_VLSB)
sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 8, 8, framebuf_pure.MONO_VLSB)
sprite_c.fill(1)
sprite_py.fill(1)

print_result("blit(sprite_8x8, 60, 28)",
    benchmark(lambda: fb_c.blit(sprite_c, 60, 28), 100),
    benchmark(lambda: fb_py.blit(sprite_py, 60, 28), 100))

print_result("line(0, 0, 127, 63, 1)",
    benchmark(lambda: fb_c.line(0, 0, 127, 63, 1), 25),
    benchmark(lambda: fb_py.line(0, 0, 127, 63, 1), 25))

print_result("text('Hello!', 10, 10, 1)",
    benchmark(lambda: fb_c.text("Hello!", 10, 10, 1), 15),
    benchmark(lambda: fb_py.text("Hello!", 10, 10, 1), 15))

print_result("scroll(1, 0)",
    benchmark(lambda: fb_c.scroll(1, 0), 2),
    benchmark(lambda: fb_py.scroll(1, 0), 2))

print_result("ellipse(64, 32, 30, 20, 1)",
    benchmark(lambda: fb_c.ellipse(64, 32, 30, 20, 1), 15),
    benchmark(lambda: fb_py.ellipse(64, 32, 30, 20, 1), 15))

print_result("ellipse(..., filled)",
    benchmark(lambda: fb_c.ellipse(64, 32, 30, 20, 1, True), 15),
    benchmark(lambda: fb_py.ellipse(64, 32, 30, 20, 1, True), 15))

coords = array('h', [0, 0, 40, 0, 20, 30])
print_result("poly(triangle, outline)",
    benchmark(lambda: fb_c.poly(50, 20, coords, 1), 15),
    benchmark(lambda: fb_py.poly(50, 20, coords, 1), 15))

print_result("poly(triangle, filled)",
    benchmark(lambda: fb_c.poly(50, 20, coords, 1, True), 15),
    benchmark(lambda: fb_py.poly(50, 20, coords, 1, True), 15))

# =============================================================================
# RGB565 128x64 - Color display
# =============================================================================
print("\n" + "="*70)
print("RGB565 128x64 (Color Display)")
print("="*70)

size = w * h * 2
buf_c = bytearray(size)
buf_py = bytearray(size)
fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.RGB565)
fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

print()
print_result("fill(0xFFFF)",
    benchmark(lambda: fb_c.fill(0xFFFF), 25),
    benchmark(lambda: fb_py.fill(0xFFFF), 25))

print_result("pixel(50, 30, 0xF800)",
    benchmark(lambda: fb_c.pixel(50, 30, 0xF800), 1000),
    benchmark(lambda: fb_py.pixel(50, 30, 0xF800), 1000))

print_result("hline(0, 32, 100, 0x07E0)",
    benchmark(lambda: fb_c.hline(0, 32, 100, 0x07E0), 300),
    benchmark(lambda: fb_py.hline(0, 32, 100, 0x07E0), 300))

print_result("vline(64, 0, 50, 0x001F)",
    benchmark(lambda: fb_c.vline(64, 0, 50, 0x001F), 300),
    benchmark(lambda: fb_py.vline(64, 0, 50, 0x001F), 300))

print_result("fill_rect(10, 10, 50, 30, 0xF800)",
    benchmark(lambda: fb_c.fill_rect(10, 10, 50, 30, 0xF800), 100),
    benchmark(lambda: fb_py.fill_rect(10, 10, 50, 30, 0xF800), 100))

# Blit test
sprite_buf_c = bytearray(8 * 8 * 2)
sprite_buf_py = bytearray(8 * 8 * 2)
sprite_c = framebuf.FrameBuffer(sprite_buf_c, 8, 8, framebuf.RGB565)
sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 8, 8, framebuf_pure.RGB565)
sprite_c.fill(0xFFFF)
sprite_py.fill(0xFFFF)

print_result("blit(sprite_8x8, 60, 28)",
    benchmark(lambda: fb_c.blit(sprite_c, 60, 28), 100),
    benchmark(lambda: fb_py.blit(sprite_py, 60, 28), 100))

print_result("line(0, 0, 127, 63, 0xF800)",
    benchmark(lambda: fb_c.line(0, 0, 127, 63, 0xF800), 25),
    benchmark(lambda: fb_py.line(0, 0, 127, 63, 0xF800), 25))

print_result("text('Hello!', 10, 10, 0x07E0)",
    benchmark(lambda: fb_c.text("Hello!", 10, 10, 0x07E0), 15),
    benchmark(lambda: fb_py.text("Hello!", 10, 10, 0x07E0), 15))

print_result("scroll(1, 0)",
    benchmark(lambda: fb_c.scroll(1, 0), 2),
    benchmark(lambda: fb_py.scroll(1, 0), 2))

print_result("ellipse(64, 32, 30, 20, 0x001F)",
    benchmark(lambda: fb_c.ellipse(64, 32, 30, 20, 0x001F), 15),
    benchmark(lambda: fb_py.ellipse(64, 32, 30, 20, 0x001F), 15))

print_result("ellipse(..., filled)",
    benchmark(lambda: fb_c.ellipse(64, 32, 30, 20, 0xFFE0, True), 15),
    benchmark(lambda: fb_py.ellipse(64, 32, 30, 20, 0xFFE0, True), 15))

coords = array('h', [0, 0, 40, 0, 20, 30])
print_result("poly(triangle, outline)",
    benchmark(lambda: fb_c.poly(50, 20, coords, 0xF800), 15),
    benchmark(lambda: fb_py.poly(50, 20, coords, 0xF800), 15))

print_result("poly(triangle, filled)",
    benchmark(lambda: fb_c.poly(50, 20, coords, 0x07E0, True), 15),
    benchmark(lambda: fb_py.poly(50, 20, coords, 0x07E0, True), 15))

# =============================================================================
# GS8 128x64 - 8-bit grayscale
# =============================================================================
print("\n" + "="*70)
print("GS8 128x64 (8-bit Grayscale)")
print("="*70)

size = w * h
buf_c = bytearray(size)
buf_py = bytearray(size)
fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS8)
fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

print()
print_result("fill(128)",
    benchmark(lambda: fb_c.fill(128), 25),
    benchmark(lambda: fb_py.fill(128), 25))

print_result("pixel(50, 30, 255)",
    benchmark(lambda: fb_c.pixel(50, 30, 255), 1000),
    benchmark(lambda: fb_py.pixel(50, 30, 255), 1000))

print_result("hline(0, 32, 100, 200)",
    benchmark(lambda: fb_c.hline(0, 32, 100, 200), 300),
    benchmark(lambda: fb_py.hline(0, 32, 100, 200), 300))

print_result("vline(64, 0, 50, 150)",
    benchmark(lambda: fb_c.vline(64, 0, 50, 150), 300),
    benchmark(lambda: fb_py.vline(64, 0, 50, 150), 300))

print_result("fill_rect(10, 10, 50, 30, 64)",
    benchmark(lambda: fb_c.fill_rect(10, 10, 50, 30, 64), 100),
    benchmark(lambda: fb_py.fill_rect(10, 10, 50, 30, 64), 100))

# Blit test
sprite_buf_c = bytearray(8 * 8)
sprite_buf_py = bytearray(8 * 8)
sprite_c = framebuf.FrameBuffer(sprite_buf_c, 8, 8, framebuf.GS8)
sprite_py = framebuf_pure.FrameBuffer(sprite_buf_py, 8, 8, framebuf_pure.GS8)
sprite_c.fill(255)
sprite_py.fill(255)

print_result("blit(sprite_8x8, 60, 28)",
    benchmark(lambda: fb_c.blit(sprite_c, 60, 28), 100),
    benchmark(lambda: fb_py.blit(sprite_py, 60, 28), 100))

print_result("line(0, 0, 127, 63, 200)",
    benchmark(lambda: fb_c.line(0, 0, 127, 63, 200), 25),
    benchmark(lambda: fb_py.line(0, 0, 127, 63, 200), 25))

print_result("text('Hello!', 10, 10, 255)",
    benchmark(lambda: fb_c.text("Hello!", 10, 10, 255), 15),
    benchmark(lambda: fb_py.text("Hello!", 10, 10, 255), 15))

print_result("scroll(1, 0)",
    benchmark(lambda: fb_c.scroll(1, 0), 2),
    benchmark(lambda: fb_py.scroll(1, 0), 2))

print_result("ellipse(64, 32, 30, 20, 180)",
    benchmark(lambda: fb_c.ellipse(64, 32, 30, 20, 180), 15),
    benchmark(lambda: fb_py.ellipse(64, 32, 30, 20, 180), 15))

print_result("ellipse(..., filled)",
    benchmark(lambda: fb_c.ellipse(64, 32, 30, 20, 220, True), 15),
    benchmark(lambda: fb_py.ellipse(64, 32, 30, 20, 220, True), 15))

coords = array('h', [0, 0, 40, 0, 20, 30])
print_result("poly(triangle, outline)",
    benchmark(lambda: fb_c.poly(50, 20, coords, 200), 15),
    benchmark(lambda: fb_py.poly(50, 20, coords, 200), 15))

print_result("poly(triangle, filled)",
    benchmark(lambda: fb_c.poly(50, 20, coords, 150, True), 15),
    benchmark(lambda: fb_py.poly(50, 20, coords, 150, True), 15))

print("\n" + "="*70)
print("Benchmark Complete!")
print("="*70)
