"""
Local test for framebuf_pure - runs without MicroPython board

This tests the pure Python implementation in isolation,
without comparing to the C implementation (since we may not have it locally).
"""

import framebuf_pure

def test_mono_vlsb_basic():
    """Basic MONO_VLSB functionality test"""
    print("Testing MONO_VLSB basic functionality...")

    w, h = 8, 16
    size = ((h + 7) // 8) * w  # 2 * 8 = 16 bytes

    buf = bytearray(size)
    fb = framebuf_pure.FrameBuffer(buf, w, h, framebuf_pure.MONO_VLSB)

    # Test pixel set/get
    fb.pixel(0, 0, 1)
    assert fb.pixel(0, 0) == 1, "Pixel(0,0) should be 1"
    assert buf[0] == 0x01, f"Buffer[0] should be 0x01, got 0x{buf[0]:02x}"

    fb.pixel(0, 1, 1)
    assert fb.pixel(0, 1) == 1, "Pixel(0,1) should be 1"
    assert buf[0] == 0x03, f"Buffer[0] should be 0x03, got 0x{buf[0]:02x}"

    fb.pixel(0, 7, 1)
    assert fb.pixel(0, 7) == 1, "Pixel(0,7) should be 1"
    assert buf[0] == 0x83, f"Buffer[0] should be 0x83, got 0x{buf[0]:02x}"

    # Test pixel crossing byte boundary
    fb.pixel(0, 8, 1)
    assert fb.pixel(0, 8) == 1, "Pixel(0,8) should be 1"
    assert buf[8] == 0x01, f"Buffer[8] should be 0x01, got 0x{buf[8]:02x}"

    print("✓ Pixel operations work correctly")

    # Test hline
    buf2 = bytearray(size)
    fb2 = framebuf_pure.FrameBuffer(buf2, w, h, framebuf_pure.MONO_VLSB)
    fb2.hline(0, 0, 8, 1)

    # All x positions at y=0 should be set (bit 0 in each byte)
    for x in range(8):
        assert buf2[x] == 0x01, f"Buffer[{x}] should be 0x01, got 0x{buf2[x]:02x}"

    print("✓ Hline works correctly")

    # Test vline
    buf3 = bytearray(size)
    fb3 = framebuf_pure.FrameBuffer(buf3, w, h, framebuf_pure.MONO_VLSB)
    fb3.vline(0, 0, 16, 1)

    # Vertical line at x=0 should set bits 0-7 in buf3[0] and bits 0-7 in buf3[8]
    assert buf3[0] == 0xFF, f"Buffer[0] should be 0xFF, got 0x{buf3[0]:02x}"
    assert buf3[8] == 0xFF, f"Buffer[8] should be 0xFF, got 0x{buf3[8]:02x}"

    print("✓ Vline works correctly")

    # Test fill
    buf4 = bytearray(size)
    fb4 = framebuf_pure.FrameBuffer(buf4, w, h, framebuf_pure.MONO_VLSB)
    fb4.fill(1)

    for i, byte in enumerate(buf4):
        assert byte == 0xFF, f"Buffer[{i}] should be 0xFF, got 0x{byte:02x}"

    fb4.fill(0)
    for i, byte in enumerate(buf4):
        assert byte == 0x00, f"Buffer[{i}] should be 0x00, got 0x{byte:02x}"

    print("✓ Fill works correctly")

    print("\n✅ All local tests passed!")
    return True


if __name__ == "__main__":
    try:
        test_mono_vlsb_basic()
    except AssertionError as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ Exception: {e}")
        import traceback
        traceback.print_exc()
