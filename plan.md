# MicroPython Pure-Python Framebuf Implementation Plan

## Overview
Create a pure-Python implementation of MicroPython's framebuf module (currently in C) that achieves **1:1 functional compatibility** using `@micropython.viper` optimization.

## Requirements
- ✅ **All 7 color modes**: MONO_VLSB, RGB565, GS4_HMSB, MONO_HLSB, MONO_HMSB, GS2_HMSB, GS8
- ✅ **4 core functions**: `pixel()`, `hline()`, `vline()`, `fill()`
- ✅ **Direct implementations**: hline/vline NOT via fill_rect
- ✅ **Correctness first**: Match C implementation byte-for-byte
- ✅ **Viper optimization**: Use @micropython.viper for speed
- ✅ **Hardware testing**: Test on MicroPython board via RFC2217

## Architecture

### File Structure
```
framebuf_pure.py          # Main implementation (single file)
├── Format constants (7)
├── FrameBuffer class
│   ├── __init__(buffer, width, height, format, stride)
│   ├── Public API: pixel(), hline(), vline(), fill()
│   └── 28 @viper functions (7 formats × 4 operations)

test_framebuf.py          # Test suite with byte-for-byte verification
```

### Implementation Strategy
- **Single FrameBuffer class** with format dispatch
- **28 viper-optimized functions** (7 formats × 4 operations)
- **Bounds checking** inside viper functions
- **Format-specific implementations** for maximum performance

## Color Modes Reference

| Format | ID | Bits/Pixel | Buffer Size | Index Calculation |
|--------|----|-----------:|-------------|-------------------|
| MONO_VLSB | 0 | 1 | `((h+7)//8)*w` | `(y>>3)*stride + x` |
| RGB565 | 1 | 16 | `w*h*2` | `(y*stride + x)*2` |
| GS4_HMSB | 2 | 4 | `((w+1)//2)*h` | `(y*stride + x)>>1` |
| MONO_HLSB | 3 | 1 | `((w+7)//8)*h` | `(y*stride + x)>>3` |
| MONO_HMSB | 4 | 1 | `((w+7)//8)*h` | `(y*stride + x)>>3` |
| GS2_HMSB | 5 | 2 | `((w+3)//4)*h` | `(y*stride + x)>>2` |
| GS8 | 6 | 8 | `w*h` | `y*stride + x` |

### Format-Specific Details

**MONO_VLSB (0)**: Vertical bits, LSB first
- Bit position: `y & 0x07` (bit 0 = top)
- Use for: SSD1306 displays

**RGB565 (1)**: 16-bit color, little-endian
- R: 5 bits, G: 6 bits, B: 5 bits
- Store: low byte first, then high byte

**GS4_HMSB (2)**: 4-bit grayscale
- Even pixels: upper nibble (bits 7:4)
- Odd pixels: lower nibble (bits 3:0)

**MONO_HLSB (3)**: Horizontal bits, LSB first
- Bit position: `7 - (x & 0x07)` (bit 7 = leftmost)
- **TRICKY**: Bit ordering reversed from HMSB!

**MONO_HMSB (4)**: Horizontal bits, MSB first
- Bit position: `x & 0x07` (bit 0 = leftmost)

**GS2_HMSB (5)**: 2-bit grayscale
- 4 pixels per byte
- Shift: `(x & 0x3) << 1`

**GS8 (6)**: 8-bit grayscale
- Simplest format: 1 byte per pixel

## Critical Viper Rules

**These are MANDATORY for correct operation:**

1. **Type annotations**
   ```python
   def _pixel_xxx(self, x: int, y: int, c: int) -> int:
   ```

2. **uint() casts for bit operations**
   ```python
   buf[i] |= uint(1 << offset)  # CORRECT ✅
   buf[i] |= (1 << offset)       # WRONG ❌ - type issues
   ```

3. **Buffer access with ptr8**
   ```python
   buf = ptr8(self.buffer)  # Do once at start
   ```

4. **Cache attributes in locals**
   ```python
   width = int(self.width)   # Not self.width in loops
   stride = int(self.stride)
   ```

5. **Bounds checking in viper**
   ```python
   if x < 0 or x >= width or y < 0 or y >= height:
       return 0
   ```

## Implementation Phases

### Phase 1: Foundation & MONO_VLSB ⬅ START HERE
1. Create `framebuf_pure.py`
2. Define constants and FrameBuffer.__init__()
3. Implement MONO_VLSB:
   - `_pixel_mono_vlsb()`
   - `_hline_mono_vlsb()`
   - `_vline_mono_vlsb()`
   - `_fill_mono_vlsb()`
4. Create `test_framebuf.py`
5. Test on hardware

**Milestone**: MONO_VLSB working and verified ✅

### Phase 2: Simple Formats
6. Implement RGB565 (all 4 functions)
7. Implement GS8 (all 4 functions)
8. Test against C implementation

**Milestone**: 3 formats working ✅

### Phase 3: Horizontal Mono Formats
9. Implement MONO_HLSB (watch bit ordering!)
10. Implement MONO_HMSB
11. Extensive edge case testing
12. Add uint casts everywhere

