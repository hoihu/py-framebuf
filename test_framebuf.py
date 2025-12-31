"""
Test suite for pure-Python framebuf implementation

Tests each format against the built-in C implementation
to ensure byte-for-byte compatibility.
"""

# Import C implementation
import framebuf as framebuf_c

# Import our pure Python implementation (renamed to framebufpy to avoid conflict)
import framebufpy as framebuf_pure


def hex_dump(buf, width=16):
    """Pretty print buffer as hex dump"""
    for i in range(0, len(buf), width):
        hex_str = ' '.join(f'{b:02x}' for b in buf[i:i+width])
        print(f'{i:04x}: {hex_str}')


def compare_buffers(buf1, buf2, test_name):
    """Compare two buffers and report differences"""
    if buf1 == buf2:
        return True

    print(f"\n❌ FAILED: {test_name}")
    print(f"Buffers differ! Length: {len(buf1)} vs {len(buf2)}")

    # Find first difference
    for i in range(min(len(buf1), len(buf2))):
        if buf1[i] != buf2[i]:
            print(f"First difference at byte {i}: 0x{buf1[i]:02x} vs 0x{buf2[i]:02x}")
            break

    print("\nC implementation buffer:")
    hex_dump(buf1)
    print("\nPure Python buffer:")
    hex_dump(buf2)

    return False


# ========================================================================
# MONO_VLSB Tests
# ========================================================================

def test_mono_vlsb_pixel_set():
    """Test MONO_VLSB pixel set operations"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w  # 4 * 20 = 80 bytes

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test single pixel
    fb_c.pixel(0, 0, 1)
    fb_py.pixel(0, 0, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB pixel(0, 0, 1)"):
        return False

    # Test multiple pixels
    test_pixels = [(5, 5, 1), (10, 15, 1), (19, 31, 1), (0, 7, 1), (0, 8, 1)]
    for x, y, c in test_pixels:
        fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB multiple pixels"):
        return False

    print("✓ MONO_VLSB pixel set test passed")
    return True


def test_mono_vlsb_pixel_get():
    """Test MONO_VLSB pixel get operations"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Set some pixels
    test_pixels = [(5, 5, 1), (10, 15, 1), (19, 31, 1)]
    for x, y, c in test_pixels:
        fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    # Read them back
    for x, y, expected in test_pixels:
        val_c = fb_c.pixel(x, y)
        val_py = fb_py.pixel(x, y, -1)
        if val_c != val_py:
            print(f"❌ FAILED: pixel({x}, {y}) returned {val_py}, expected {val_c}")
            return False
        if val_c != expected:
            print(f"❌ FAILED: pixel({x}, {y}) returned {val_c}, expected {expected}")
            return False

    print("✓ MONO_VLSB pixel get test passed")
    return True


