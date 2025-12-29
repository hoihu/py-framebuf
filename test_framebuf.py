"""
Test suite for pure-Python framebuf implementation

Tests each format against the built-in C implementation
to ensure byte-for-byte compatibility.
"""

try:
    import framebuf  # C implementation
    import framebuf_pure  # Our implementation
    HAS_C_FRAMEBUF = True
except ImportError:
    # On some platforms, built-in framebuf may not be available
    import framebuf_pure
    framebuf = None
    HAS_C_FRAMEBUF = False
    print("WARNING: Built-in framebuf not available, testing pure implementation only")


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

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test single pixel
    if HAS_C_FRAMEBUF:
        fb_c.pixel(0, 0, 1)
    fb_py.pixel(0, 0, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB pixel(0, 0, 1)"):
        return False

    # Test multiple pixels
    test_pixels = [(5, 5, 1), (10, 15, 1), (19, 31, 1), (0, 7, 1), (0, 8, 1)]
    for x, y, c in test_pixels:
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB multiple pixels"):
        return False

    print("✓ MONO_VLSB pixel set test passed")
    return True


def test_mono_vlsb_pixel_get():
    """Test MONO_VLSB pixel get operations"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Set some pixels
    test_pixels = [(5, 5, 1), (10, 15, 1), (19, 31, 1)]
    for x, y, c in test_pixels:
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    # Read them back
    for x, y, expected in test_pixels:
        if HAS_C_FRAMEBUF:
            val_c = fb_c.pixel(x, y)
            val_py = fb_py.pixel(x, y)
            if val_c != val_py:
                print(f"❌ FAILED: pixel({x}, {y}) returned {val_py}, expected {val_c}")
                return False
            if val_c != expected:
                print(f"❌ FAILED: pixel({x}, {y}) returned {val_c}, expected {expected}")
                return False
        else:
            val_py = fb_py.pixel(x, y)
            if val_py != expected:
                print(f"❌ FAILED: pixel({x}, {y}) returned {val_py}, expected {expected}")
                return False

    print("✓ MONO_VLSB pixel get test passed")
    return True


def test_mono_vlsb_hline():
    """Test MONO_VLSB horizontal line"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test hline across full width
    if HAS_C_FRAMEBUF:
        fb_c.hline(0, 5, w, 1)
    fb_py.hline(0, 5, w, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB hline(0, 5, 20, 1)"):
        return False

    # Test hline partial
    if HAS_C_FRAMEBUF:
        fb_c.hline(5, 10, 10, 1)
    fb_py.hline(5, 10, 10, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB hline(5, 10, 10, 1)"):
        return False

    # Test hline with clear
    if HAS_C_FRAMEBUF:
        fb_c.hline(5, 10, 5, 0)
    fb_py.hline(5, 10, 5, 0)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB hline clear"):
        return False

    print("✓ MONO_VLSB hline test passed")
    return True


def test_mono_vlsb_vline():
    """Test MONO_VLSB vertical line"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test vline across full height
    if HAS_C_FRAMEBUF:
        fb_c.vline(5, 0, h, 1)
    fb_py.vline(5, 0, h, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB vline(5, 0, 32, 1)"):
        return False

    # Test vline partial
    if HAS_C_FRAMEBUF:
        fb_c.vline(10, 5, 10, 1)
    fb_py.vline(10, 5, 10, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB vline(10, 5, 10, 1)"):
        return False

    # Test vline spanning byte boundaries (y=6 to y=10 crosses byte boundary at y=8)
    if HAS_C_FRAMEBUF:
        fb_c.vline(15, 6, 5, 1)
    fb_py.vline(15, 6, 5, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB vline byte boundary"):
        return False

    print("✓ MONO_VLSB vline test passed")
    return True


def test_mono_vlsb_fill():
    """Test MONO_VLSB fill"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    # Test fill with 1
    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)
        fb_c.fill(1)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)
    fb_py.fill(1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB fill(1)"):
        return False

    # Test fill with 0
    if HAS_C_FRAMEBUF:
        fb_c.fill(0)
    fb_py.fill(0)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB fill(0)"):
        return False

    # Test with non-multiple-of-8 height
    h2 = 25  # Not a multiple of 8
    size2 = ((h2 + 7) // 8) * w

    if HAS_C_FRAMEBUF:
        buf_c2 = bytearray(size2)
        fb_c2 = framebuf.FrameBuffer(buf_c2, w, h2, framebuf.MONO_VLSB)
        fb_c2.fill(1)

    buf_py2 = bytearray(size2)
    fb_py2 = framebuf_pure.FrameBuffer(buf_py2, w, h2, framebuf_pure.MONO_VLSB)
    fb_py2.fill(1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c2, buf_py2, "MONO_VLSB fill partial height"):
        return False

    print("✓ MONO_VLSB fill test passed")
    return True


def test_mono_vlsb_edge_cases():
    """Test MONO_VLSB edge cases"""
    w, h = 20, 32
    size = ((h + 7) // 8) * w

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_VLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_VLSB)

    # Test clipping - pixel outside bounds
    if HAS_C_FRAMEBUF:
        fb_c.pixel(-1, 5, 1)
        fb_c.pixel(25, 5, 1)
        fb_c.pixel(5, -1, 1)
        fb_c.pixel(5, 35, 1)

    fb_py.pixel(-1, 5, 1)
    fb_py.pixel(25, 5, 1)
    fb_py.pixel(5, -1, 1)
    fb_py.pixel(5, 35, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB pixel clipping"):
        return False

    # Test hline clipping
    if HAS_C_FRAMEBUF:
        fb_c.hline(-5, 10, 10, 1)  # Starts before buffer, should clip
        fb_c.hline(15, 10, 10, 1)  # Extends past buffer, should clip

    fb_py.hline(-5, 10, 10, 1)
    fb_py.hline(15, 10, 10, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB hline clipping"):
        return False

    # Test vline clipping
    if HAS_C_FRAMEBUF:
        fb_c.vline(10, -5, 10, 1)  # Starts before buffer, should clip
        fb_c.vline(10, 25, 10, 1)  # Extends past buffer, should clip

    fb_py.vline(10, -5, 10, 1)
    fb_py.vline(10, 25, 10, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_VLSB vline clipping"):
        return False

    print("✓ MONO_VLSB edge cases test passed")
    return True


# ========================================================================
# RGB565 Tests
# ========================================================================

def test_rgb565_pixel():
    """Test RGB565 pixel operations"""
    w, h = 10, 10
    size = w * h * 2  # 2 bytes per pixel

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.RGB565)

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
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, color)
        fb_py.pixel(x, y, color)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "RGB565 pixel set"):
        return False

    # Test pixel get
    for i, color in enumerate(colors):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            val_c = fb_c.pixel(x, y)
            val_py = fb_py.pixel(x, y)
            if val_c != val_py or val_c != color:
                print(f"❌ FAILED: RGB565 pixel({x}, {y}) get mismatch")
                return False
        else:
            val_py = fb_py.pixel(x, y)
            if val_py != color:
                print(f"❌ FAILED: RGB565 pixel({x}, {y}) returned {val_py:04x}, expected {color:04x}")
                return False

    print("✓ RGB565 pixel test passed")
    return True


def test_rgb565_hline():
    """Test RGB565 horizontal line"""
    w, h = 20, 10
    size = w * h * 2

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.RGB565)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    # Test hline with red color
    if HAS_C_FRAMEBUF:
        fb_c.hline(0, 5, w, 0xF800)
    fb_py.hline(0, 5, w, 0xF800)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "RGB565 hline"):
        return False

    print("✓ RGB565 hline test passed")
    return True


def test_rgb565_vline():
    """Test RGB565 vertical line"""
    w, h = 20, 10
    size = w * h * 2

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.RGB565)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)

    # Test vline with green color
    if HAS_C_FRAMEBUF:
        fb_c.vline(5, 0, h, 0x07E0)
    fb_py.vline(5, 0, h, 0x07E0)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "RGB565 vline"):
        return False

    print("✓ RGB565 vline test passed")
    return True


