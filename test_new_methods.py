"""
Test script for new framebuf methods on MicroPython hardware
Tests: line, text, scroll, ellipse, poly
"""

import framebuf as framebuf_c
import framebufpy as framebuf_py

def hex_dump(buf, width=16):
    """Pretty print buffer as hex dump"""
    for i in range(0, min(len(buf), 128), width):
        hex_str = ' '.join('%02x' % b for b in buf[i:i+width])
        print('%04x: %s' % (i, hex_str))

def compare_buffers(buf1, buf2, test_name):
    """Compare two buffers"""
    if buf1 == buf2:
        print("✓ PASS:", test_name)
        return True
    else:
        print("✗ FAIL:", test_name)
        # Find first difference
        for i in range(min(len(buf1), len(buf2))):
            if buf1[i] != buf2[i]:
                print("  First diff at byte %d: 0x%02x vs 0x%02x" % (i, buf1[i], buf2[i]))
                break
        print("  C implementation:")
        hex_dump(buf1)
        print("  Python implementation:")
        hex_dump(buf2)
        return False

# Test 1: line() - basic horizontal line
print("\n=== Test 1: line() - horizontal ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

fb_c.line(0, 5, 15, 5, 1)
fb_py.line(0, 5, 15, 5, 1)
compare_buffers(buf_c, buf_py, "line() horizontal")

# Test 2: line() - diagonal
print("\n=== Test 2: line() - diagonal ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

fb_c.line(0, 0, 15, 15, 1)
fb_py.line(0, 0, 15, 15, 1)
compare_buffers(buf_c, buf_py, "line() diagonal")

# Test 3: line() - all 8 octants
print("\n=== Test 3: line() - all octants ===")
buf_c = bytearray(160)
fb_c = framebuf_c.FrameBuffer(buf_c, 32, 32, framebuf_c.MONO_VLSB)
buf_py = bytearray(160)
fb_py = framebuf_py.FrameBuffer(buf_py, 32, 32, framebuf_py.MONO_VLSB)

cx, cy = 16, 16
lines = [
    (cx, cy, cx + 10, cy + 3),
    (cx, cy, cx + 3, cy + 10),
    (cx, cy, cx - 3, cy + 10),
    (cx, cy, cx - 10, cy + 3),
    (cx, cy, cx - 10, cy - 3),
    (cx, cy, cx - 3, cy - 10),
    (cx, cy, cx + 3, cy - 10),
    (cx, cy, cx + 10, cy - 3),
]
for x1, y1, x2, y2 in lines:
    fb_c.line(x1, y1, x2, y2, 1)
    fb_py.line(x1, y1, x2, y2, 1)
compare_buffers(buf_c, buf_py, "line() all octants")

# Test 4: text() - basic string
print("\n=== Test 4: text() - basic string ===")
buf_c = bytearray(200)
fb_c = framebuf_c.FrameBuffer(buf_c, 40, 32, framebuf_c.MONO_VLSB)
buf_py = bytearray(200)
fb_py = framebuf_py.FrameBuffer(buf_py, 40, 32, framebuf_py.MONO_VLSB)

fb_c.text("Hi", 0, 0, 1)
fb_py.text("Hi", 0, 0, 1)
compare_buffers(buf_c, buf_py, "text() basic")

# Test 5: text() - longer string
print("\n=== Test 5: text() - longer string ===")
buf_c = bytearray(200)
fb_c = framebuf_c.FrameBuffer(buf_c, 40, 32, framebuf_c.MONO_VLSB)
buf_py = bytearray(200)
fb_py = framebuf_py.FrameBuffer(buf_py, 40, 32, framebuf_py.MONO_VLSB)

fb_c.text("Test!", 5, 10, 1)
fb_py.text("Test!", 5, 10, 1)
compare_buffers(buf_c, buf_py, "text() longer")

# Test 6: scroll() - scroll right
print("\n=== Test 6: scroll() - right ===")
buf_c = bytearray(40)
fb_c = framebuf_c.FrameBuffer(buf_c, 10, 10, framebuf_c.MONO_VLSB)
buf_py = bytearray(40)
fb_py = framebuf_py.FrameBuffer(buf_py, 10, 10, framebuf_py.MONO_VLSB)

# Draw a pattern first
fb_c.fill_rect(0, 0, 5, 5, 1)
fb_py.fill_rect(0, 0, 5, 5, 1)
# Scroll it
fb_c.scroll(2, 0)
fb_py.scroll(2, 0)
compare_buffers(buf_c, buf_py, "scroll() right")

# Test 7: scroll() - scroll down
print("\n=== Test 7: scroll() - down ===")
buf_c = bytearray(40)
fb_c = framebuf_c.FrameBuffer(buf_c, 10, 10, framebuf_c.MONO_VLSB)
buf_py = bytearray(40)
fb_py = framebuf_py.FrameBuffer(buf_py, 10, 10, framebuf_py.MONO_VLSB)

fb_c.fill_rect(0, 0, 5, 3, 1)
fb_py.fill_rect(0, 0, 5, 3, 1)
fb_c.scroll(0, 2)
fb_py.scroll(0, 2)
compare_buffers(buf_c, buf_py, "scroll() down")

# Test 8: ellipse() - circle
print("\n=== Test 8: ellipse() - circle ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

fb_c.ellipse(10, 10, 5, 5, 1)
fb_py.ellipse(10, 10, 5, 5, 1)
compare_buffers(buf_c, buf_py, "ellipse() circle outline")

# Test 9: ellipse() - filled ellipse
print("\n=== Test 9: ellipse() - filled ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

fb_c.ellipse(10, 10, 6, 4, 1, True)
fb_py.ellipse(10, 10, 6, 4, 1, True)
compare_buffers(buf_c, buf_py, "ellipse() filled")

# Test 10: poly() - triangle outline
print("\n=== Test 10: poly() - triangle outline ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

from array import array
coords = array('h', [0, 0, 10, 0, 5, 10])
fb_c.poly(5, 5, coords, 1)
fb_py.poly(5, 5, coords, 1)
compare_buffers(buf_c, buf_py, "poly() triangle outline")

# Test 11: poly() - filled triangle
print("\n=== Test 11: poly() - triangle filled ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

coords = array('h', [0, 0, 10, 0, 5, 10])
fb_c.poly(5, 5, coords, 1, True)
fb_py.poly(5, 5, coords, 1, True)
compare_buffers(buf_c, buf_py, "poly() triangle filled")

# Test 12: poly() - square filled
print("\n=== Test 12: poly() - square filled ===")
buf_c = bytearray(80)
fb_c = framebuf_c.FrameBuffer(buf_c, 20, 20, framebuf_c.MONO_VLSB)
buf_py = bytearray(80)
fb_py = framebuf_py.FrameBuffer(buf_py, 20, 20, framebuf_py.MONO_VLSB)

coords = array('h', [0, 0, 8, 0, 8, 8, 0, 8])
fb_c.poly(5, 5, coords, 1, True)
fb_py.poly(5, 5, coords, 1, True)
compare_buffers(buf_c, buf_py, "poly() square filled")

print("\n=== All tests complete! ===")