def test_mono_vlsb_hline():
    """Test MONO_VLSB horizontal line"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test hline across full width
    fb_c.hline(0, 5, w, 1)
    fb_py.hline(0, 5, w, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB hline(0, 5, 20, 1)"):
        return False

    # Test hline partial
    fb_c.hline(5, 10, 10, 1)
    fb_py.hline(5, 10, 10, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB hline(5, 10, 10, 1)"):
        return False

    # Test hline with clear
    fb_c.hline(5, 10, 5, 0)
    fb_py.hline(5, 10, 5, 0)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB hline clear"):
        return False

    print("✓ MONO_VLSB hline test passed")
    return True


def test_mono_vlsb_vline():
    """Test MONO_VLSB vertical line"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test vline across full height
    fb_c.vline(5, 0, h, 1)
    fb_py.vline(5, 0, h, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB vline(5, 0, 32, 1)"):
        return False

    # Test vline partial
    fb_c.vline(10, 5, 10, 1)
    fb_py.vline(10, 5, 10, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB vline(10, 5, 10, 1)"):
        return False

    # Test vline spanning byte boundaries (y=6 to y=10 crosses byte boundary at y=8)
    fb_c.vline(15, 6, 5, 1)
    fb_py.vline(15, 6, 5, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB vline byte boundary"):
        return False

    print("✓ MONO_VLSB vline test passed")
    return True


def test_mono_vlsb_fill():
    """Test MONO_VLSB fill"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    # Test fill with 1
    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)
    fb_c.fill(1)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)
    fb_py.fill(1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB fill(1)"):
        return False

    # Test fill with 0
    fb_c.fill(0)
    fb_py.fill(0)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB fill(0)"):
        return False

    # Test with non-multiple-of-8 height
    h2 = 25  # Not a multiple of 8
    size2 = ((h2 + 7) // 8) * w

    buf_c2 = bytearray(size2)
    fb_c2 = framebuf_c.FrameBuffer(buf_c2, w, h2, framebuf_c.MONO_VLSB)
    fb_c2.fill(1)

    buf_py2 = bytearray(size2)
    fb_py2 = framebuf_pure.FrameBuffer(buf_py2, w, h2, framebuf_pure.MONO_VLSB)
    fb_py2.fill(1)

    if not compare_buffers(buf_c2, buf_py2, "MONO_VLSB fill partial height"):
        return False

    print("✓ MONO_VLSB fill test passed")
    return True


def test_mono_vlsb_edge_cases():
    """Test MONO_VLSB edge cases"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test clipping - pixel outside bounds
    fb_c.pixel(-1, 5, 1)
    fb_c.pixel(25, 5, 1)
    fb_c.pixel(5, -1, 1)
    fb_c.pixel(5, 35, 1)

    fb_py.pixel(-1, 5, 1)
    fb_py.pixel(25, 5, 1)
    fb_py.pixel(5, -1, 1)
    fb_py.pixel(5, 35, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB pixel clipping"):
        return False

    # Test hline clipping
    fb_c.hline(-5, 10, 10, 1)  # Starts before buffer, should clip
    fb_c.hline(15, 10, 10, 1)  # Extends past buffer, should clip

    fb_py.hline(-5, 10, 10, 1)
    fb_py.hline(15, 10, 10, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB hline clipping"):
        return False

    # Test vline clipping
    fb_c.vline(10, -5, 10, 1)  # Starts before buffer, should clip
    fb_c.vline(10, 25, 10, 1)  # Extends past buffer, should clip

    fb_py.vline(10, -5, 10, 1)
    fb_py.vline(10, 25, 10, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB vline clipping"):
        return False

    print("✓ MONO_VLSB edge cases test passed")
    return True


def test_mono_vlsb_realistic_size():
    """Test MONO_VLSB with realistic 128x64 display size (SSD1306)"""
    w, h = 128, 64
    size = ((h + 7) // 8) * w  # 8 * 128 = 1024 bytes

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test fill
    fb_c.fill(1)
    fb_py.fill(1)

    if not compare_buffers(buf_c, buf_py, "128x64 fill"):
        return False

    # Test horizontal line across full width
    fb_c.fill(0)
    fb_c.hline(0, 32, w, 1)
    fb_py.fill(0)
    fb_py.hline(0, 32, w, 1)

    if not compare_buffers(buf_c, buf_py, "128x64 hline"):
        return False

    # Test vertical line down full height
    fb_c.fill(0)
    fb_c.vline(64, 0, h, 1)
    fb_py.fill(0)
    fb_py.vline(64, 0, h, 1)

    if not compare_buffers(buf_c, buf_py, "128x64 vline"):
        return False

    # Test some pixels
    fb_c.fill(0)
    fb_c.pixel(0, 0, 1)
    fb_c.pixel(127, 63, 1)
    fb_c.pixel(64, 32, 1)
    fb_py.fill(0)
    fb_py.pixel(0, 0, 1)
    fb_py.pixel(127, 63, 1)
    fb_py.pixel(64, 32, 1)

    if not compare_buffers(buf_c, buf_py, "128x64 pixels"):
        return False

    print("✓ MONO_VLSB 128x64 realistic size test passed")
    return True


# ========================================================================
# RGB565 Tests
# ========================================================================

def test_rgb565_pixel():
    """Test RGB565 pixel operations"""
    w, h = 10, 10
    size = w * h * 2  # 2 bytes per pixel

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.RGB565)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    # Test some RGB565 colors
    colors = [
        0xF800,  # Red (11111 000000 00000)
        0x07E0,  # Green (00000 111111 00000)
        0x001F,  # Blue (00000 000000 11111)
        0xFFFF,  # White
        0x0000,  # Black
        0xF81F,  # Magenta
    ]

    for i, color in enumerate(colors):
        x, y = i % w, i // w
        fb_c.pixel(x, y, color)
        fb_py.pixel(x, y, color)

    if not compare_buffers(buf_c, buf_py, "RGB565 pixel set"):
        return False

    # Test pixel get
    for i, color in enumerate(colors):
        x, y = i % w, i // w
        val_c = fb_c.pixel(x, y)
        val_py = fb_py.pixel(x, y, -1)
        if val_c != val_py or val_c != color:
            print(f"❌ FAILED: RGB565 pixel({x}, {y}) get mismatch")
            return False
        if val_c != color:
            print(f"❌ FAILED: RGB565 pixel({x}, {y}) returned {val_py:04x}, expected {color:04x}")
            return False

    print("✓ RGB565 pixel test passed")
    return True


def test_rgb565_hline():
    """Test RGB565 horizontal line"""
    w, h = 20, 10
    size = w * h * 2

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.RGB565)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    # Test hline with red color
    fb_c.hline(0, 5, w, 0xF800)
    fb_py.hline(0, 5, w, 0xF800)

    if not compare_buffers(buf_c, buf_py, "RGB565 hline"):
        return False

    print("✓ RGB565 hline test passed")
    return True


def test_rgb565_vline():
    """Test RGB565 vertical line"""
    w, h = 20, 10
    size = w * h * 2

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.RGB565)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    # Test vline with green color
    fb_c.vline(5, 0, h, 0x07E0)
    fb_py.vline(5, 0, h, 0x07E0)

    if not compare_buffers(buf_c, buf_py, "RGB565 vline"):
        return False

    print("✓ RGB565 vline test passed")
    return True


def test_rgb565_fill():
    """Test RGB565 fill"""
    w, h = 10, 10
    size = w * h * 2

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.RGB565)
    fb_c.fill(0x001F)  # Blue

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)
    fb_py.fill(0x001F)

    if not compare_buffers(buf_c, buf_py, "RGB565 fill"):
        return False

    print("✓ RGB565 fill test passed")
    return True


# ========================================================================
# GS8 Tests
# ========================================================================

def test_gs8_pixel():
    """Test GS8 pixel operations"""
    w, h = 10, 10
    size = w * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    # Test grayscale values
    grays = [0, 64, 128, 192, 255]

    for i, gray in enumerate(grays):
        x, y = i % w, i // w
        fb_c.pixel(x, y, gray)
        fb_py.pixel(x, y, gray)

    if not compare_buffers(buf_c, buf_py, "GS8 pixel set"):
        return False

    # Test pixel get
    for i, gray in enumerate(grays):
        x, y = i % w, i // w
        val_c = fb_c.pixel(x, y)
        val_py = fb_py.pixel(x, y, -1)
        if val_c != val_py or val_c != gray:
            print(f"❌ FAILED: GS8 pixel({x}, {y}) get mismatch")
            return False
        if val_c != gray:
            print(f"❌ FAILED: GS8 pixel({x}, {y}) returned {val_py}, expected {gray}")
            return False

    print("✓ GS8 pixel test passed")
    return True


def test_gs8_hline():
    """Test GS8 horizontal line"""
    w, h = 20, 10
    size = w * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    fb_c.hline(0, 5, w, 128)
    fb_py.hline(0, 5, w, 128)

    if not compare_buffers(buf_c, buf_py, "GS8 hline"):
        return False

    print("✓ GS8 hline test passed")
    return True


def test_gs8_vline():
    """Test GS8 vertical line"""
    w, h = 20, 10
    size = w * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    fb_c.vline(5, 0, h, 192)
    fb_py.vline(5, 0, h, 192)

    if not compare_buffers(buf_c, buf_py, "GS8 vline"):
        return False

    print("✓ GS8 vline test passed")
    return True


def test_gs8_fill():
    """Test GS8 fill"""
    w, h = 10, 10
    size = w * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)
    fb_c.fill(200)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)
    fb_py.fill(200)

    if not compare_buffers(buf_c, buf_py, "GS8 fill"):
        return False

    print("✓ GS8 fill test passed")
    return True