def test_rgb565_fill():
    """Test RGB565 fill"""
    w, h = 10, 10
    size = w * h * 2

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.RGB565)
        fb_c.fill(0x001F)  # Blue

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.RGB565)
    fb_py.fill(0x001F)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "RGB565 fill"):
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

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    # Test grayscale values
    grays = [0, 64, 128, 192, 255]

    for i, gray in enumerate(grays):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, gray)
        fb_py.pixel(x, y, gray)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS8 pixel set"):
        return False

    # Test pixel get
    for i, gray in enumerate(grays):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            val_c = fb_c.pixel(x, y)
            val_py = fb_py.pixel(x, y)
            if val_c != val_py or val_c != gray:
                print(f"❌ FAILED: GS8 pixel({x}, {y}) get mismatch")
                return False
        else:
            val_py = fb_py.pixel(x, y)
            if val_py != gray:
                print(f"❌ FAILED: GS8 pixel({x}, {y}) returned {val_py}, expected {gray}")
                return False

    print("✓ GS8 pixel test passed")
    return True


def test_gs8_hline():
    """Test GS8 horizontal line"""
    w, h = 20, 10
    size = w * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    if HAS_C_FRAMEBUF:
        fb_c.hline(0, 5, w, 128)
    fb_py.hline(0, 5, w, 128)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS8 hline"):
        return False

    print("✓ GS8 hline test passed")
    return True