**Milestone**: All mono formats working ✅

### Phase 4: Multi-bit Grayscale
13. Implement GS4_HMSB (nibble alignment)
14. Implement GS2_HMSB (2-bit alignment)
15. Test all grayscale formats

**Milestone**: All 7 formats complete ✅

### Phase 5: Comprehensive Testing
16. Test edge cases (1x1, 7x9, 128x64, 256x256)
17. Test partial bytes, clipping
18. Upload to MicroPython board
19. Run hardware tests
20. Fix any discrepancies

**Milestone**: 100% correctness verified ✅

### Phase 6: Documentation
21. Add docstrings
22. Create usage examples
23. Optional: Performance benchmarks

**Milestone**: Complete implementation ✅

## Testing Strategy

### Byte-for-Byte Verification
```python
# Create identical buffers
buf_c = bytearray(size)
buf_py = bytearray(size)

# Create both framebuffers
fb_c = framebuf.FrameBuffer(buf_c, w, h, format)
fb_py = framebuf_pure.FrameBuffer(buf_py, w, h, format)

# Perform same operations
fb_c.pixel(x, y, c)
fb_py.pixel(x, y, c)

# Verify exact match
assert buf_c == buf_py, "Buffers must match exactly!"
```

### Hardware Testing Workflow
```bash
# 1. Upload implementation
./venvdev/bin/python -m there -p rfc2217://host.docker.internal:2217 push framebuf_pure.py /

# 2. Upload tests
./venvdev/bin/python -m there -p rfc2217://host.docker.internal:2217 push test_framebuf.py /

# 3. Reset board
./venvdev/bin/python -m there -p rfc2217://host.docker.internal:2217 --reset

# 4. Run tests
./venvdev/bin/python -m there -p rfc2217://host.docker.internal:2217 run /test_framebuf.py
```

## Common Pitfalls

### ❌ Mistakes to Avoid

1. **Missing uint() casts**
   ```python
   # WRONG
   buf[i] |= (1 << offset)

   # CORRECT
   buf[i] |= uint(1 << offset)
   ```

2. **Using width instead of stride**
   ```python
   # WRONG
   index = y * width + x

   # CORRECT
   index = y * stride + x
   ```

3. **Wrong bit ordering in MONO_HLSB**
   ```python
   # WRONG (this is HMSB)
   offset = x & 0x07

   # CORRECT (HLSB is reversed)
   offset = 7 - (x & 0x07)
   ```

4. **Forgetting partial byte handling**
   ```python
   # In fill(), handle non-multiple-of-8 dimensions!
   remaining_bits = height & 7
   if remaining_bits:
       # Mask partial bits
   ```

5. **Not clipping coordinates**
   ```python
   # Must clip, not reject!
   if x < 0:
       w += x  # Reduce width
       x = 0   # Start at 0
   ```

## Reference Files

### Implementation Reference
- **C source**: `/workspace/micropython/extmod/modframebuf.c`
  - Lines 70-74: MONO_HLSB/HMSB setpixel
  - Lines 98-106: MONO_VLSB setpixel
  - Lines 122-124: RGB565 setpixel
  - Lines 142-148: GS2_HMSB setpixel
  - Lines 166-174: GS4_HMSB setpixel
  - Lines 217-220: GS8 setpixel

### Documentation
- **Viper guide**: `/workspace/micropython/docs/reference/speed_python.rst`
- **ASM_Thumb**: `/workspace/micropython/docs/reference/asm_thumb2_*.rst`

### Test Patterns
- `/workspace/micropython/tests/extmod/framebuf1.py` - MONO formats
- `/workspace/micropython/tests/extmod/framebuf2.py` - GS2_HMSB
- `/workspace/micropython/tests/extmod/framebuf4.py` - GS4_HMSB
- `/workspace/micropython/tests/extmod/framebuf8.py` - GS8
- `/workspace/micropython/tests/extmod/framebuf16.py` - RGB565

## Quick Start Template

```python
# framebuf_pure.py - Basic structure

import micropython

# Format constants
MONO_VLSB = 0
RGB565 = 1
GS4_HMSB = 2
MONO_HLSB = 3
MONO_HMSB = 4
GS2_HMSB = 5
GS8 = 6

class FrameBuffer:
    def __init__(self, buffer, width, height, format, stride=None):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format
        self.stride = stride if stride is not None else width

    def pixel(self, x, y, c=-1):
        if self.format == MONO_VLSB:
            return self._pixel_mono_vlsb(x, y, c)
        # ... dispatch to other formats

    @micropython.viper
    def _pixel_mono_vlsb(self, x: int, y: int, c: int) -> int:
        # Implementation with proper uint casts
        pass
```

## Success Criteria

- ✅ All 7 formats implemented
- ✅ All 4 functions (pixel, hline, vline, fill) working
- ✅ Byte-for-byte match with C implementation
- ✅ All tests passing on hardware
- ✅ Clean, documented code

---

**Ready to implement!** Start with Phase 1: MONO_VLSB