# ========================================================================
# MONO_HLSB Tests
# ========================================================================

def test_mono_hlsb_pixel():
    """Test MONO_HLSB pixel operations"""
    w, h = 16, 10  # 16 = 2 bytes wide
    size = ((w + 7) // 8) * h  # 2 * 10 = 20 bytes

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    # Test pixels across byte boundary
    test_pixels = [(0, 0, 1), (7, 0, 1), (8, 0, 1), (15, 0, 1), (5, 5, 1)]
    for x, y, c in test_pixels:
        fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    if not compare_buffers(buf_c, buf_py, "MONO_HLSB pixel set"):
        return False

    print("✓ MONO_HLSB pixel test passed")
    return True


def test_mono_hlsb_hline():
    """Test MONO_HLSB horizontal line - critical for byte spanning"""
    w, h = 24, 10  # 24 = 3 bytes wide
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    # Test hline within single byte
    fb_c.hline(1, 0, 3, 1)
    fb_py.hline(1, 0, 3, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HLSB hline single byte"):
        return False

    # Test hline spanning two bytes
    fb_c.hline(5, 1, 6, 1)  # Crosses byte boundary at x=8
    fb_py.hline(5, 1, 6, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HLSB hline two bytes"):
        return False

    # Test hline spanning three bytes
    fb_c.hline(6, 2, 12, 1)  # Crosses two byte boundaries
    fb_py.hline(6, 2, 12, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HLSB hline three bytes"):
        return False

    print("✓ MONO_HLSB hline test passed")
    return True


def test_mono_hlsb_vline():
    """Test MONO_HLSB vertical line"""
    w, h = 16, 20
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    fb_c.vline(5, 0, h, 1)
    fb_py.vline(5, 0, h, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HLSB vline"):
        return False

    print("✓ MONO_HLSB vline test passed")
    return True


def test_mono_hlsb_fill():
    """Test MONO_HLSB fill"""
    w, h = 13, 10  # Non-multiple of 8 to test partial byte handling
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HLSB)
    fb_c.fill(1)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)
    fb_py.fill(1)

    if not compare_buffers(buf_c, buf_py, "MONO_HLSB fill(1)"):
        return False

    print("✓ MONO_HLSB fill test passed")
    return True


# ========================================================================
# MONO_HMSB Tests
# ========================================================================

def test_mono_hmsb_pixel():
    """Test MONO_HMSB pixel operations"""
    w, h = 16, 10
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)

    # Test pixels across byte boundary
    test_pixels = [(0, 0, 1), (7, 0, 1), (8, 0, 1), (15, 0, 1), (5, 5, 1)]
    for x, y, c in test_pixels:
        fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    if not compare_buffers(buf_c, buf_py, "MONO_HMSB pixel set"):
        return False

    print("✓ MONO_HMSB pixel test passed")
    return True


def test_mono_hmsb_hline():
    """Test MONO_HMSB horizontal line - critical for byte spanning"""
    w, h = 24, 10
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)

    # Test hline within single byte
    fb_c.hline(1, 0, 3, 1)
    fb_py.hline(1, 0, 3, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HMSB hline single byte"):
        return False

    # Test hline spanning two bytes
    fb_c.hline(5, 1, 6, 1)
    fb_py.hline(5, 1, 6, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HMSB hline two bytes"):
        return False

    # Test hline spanning three bytes
    fb_c.hline(6, 2, 12, 1)
    fb_py.hline(6, 2, 12, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HMSB hline three bytes"):
        return False

    print("✓ MONO_HMSB hline test passed")
    return True


def test_mono_hmsb_vline():
    """Test MONO_HMSB vertical line"""
    w, h = 16, 20
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)

    fb_c.vline(5, 0, h, 1)
    fb_py.vline(5, 0, h, 1)

    if not compare_buffers(buf_c, buf_py, "MONO_HMSB vline"):
        return False

    print("✓ MONO_HMSB vline test passed")
    return True


def test_mono_hmsb_fill():
    """Test MONO_HMSB fill"""
    w, h = 13, 10  # Non-multiple of 8
    size = ((w + 7) // 8) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_HMSB)
    fb_c.fill(1)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)
    fb_py.fill(1)

    if not compare_buffers(buf_c, buf_py, "MONO_HMSB fill(1)"):
        return False

    print("✓ MONO_HMSB fill test passed")
    return True


# ========================================================================
# GS4_HMSB Tests
# ========================================================================

def test_gs4_hmsb_pixel():
    """Test GS4_HMSB pixel operations"""
    w, h = 10, 10
    size = ((w + 1) // 2) * h  # 5 * 10 = 50 bytes

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS4_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)

    # Test various 4-bit values (0-15)
    values = [0, 3, 7, 10, 15]
    for i, val in enumerate(values):
        x, y = i % w, i // w
        fb_c.pixel(x, y, val)
        fb_py.pixel(x, y, val)

    if not compare_buffers(buf_c, buf_py, "GS4_HMSB pixel set"):
        return False

    # Test pixel get
    for i, val in enumerate(values):
        x, y = i % w, i // w
        val_c = fb_c.pixel(x, y)
        val_py = fb_py.pixel(x, y, -1)
        if val_c != val_py or val_c != val:
            print(f"❌ FAILED: GS4_HMSB pixel({x}, {y}) get mismatch")
            return False
        if val_c != val:
            print(f"❌ FAILED: GS4_HMSB pixel({x}, {y}) returned {val_py}, expected {val}")
            return False

    print("✓ GS4_HMSB pixel test passed")
    return True


def test_gs4_hmsb_hline():
    """Test GS4_HMSB horizontal line"""
    w, h = 20, 10
    size = ((w + 1) // 2) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS4_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)

    # Test hline with even and odd alignments
    fb_c.hline(0, 5, w, 8)  # Even start
    fb_py.hline(0, 5, w, 8)

    if not compare_buffers(buf_c, buf_py, "GS4_HMSB hline even"):
        return False

    # Odd start, odd width
    fb_c.hline(1, 3, 7, 12)
    fb_py.hline(1, 3, 7, 12)

    if not compare_buffers(buf_c, buf_py, "GS4_HMSB hline odd"):
        return False

    print("✓ GS4_HMSB hline test passed")
    return True


def test_gs4_hmsb_vline():
    """Test GS4_HMSB vertical line"""
    w, h = 20, 10
    size = ((w + 1) // 2) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS4_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)

    fb_c.vline(5, 0, h, 9)
    fb_py.vline(5, 0, h, 9)

    if not compare_buffers(buf_c, buf_py, "GS4_HMSB vline"):
        return False

    print("✓ GS4_HMSB vline test passed")
    return True


def test_gs4_hmsb_fill():
    """Test GS4_HMSB fill"""
    w, h = 10, 10
    size = ((w + 1) // 2) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS4_HMSB)
    fb_c.fill(11)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)
    fb_py.fill(11)

    if not compare_buffers(buf_c, buf_py, "GS4_HMSB fill"):
        return False

    print("✓ GS4_HMSB fill test passed")
    return True


# ========================================================================
# GS2_HMSB Tests
# ========================================================================

def test_gs2_hmsb_pixel():
    """Test GS2_HMSB pixel operations"""
    w, h = 12, 8
    size = ((w + 3) // 4) * h  # 3 * 8 = 24 bytes

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS2_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)

    # Test all 2-bit values (0-3)
    values = [0, 1, 2, 3]
    for i, val in enumerate(values):
        x, y = i % w, i // w
        fb_c.pixel(x, y, val)
        fb_py.pixel(x, y, val)

    if not compare_buffers(buf_c, buf_py, "GS2_HMSB pixel set"):
        return False

    # Test pixel get
    for i, val in enumerate(values):
        x, y = i % w, i // w
        val_c = fb_c.pixel(x, y)
        val_py = fb_py.pixel(x, y, -1)
        if val_c != val_py or val_c != val:
            print(f"❌ FAILED: GS2_HMSB pixel({x}, {y}) get mismatch")
            return False
        if val_c != val:
            print(f"❌ FAILED: GS2_HMSB pixel({x}, {y}) returned {val_py}, expected {val}")
            return False

    print("✓ GS2_HMSB pixel test passed")
    return True


def test_gs2_hmsb_hline():
    """Test GS2_HMSB horizontal line"""
    w, h = 16, 8
    size = ((w + 3) // 4) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS2_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)

    fb_c.hline(0, 4, w, 2)
    fb_py.hline(0, 4, w, 2)

    if not compare_buffers(buf_c, buf_py, "GS2_HMSB hline"):
        return False

    print("✓ GS2_HMSB hline test passed")
    return True


def test_gs2_hmsb_vline():
    """Test GS2_HMSB vertical line"""
    w, h = 16, 8
    size = ((w + 3) // 4) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS2_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)

    fb_c.vline(7, 0, h, 3)
    fb_py.vline(7, 0, h, 3)

    if not compare_buffers(buf_c, buf_py, "GS2_HMSB vline"):
        return False

    print("✓ GS2_HMSB vline test passed")
    return True


def test_gs2_hmsb_fill():
    """Test GS2_HMSB fill"""
    w, h = 12, 8
    size = ((w + 3) // 4) * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS2_HMSB)
    fb_c.fill(2)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)
    fb_py.fill(2)

    if not compare_buffers(buf_c, buf_py, "GS2_HMSB fill"):
        return False

    print("✓ GS2_HMSB fill test passed")
    return True


# ========================================================================
# Test Runner
# ========================================================================

def run_mono_vlsb_tests():
    """Run all MONO_VLSB tests"""
    print("\n" + "="*60)
    print("Testing MONO_VLSB Format")
    print("="*60)

    tests = [
        test_mono_vlsb_pixel_set,
        test_mono_vlsb_pixel_get,
        test_mono_vlsb_hline,
        test_mono_vlsb_vline,
        test_mono_vlsb_fill,
        test_mono_vlsb_edge_cases,
        test_mono_vlsb_realistic_size,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_rgb565_tests():
    """Run all RGB565 tests"""
    print("\n" + "="*60)
    print("Testing RGB565 Format")
    print("="*60)

    tests = [
        test_rgb565_pixel,
        test_rgb565_hline,
        test_rgb565_vline,
        test_rgb565_fill,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_gs8_tests():
    """Run all GS8 tests"""
    print("\n" + "="*60)
    print("Testing GS8 Format")
    print("="*60)

    tests = [
        test_gs8_pixel,
        test_gs8_hline,
        test_gs8_vline,
        test_gs8_fill,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_mono_hlsb_tests():
    """Run all MONO_HLSB tests"""
    print("\n" + "="*60)
    print("Testing MONO_HLSB Format")
    print("="*60)

    tests = [
        test_mono_hlsb_pixel,
        test_mono_hlsb_hline,
        test_mono_hlsb_vline,
        test_mono_hlsb_fill,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_mono_hmsb_tests():
    """Run all MONO_HMSB tests"""
    print("\n" + "="*60)
    print("Testing MONO_HMSB Format")
    print("="*60)

    tests = [
        test_mono_hmsb_pixel,
        test_mono_hmsb_hline,
        test_mono_hmsb_vline,
        test_mono_hmsb_fill,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_gs4_hmsb_tests():
    """Run all GS4_HMSB tests"""
    print("\n" + "="*60)
    print("Testing GS4_HMSB Format")
    print("="*60)

    tests = [
        test_gs4_hmsb_pixel,
        test_gs4_hmsb_hline,
        test_gs4_hmsb_vline,
        test_gs4_hmsb_fill,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_gs2_hmsb_tests():
    """Run all GS2_HMSB tests"""
    print("\n" + "="*60)
    print("Testing GS2_HMSB Format")
    print("="*60)

    tests = [
        test_gs2_hmsb_pixel,
        test_gs2_hmsb_hline,
        test_gs2_hmsb_vline,
        test_gs2_hmsb_fill,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


# ========================================================================
# Blit Tests
# ========================================================================

def test_blit_gs8_basic():
    """Test basic GS8 blit operations"""
    w, h = 5, 4
    buf_py = bytearray(w * h)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    # Create a 2x2 source filled with 0xFF
    fbuf2_py = framebuf_pure.FrameBuffer(bytearray(4), 2, 2, framebuf_pure.GS8)
    fbuf2_py.fill(0xFF)

    buf_c = bytearray(w * h)
    fbuf_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)
    fbuf2_c = framebuf_c.FrameBuffer(bytearray(4), 2, 2, framebuf_c.GS8)
    fbuf2_c.fill(0xFF)

    # Test blit at various positions
    test_positions = [(-1, -1), (0, 0), (1, 1), (4, 3)]

    for x, y in test_positions:
        fbuf_py.fill(0)
        fbuf_py.blit(fbuf2_py, x, y)

        fbuf_c.fill(0)
        fbuf_c.blit(fbuf2_c, x, y)
        if not compare_buffers(buf_c, buf_py, f"blit GS8 at ({x}, {y})"):
            return False

    return True


def test_blit_tuple_source():
    """Test blit from tuple source"""
    w, h = 5, 4
    buf_py = bytearray(w * h)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    buf_c = bytearray(w * h)
    fbuf_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    # Blit a bytes object
    fbuf_py.fill(0)
    image = (b"\x10\x11\x12\x13", 2, 2, framebuf_pure.GS8)
    fbuf_py.blit(image, 1, 1)

    fbuf_c.fill(0)
    image_c = (b"\x10\x11\x12\x13", 2, 2, framebuf_c.GS8)
    fbuf_c.blit(image_c, 1, 1)
    if not compare_buffers(buf_c, buf_py, "blit from tuple"):
        return False

    return True


def test_blit_tuple_with_stride():
    """Test blit from tuple with stride"""
    w, h = 5, 4
    buf_py = bytearray(w * h)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    buf_c = bytearray(w * h)
    fbuf_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    # Blit a bytes object with stride (2x2 image with stride=3)
    fbuf_py.fill(0)
    image = (b"\x20\x21\xff\x22\x23\xff", 2, 2, framebuf_pure.GS8, 3)
    fbuf_py.blit(image, 1, 1)

    fbuf_c.fill(0)
    image_c = (b"\x20\x21\xff\x22\x23\xff", 2, 2, framebuf_c.GS8, 3)
    fbuf_c.blit(image_c, 1, 1)
    if not compare_buffers(buf_c, buf_py, "blit with stride"):
        return False

    return True


def test_blit_with_palette():
    """Test blit with palette color translation"""
    w, h = 5, 4
    buf_py = bytearray(w * h)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    buf_c = bytearray(w * h)
    fbuf_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    # Blit with palette
    fbuf_py.fill(0)
    image = (b"\x00\x01\x01\x00", 2, 2, framebuf_pure.GS8)
    palette = (b"\xa1\xa2", 2, 1, framebuf_pure.GS8)
    fbuf_py.blit(image, 1, 1, -1, palette)

    fbuf_c.fill(0)
    image_c = (b"\x00\x01\x01\x00", 2, 2, framebuf_c.GS8)
    palette_c = (b"\xa1\xa2", 2, 1, framebuf_c.GS8)
    fbuf_c.blit(image_c, 1, 1, -1, palette_c)
    if not compare_buffers(buf_c, buf_py, "blit with palette"):
        return False

    return True


def test_blit_cross_format_palette():
    """Test blit between MONO_HLSB and RGB565 with palette"""
    # Create MONO_HLSB source (8x8)
    w, h = 8, 8
    src_buf_py = bytearray(w * h // 8)
    src_py = framebuf_pure.FrameBuffer(src_buf_py, w, h, framebuf_pure.MONO_HLSB)
    src_py.pixel(0, 0, 1)
    src_py.pixel(7, 7, 1)
    src_py.pixel(3, 3, 1)

    # Create RGB565 destination (16x16)
    wd, hd = 16, 16
    dest_buf_py = bytearray(wd * hd * 2)
    dest_py = framebuf_pure.FrameBuffer(dest_buf_py, wd, hd, framebuf_pure.RGB565)

    # Create RGB565 palette (2 colors for monochrome)
    bg = 0x1234
    fg = 0xF800
    pal_buf_py = bytearray(2 * 2)  # 2 pixels * 2 bytes
    palette_py = framebuf_pure.FrameBuffer(pal_buf_py, 2, 1, framebuf_pure.RGB565)
    palette_py.pixel(0, 0, bg)
    palette_py.pixel(1, 0, fg)

    # Blit with palette
    dest_py.blit(src_py, 0, 0, -1, palette_py)

    # Verify pixels
    if dest_py.pixel(0, 0, -1) != fg:
        print(f"❌ Expected pixel(0,0)={fg:04x}, got {dest_py.pixel(0, 0, -1):04x}")
        return False
    if dest_py.pixel(7, 7, -1) != fg:
        print(f"❌ Expected pixel(7,7)={fg:04x}, got {dest_py.pixel(7, 7, -1):04x}")
        return False
    if dest_py.pixel(3, 3, -1) != fg:
        print(f"❌ Expected pixel(3,3)={fg:04x}, got {dest_py.pixel(3, 3, -1):04x}")
        return False
    if dest_py.pixel(0, 1, -1) != bg:
        print(f"❌ Expected pixel(0,1)={bg:04x}, got {dest_py.pixel(0, 1, -1):04x}")
        return False
    if dest_py.pixel(8, 8, -1) != 0:
        print(f"❌ Expected pixel(8,8)=0000, got {dest_py.pixel(8, 8, -1):04x}")
        return False

    # Compare with C implementation
    src_buf_c = bytearray(w * h // 8)
    src_c = framebuf_c.FrameBuffer(src_buf_c, w, h, framebuf_c.MONO_HLSB)
    src_c.pixel(0, 0, 1)
    src_c.pixel(7, 7, 1)
    src_c.pixel(3, 3, 1)

    dest_buf_c = bytearray(wd * hd * 2)
    dest_c = framebuf_c.FrameBuffer(dest_buf_c, wd, hd, framebuf_c.RGB565)

    pal_buf_c = bytearray(2 * 2)
    palette_c = framebuf_c.FrameBuffer(pal_buf_c, 2, 1, framebuf_c.RGB565)
    palette_c.pixel(0, 0, bg)
    palette_c.pixel(1, 0, fg)

    dest_c.blit(src_c, 0, 0, -1, palette_c)

    if not compare_buffers(dest_buf_c, dest_buf_py, "cross-format blit with palette"):
        return False

    return True


def test_blit_mono_hmsb_to_rgb565():
    """Test optimized MONO_HMSB to RGB565 blit with palette (text/icon rendering)"""
    # Create MONO_HMSB source (8x8) - horizontal MSB format (typical for text)
    w, h = 8, 8
    src_buf_py = bytearray(w * h // 8)
    src_py = framebuf_pure.FrameBuffer(src_buf_py, w, h, framebuf_pure.MONO_HMSB)

    # Draw a diagonal line
    src_py.pixel(0, 0, 1)
    src_py.pixel(1, 1, 1)
    src_py.pixel(2, 2, 1)
    src_py.pixel(7, 7, 1)

    # Create RGB565 destination (16x16)
    wd, hd = 16, 16
    dest_buf_py = bytearray(wd * hd * 2)
    dest_py = framebuf_pure.FrameBuffer(dest_buf_py, wd, hd, framebuf_pure.RGB565)

    # Create RGB565 palette (2 colors for monochrome)
    bg = 0x0000  # Black background
    fg = 0xFFFF  # White foreground
    pal_buf_py = bytearray(2 * 2)  # 2 pixels * 2 bytes
    palette_py = framebuf_pure.FrameBuffer(pal_buf_py, 2, 1, framebuf_pure.RGB565)
    palette_py.pixel(0, 0, bg)
    palette_py.pixel(1, 0, fg)

    # Blit with palette (should use optimized path)
    dest_py.blit(src_py, 0, 0, -1, palette_py)

    # Verify foreground pixels
    if dest_py.pixel(0, 0, -1) != fg:
        print(f"❌ Expected pixel(0,0)={fg:04x}, got {dest_py.pixel(0, 0, -1):04x}")
        return False
    if dest_py.pixel(1, 1, -1) != fg:
        print(f"❌ Expected pixel(1,1)={fg:04x}, got {dest_py.pixel(1, 1, -1):04x}")
        return False
    if dest_py.pixel(2, 2, -1) != fg:
        print(f"❌ Expected pixel(2,2)={fg:04x}, got {dest_py.pixel(2, 2, -1):04x}")
        return False
    if dest_py.pixel(7, 7, -1) != fg:
        print(f"❌ Expected pixel(7,7)={fg:04x}, got {dest_py.pixel(7, 7, -1):04x}")
        return False

    # Verify background pixels
    if dest_py.pixel(0, 1, -1) != bg:
        print(f"❌ Expected pixel(0,1)={bg:04x}, got {dest_py.pixel(0, 1, -1):04x}")
        return False
    if dest_py.pixel(3, 3, -1) != bg:
        print(f"❌ Expected pixel(3,3)={bg:04x}, got {dest_py.pixel(3, 3, -1):04x}")
        return False

    # Verify pixels outside blit area are still 0
    if dest_py.pixel(8, 8, -1) != 0:
        print(f"❌ Expected pixel(8,8)=0000, got {dest_py.pixel(8, 8, -1):04x}")
        return False

    # Compare with C implementation
    src_buf_c = bytearray(w * h // 8)
    src_c = framebuf_c.FrameBuffer(src_buf_c, w, h, framebuf_c.MONO_HMSB)
    src_c.pixel(0, 0, 1)
    src_c.pixel(1, 1, 1)
    src_c.pixel(2, 2, 1)
    src_c.pixel(7, 7, 1)

    dest_buf_c = bytearray(wd * hd * 2)
    dest_c = framebuf_c.FrameBuffer(dest_buf_c, wd, hd, framebuf_c.RGB565)

    pal_buf_c = bytearray(2 * 2)
    palette_c = framebuf_c.FrameBuffer(pal_buf_c, 2, 1, framebuf_c.RGB565)
    palette_c.pixel(0, 0, bg)
    palette_c.pixel(1, 0, fg)

    dest_c.blit(src_c, 0, 0, -1, palette_c)

    if not compare_buffers(dest_buf_c, dest_buf_py, "MONO_HMSB->RGB565 palette blit"):
        return False

    return True


def test_blit_transparency():
    """Test blit with transparency key"""
    w, h = 8, 8
    buf_py = bytearray(w * h)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)
    fbuf_py.fill(0x55)

    # Create source with alternating pattern
    src_buf = bytearray([0xFF if (i + j) % 2 == 0 else 0x00 for j in range(4) for i in range(4)])
    src_py = framebuf_pure.FrameBuffer(src_buf, 4, 4, framebuf_pure.GS8)

    # Blit with transparency (skip 0x00 pixels)
    fbuf_py.blit(src_py, 2, 2, 0x00)

    buf_c = bytearray(w * h)
    fbuf_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)
    fbuf_c.fill(0x55)

    src_c = framebuf_c.FrameBuffer(bytearray(src_buf), 4, 4, framebuf_c.GS8)
    fbuf_c.blit(src_c, 2, 2, 0x00)

    if not compare_buffers(buf_c, buf_py, "blit with transparency"):
        return False

    return True


def test_blit_mono_vlsb():
    """Test MONO_VLSB blit"""
    w, h = 10, 16
    size = ((h + 7) // 8) * w

    buf_py = bytearray(size)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Create 4x8 source
    src_size = ((8 + 7) // 8) * 4
    src_buf = bytearray(src_size)
    src_py = framebuf_pure.FrameBuffer(src_buf, 4, 8, framebuf_pure.MONO_VLSB)
    src_py.fill(1)

    # Blit source
    fbuf_py.blit(src_py, 2, 4)

    # Verify pixels in blitted region
    for y in range(4, 12):
        for x in range(2, 6):
            if fbuf_py.pixel(x, y, -1) != 1:
                print(f"❌ Expected pixel({x},{y})=1, got {fbuf_py.pixel(x, y, -1)}")
                return False

    buf_c = bytearray(size)
    fbuf_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)
    src_c = framebuf_c.FrameBuffer(bytearray(src_size), 4, 8, framebuf_c.MONO_VLSB)
    src_c.fill(1)
    fbuf_c.blit(src_c, 2, 4)

    if not compare_buffers(buf_c, buf_py, "MONO_VLSB blit"):
        return False

    return True


def test_blit_error_cases():
    """Test error cases for blit"""
    w, h = 5, 4
    fbuf = framebuf_pure.FrameBuffer(bytearray(w * h), w, h, framebuf_pure.GS8)

    # Not enough elements in tuple
    try:
        fbuf.blit((0, 0, 0), 0, 0)
        print("❌ Should have raised ValueError for short tuple")
        return False
    except ValueError:
        pass  # Expected

    # Too many elements in tuple
    try:
        fbuf.blit((0, 0, 0, 0, 0, 0), 0, 0)
        print("❌ Should have raised ValueError for long tuple")
        return False
    except ValueError:
        pass  # Expected

    # Bytes too small
    try:
        fbuf.blit((b"", 1, 1, framebuf_pure.GS8), 0, 0)
        print("❌ Should have raised ValueError for insufficient buffer")
        return False
    except ValueError:
        pass  # Expected

    # Invalid palette height
    try:
        pal = framebuf_pure.FrameBuffer(bytearray(4), 2, 2, framebuf_pure.GS8)
        fbuf.blit((b"\x00\x00", 1, 2, framebuf_pure.GS8), 0, 0, -1, pal)
        print("❌ Should have raised ValueError for palette height != 1")
        return False
    except ValueError:
        pass  # Expected

    return True


def test_blit_out_of_bounds():
    """Test blit completely out of bounds (should no-op)"""
    w, h = 5, 4
    buf_py = bytearray(w * h)
    fbuf_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)
    fbuf_py.fill(0x55)

    src = framebuf_pure.FrameBuffer(bytearray(4), 2, 2, framebuf_pure.GS8)
    src.fill(0xFF)

    # Save original state
    original = bytearray(buf_py)

    # Blit completely out of bounds - should be no-op
    fbuf_py.blit(src, 10, 10)
    fbuf_py.blit(src, -5, -5)
    fbuf_py.blit(src, 100, 0)
    fbuf_py.blit(src, 0, 100)

    # Buffer should be unchanged
    if buf_py != original:
        print("❌ Buffer changed after out-of-bounds blit")
        return False

    return True


def run_blit_tests():
    """Run blit tests"""
    print("\n" + "="*60)
    print("BLIT TESTS")
    print("="*60)

    tests = [
        test_blit_gs8_basic,
        test_blit_tuple_source,
        test_blit_tuple_with_stride,
        test_blit_with_palette,
        test_blit_cross_format_palette,
        test_blit_mono_hmsb_to_rgb565,
        test_blit_transparency,
        test_blit_mono_vlsb,
        test_blit_error_cases,
        test_blit_out_of_bounds,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            print(f"\nRunning {test.__name__}...", end=" ")
            if test():
                print("✅ PASSED")
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {test.__name__}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


# ========================================================================
# Line Tests
# ========================================================================

def test_line_basic():
    """Test basic line drawing (horizontal, vertical, diagonal)"""
    w, h = 20, 20
    size = ((h + 7) // 8) * w  # MONO_VLSB format

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Horizontal line
    fb_c.line(0, 5, 15, 5, 1)
    fb_py.line(0, 5, 15, 5, 1)

    if not compare_buffers(buf_c, buf_py, "line() horizontal"):
        return False

    # Vertical line
    fb_c.line(10, 0, 10, 15, 1)
    fb_py.line(10, 0, 10, 15, 1)

    if not compare_buffers(buf_c, buf_py, "line() vertical"):
        return False

    # Diagonal line (45 degrees)
    fb_c.line(0, 0, 10, 10, 1)
    fb_py.line(0, 0, 10, 10, 1)

    if not compare_buffers(buf_c, buf_py, "line() diagonal 45°"):
        return False

    print("✓ line() basic test passed")
    return True


def test_line_all_octants():
    """Test line drawing in all 8 octants"""
    w, h = 40, 40
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    cx, cy = 20, 20  # Center point

    # All 8 octants from center
    test_lines = [
        (cx, cy, cx + 10, cy + 3),   # Octant 0: East, shallow
        (cx, cy, cx + 3, cy + 10),   # Octant 1: North-East, steep
        (cx, cy, cx - 3, cy + 10),   # Octant 2: North-West, steep
        (cx, cy, cx - 10, cy + 3),   # Octant 3: West, shallow
        (cx, cy, cx - 10, cy - 3),   # Octant 4: West, shallow down
        (cx, cy, cx - 3, cy - 10),   # Octant 5: South-West, steep
        (cx, cy, cx + 3, cy - 10),   # Octant 6: South-East, steep
        (cx, cy, cx + 10, cy - 3),   # Octant 7: East, shallow down
    ]

    for x1, y1, x2, y2 in test_lines:
        fb_c.line(x1, y1, x2, y2, 1)
        fb_py.line(x1, y1, x2, y2, 1)

    if not compare_buffers(buf_c, buf_py, "line() all octants"):
        return False

    print("✓ line() all octants test passed")
    return True


def test_line_clipping():
    """Test line clipping (partially out of bounds)"""
    w, h = 20, 20
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Line starting outside, ending inside
    fb_c.line(-5, 5, 10, 5, 1)
    fb_py.line(-5, 5, 10, 5, 1)

    if not compare_buffers(buf_c, buf_py, "line() clip start"):
        return False

    # Line starting inside, ending outside
    fb_c.line(5, 10, 25, 15, 1)
    fb_py.line(5, 10, 25, 15, 1)

    if not compare_buffers(buf_c, buf_py, "line() clip end"):
        return False

    # Line completely outside
    fb_c.line(-10, -10, -5, -5, 1)
    fb_py.line(-10, -10, -5, -5, 1)

    if not compare_buffers(buf_c, buf_py, "line() completely outside"):
        return False

    # Diagonal line crossing through
    fb_c.line(-5, -5, 25, 25, 1)
    fb_py.line(-5, -5, 25, 25, 1)

    if not compare_buffers(buf_c, buf_py, "line() crossing through"):
        return False

    print("✓ line() clipping test passed")
    return True


def test_line_single_pixel():
    """Test single-pixel lines (same start and end point)"""
    w, h = 10, 10
    size = ((h + 7) // 8) * w

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Line with same start and end
    fb_c.line(5, 5, 5, 5, 1)
    fb_py.line(5, 5, 5, 5, 1)

    if not compare_buffers(buf_c, buf_py, "line() single pixel"):
        return False

    # Another single pixel
    fb_c.line(3, 7, 3, 7, 1)
    fb_py.line(3, 7, 3, 7, 1)

    if not compare_buffers(buf_c, buf_py, "line() single pixel 2"):
        return False

    print("✓ line() single pixel test passed")
    return True


def test_line_rgb565():
    """Test line() with RGB565 format"""
    w, h = 20, 20
    size = w * h * 2  # 2 bytes per pixel

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.RGB565)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    # RGB565 color (red)
    red = 0xF800

    # Draw several lines
    fb_c.line(0, 0, 19, 19, red)
    fb_py.line(0, 0, 19, 19, red)

    fb_c.line(0, 10, 19, 10, red)
    fb_py.line(0, 10, 19, 10, red)

    fb_c.line(10, 0, 10, 19, red)
    fb_py.line(10, 0, 10, 19, red)

    if not compare_buffers(buf_c, buf_py, "line() RGB565"):
        return False

    print("✓ line() RGB565 test passed")
    return True


def test_line_gs8():
    """Test line() with GS8 format"""
    w, h = 20, 20
    size = w * h

    buf_c = bytearray(size)
    fb_c = framebuf_c.FrameBuffer(buf_c, w, h, framebuf_c.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    # Draw lines with different gray levels
    fb_c.line(0, 0, 19, 19, 128)
    fb_py.line(0, 0, 19, 19, 128)

    fb_c.line(0, 19, 19, 0, 255)
    fb_py.line(0, 19, 19, 0, 255)

    fb_c.line(5, 0, 5, 19, 64)
    fb_py.line(5, 0, 5, 19, 64)

    if not compare_buffers(buf_c, buf_py, "line() GS8"):
        return False

    print("✓ line() GS8 test passed")
    return True


def run_line_tests():
    """Run all line() tests"""
    print("\n" + "="*60)
    print("Line Tests")
    print("="*60)

    tests = [
        ("line() basic", test_line_basic),
        ("line() all octants", test_line_all_octants),
        ("line() clipping", test_line_clipping),
        ("line() single pixel", test_line_single_pixel),
        ("line() RGB565", test_line_rgb565),
        ("line() GS8", test_line_gs8),
    ]

    passed = 0
    failed = 0

    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ EXCEPTION in {name}: {e}")
            import sys
            sys.print_exception(e)
            failed += 1

    print("\n" + "="*60)
    print(f"Line Tests Results: {passed} passed, {failed} failed")
    print("="*60)

    return failed == 0


def run_all():
    """Run all tests"""
    success = True

    # Phase 1: MONO_VLSB
    if not run_mono_vlsb_tests():
        success = False

    # Phase 2: RGB565 and GS8
    if not run_rgb565_tests():
        success = False

    if not run_gs8_tests():
        success = False

    # Phase 3: MONO_HLSB and MONO_HMSB
    if not run_mono_hlsb_tests():
        success = False

    if not run_mono_hmsb_tests():
        success = False

    # Phase 4: GS4_HMSB and GS2_HMSB
    if not run_gs4_hmsb_tests():
        success = False

    if not run_gs2_hmsb_tests():
        success = False

    # Phase 5: Blit tests
    if not run_blit_tests():
        success = False

    # Phase 6: Line tests
    if not run_line_tests():
        success = False

    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")

    return success


if __name__ == "__main__":
    run_all()