def test_gs8_vline():
    """Test GS8 vertical line"""
    w, h = 20, 10
    size = w * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS8)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)

    if HAS_C_FRAMEBUF:
        fb_c.vline(5, 0, h, 192)
    fb_py.vline(5, 0, h, 192)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS8 vline"):
        return False

    print("✓ GS8 vline test passed")
    return True


def test_gs8_fill():
    """Test GS8 fill"""
    w, h = 10, 10
    size = w * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS8)
        fb_c.fill(200)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS8)
    fb_py.fill(200)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS8 fill"):
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

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    # Test pixels across byte boundary
    test_pixels = [(0, 0, 1), (7, 0, 1), (8, 0, 1), (15, 0, 1), (5, 5, 1)]
    for x, y, c in test_pixels:
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HLSB pixel set"):
        return False

    print("✓ MONO_HLSB pixel test passed")
    return True


def test_mono_hlsb_hline():
    """Test MONO_HLSB horizontal line - critical for byte spanning"""
    w, h = 24, 10  # 24 = 3 bytes wide
    size = ((w + 7) // 8) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    # Test hline within single byte
    if HAS_C_FRAMEBUF:
        fb_c.hline(1, 0, 3, 1)
    fb_py.hline(1, 0, 3, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HLSB hline single byte"):
        return False

    # Test hline spanning two bytes
    if HAS_C_FRAMEBUF:
        fb_c.hline(5, 1, 6, 1)  # Crosses byte boundary at x=8
    fb_py.hline(5, 1, 6, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HLSB hline two bytes"):
        return False

    # Test hline spanning three bytes
    if HAS_C_FRAMEBUF:
        fb_c.hline(6, 2, 12, 1)  # Crosses two byte boundaries
    fb_py.hline(6, 2, 12, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HLSB hline three bytes"):
        return False

    print("✓ MONO_HLSB hline test passed")
    return True


def test_mono_hlsb_vline():
    """Test MONO_HLSB vertical line"""
    w, h = 16, 20
    size = ((w + 7) // 8) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HLSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)

    if HAS_C_FRAMEBUF:
        fb_c.vline(5, 0, h, 1)
    fb_py.vline(5, 0, h, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HLSB vline"):
        return False

    print("✓ MONO_HLSB vline test passed")
    return True


def test_mono_hlsb_fill():
    """Test MONO_HLSB fill"""
    w, h = 13, 10  # Non-multiple of 8 to test partial byte handling
    size = ((w + 7) // 8) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HLSB)
        fb_c.fill(1)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HLSB)
    fb_py.fill(1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HLSB fill(1)"):
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

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)

    # Test pixels across byte boundary
    test_pixels = [(0, 0, 1), (7, 0, 1), (8, 0, 1), (15, 0, 1), (5, 5, 1)]
    for x, y, c in test_pixels:
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, c)
        fb_py.pixel(x, y, c)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HMSB pixel set"):
        return False

    print("✓ MONO_HMSB pixel test passed")
    return True


def test_mono_hmsb_hline():
    """Test MONO_HMSB horizontal line - critical for byte spanning"""
    w, h = 24, 10
    size = ((w + 7) // 8) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)

    # Test hline within single byte
    if HAS_C_FRAMEBUF:
        fb_c.hline(1, 0, 3, 1)
    fb_py.hline(1, 0, 3, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HMSB hline single byte"):
        return False

    # Test hline spanning two bytes
    if HAS_C_FRAMEBUF:
        fb_c.hline(5, 1, 6, 1)
    fb_py.hline(5, 1, 6, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HMSB hline two bytes"):
        return False

    # Test hline spanning three bytes
    if HAS_C_FRAMEBUF:
        fb_c.hline(6, 2, 12, 1)
    fb_py.hline(6, 2, 12, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HMSB hline three bytes"):
        return False

    print("✓ MONO_HMSB hline test passed")
    return True


def test_mono_hmsb_vline():
    """Test MONO_HMSB vertical line"""
    w, h = 16, 20
    size = ((w + 7) // 8) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)

    if HAS_C_FRAMEBUF:
        fb_c.vline(5, 0, h, 1)
    fb_py.vline(5, 0, h, 1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HMSB vline"):
        return False

    print("✓ MONO_HMSB vline test passed")
    return True


def test_mono_hmsb_fill():
    """Test MONO_HMSB fill"""
    w, h = 13, 10  # Non-multiple of 8
    size = ((w + 7) // 8) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.MONO_HMSB)
        fb_c.fill(1)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.MONO_HMSB)
    fb_py.fill(1)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "MONO_HMSB fill(1)"):
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

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS4_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)

    # Test various 4-bit values (0-15)
    values = [0, 3, 7, 10, 15]
    for i, val in enumerate(values):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, val)
        fb_py.pixel(x, y, val)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS4_HMSB pixel set"):
        return False

    # Test pixel get
    for i, val in enumerate(values):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            val_c = fb_c.pixel(x, y)
            val_py = fb_py.pixel(x, y)
            if val_c != val_py or val_c != val:
                print(f"❌ FAILED: GS4_HMSB pixel({x}, {y}) get mismatch")
                return False
        else:
            val_py = fb_py.pixel(x, y)
            if val_py != val:
                print(f"❌ FAILED: GS4_HMSB pixel({x}, {y}) returned {val_py}, expected {val}")
                return False

    print("✓ GS4_HMSB pixel test passed")
    return True


def test_gs4_hmsb_hline():
    """Test GS4_HMSB horizontal line"""
    w, h = 20, 10
    size = ((w + 1) // 2) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS4_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)

    # Test hline with even and odd alignments
    if HAS_C_FRAMEBUF:
        fb_c.hline(0, 5, w, 8)  # Even start
    fb_py.hline(0, 5, w, 8)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS4_HMSB hline even"):
        return False

    # Odd start, odd width
    if HAS_C_FRAMEBUF:
        fb_c.hline(1, 3, 7, 12)
    fb_py.hline(1, 3, 7, 12)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS4_HMSB hline odd"):
        return False

    print("✓ GS4_HMSB hline test passed")
    return True


def test_gs4_hmsb_vline():
    """Test GS4_HMSB vertical line"""
    w, h = 20, 10
    size = ((w + 1) // 2) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS4_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)

    if HAS_C_FRAMEBUF:
        fb_c.vline(5, 0, h, 9)
    fb_py.vline(5, 0, h, 9)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS4_HMSB vline"):
        return False

    print("✓ GS4_HMSB vline test passed")
    return True


def test_gs4_hmsb_fill():
    """Test GS4_HMSB fill"""
    w, h = 10, 10
    size = ((w + 1) // 2) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS4_HMSB)
        fb_c.fill(11)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS4_HMSB)
    fb_py.fill(11)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS4_HMSB fill"):
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

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS2_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)

    # Test all 2-bit values (0-3)
    values = [0, 1, 2, 3]
    for i, val in enumerate(values):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            fb_c.pixel(x, y, val)
        fb_py.pixel(x, y, val)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS2_HMSB pixel set"):
        return False

    # Test pixel get
    for i, val in enumerate(values):
        x, y = i % w, i // w
        if HAS_C_FRAMEBUF:
            val_c = fb_c.pixel(x, y)
            val_py = fb_py.pixel(x, y)
            if val_c != val_py or val_c != val:
                print(f"❌ FAILED: GS2_HMSB pixel({x}, {y}) get mismatch")
                return False
        else:
            val_py = fb_py.pixel(x, y)
            if val_py != val:
                print(f"❌ FAILED: GS2_HMSB pixel({x}, {y}) returned {val_py}, expected {val}")
                return False

    print("✓ GS2_HMSB pixel test passed")
    return True


def test_gs2_hmsb_hline():
    """Test GS2_HMSB horizontal line"""
    w, h = 16, 8
    size = ((w + 3) // 4) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS2_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)

    if HAS_C_FRAMEBUF:
        fb_c.hline(0, 4, w, 2)
    fb_py.hline(0, 4, w, 2)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS2_HMSB hline"):
        return False

    print("✓ GS2_HMSB hline test passed")
    return True


def test_gs2_hmsb_vline():
    """Test GS2_HMSB vertical line"""
    w, h = 16, 8
    size = ((w + 3) // 4) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS2_HMSB)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)

    if HAS_C_FRAMEBUF:
        fb_c.vline(7, 0, h, 3)
    fb_py.vline(7, 0, h, 3)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS2_HMSB vline"):
        return False

    print("✓ GS2_HMSB vline test passed")
    return True


def test_gs2_hmsb_fill():
    """Test GS2_HMSB fill"""
    w, h = 12, 8
    size = ((w + 3) // 4) * h

    if HAS_C_FRAMEBUF:
        buf_c = bytearray(size)
        fb_c = framebuf.FrameBuffer(buf_c, w, h, framebuf.GS2_HMSB)
        fb_c.fill(2)

    buf_py = bytearray(size)
    fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, framebuf_pure.GS2_HMSB)
    fb_py.fill(2)

    if HAS_C_FRAMEBUF and not compare_buffers(buf_c, buf_py, "GS2_HMSB fill"):
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

    if success:
        print("\n✅ ALL TESTS PASSED!")
    else:
        print("\n❌ SOME TESTS FAILED")

    return success


if __name__ == "__main__":
    run_all()
