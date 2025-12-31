"""
Pure Python MicroPython Framebuffer Implementation
===================================================

A 1:1 compatible replacement for the built-in C framebuf module,
optimized with @micropython.viper for performance.

Supports all 7 color modes:
- MONO_VLSB (0): Monochrome vertical LSB
- RGB565 (1): 16-bit RGB color
- GS4_HMSB (2): 4-bit grayscale horizontal MSB
- MONO_HLSB (3): Monochrome horizontal LSB
- MONO_HMSB (4): Monochrome horizontal MSB
- GS2_HMSB (5): 2-bit grayscale horizontal MSB
- GS8 (6): 8-bit grayscale

Usage:
    import framebuf

    buf = bytearray(200)  # 50x32 MONO_VLSB: ((32+7)//8)*50 = 200 bytes
    fb = framebuf.FrameBuffer(buf, 50, 32, framebuf.MONO_VLSB)

    fb.pixel(10, 10, 1)
    fb.hline(0, 0, 50, 1)
    fb.vline(0, 0, 32, 1)
    fb.fill(0)
"""

import micropython
from uctypes import addressof

# Format constants
MONO_VLSB = 0
RGB565 = 1
GS4_HMSB = 2
MONO_HLSB = 3
MONO_HMSB = 4
GS2_HMSB = 5
GS8 = 6

# Aliases for compatibility
MVLSB = MONO_VLSB


# ====================================================================
# ASM_THUMB OPTIMIZED HELPERS
# Fast bulk memory fill operations using ARM Thumb-2 assembly
# ====================================================================

@micropython.asm_thumb
def _asm_fill_byte(r0, r1, r2):
    """
    Fill memory with a byte value using assembly (optimized with word writes)
    Args:
        r0: buffer address
        r1: number of bytes to fill
        r2: byte value to fill
    """
    # Replicate byte across all 4 positions in a 32-bit word
    # r3 = r2 | (r2 << 8) | (r2 << 16) | (r2 << 24)
    mov(r3, r2)         # r3 = byte
    lsl(r4, r2, 8)      # r4 = byte << 8
    orr(r3, r4)         # r3 = byte | (byte << 8)
    lsl(r4, r3, 16)     # r4 = (r3) << 16
    orr(r3, r4)         # r3 now has byte replicated 4 times

    # Calculate number of words (r1 / 4)
    mov(r4, r1)         # r4 = total bytes
    lsr(r4, r4, 2)      # r4 = total bytes / 4 (number of words)

    # Word fill loop
    label(WORD_LOOP)
    cmp(r4, 0)
    beq(BYTE_LOOP_SETUP)
    str(r3, [r0, 0])    # Store word (4 bytes at once)
    add(r0, r0, 4)      # r0 += 4
    sub(r4, r4, 1)      # r4--
    b(WORD_LOOP)

    # Handle remaining bytes (0-3 bytes)
    label(BYTE_LOOP_SETUP)
    mov(r4, 3)          # r4 = 3
    and_(r1, r4)        # r1 = original length & 3 (remainder)

    # Byte fill loop for remainder
    label(BYTE_LOOP)
    cmp(r1, 0)
    beq(END)
    strb(r2, [r0, 0])   # Store byte
    add(r0, r0, 1)      # r0++
    sub(r1, r1, 1)      # r1--
    b(BYTE_LOOP)

    label(END)


@micropython.asm_thumb
def _asm_fill_word(r0, r1, r2):
    """
    Fill memory with a 32-bit word value using assembly (for 4-byte aligned fills)
    Args:
        r0: buffer address (must be 4-byte aligned)
        r1: number of words to fill (total_bytes // 4)
        r2: 32-bit word value to fill
    """
    label(LOOP)
    str(r2, [r0, 0])   # Store word at r0
    add(r0, r0, 4)      # r0 += 4
    sub(r1, r1, 1)      # r1--
    bne(LOOP)           # if r1 != 0 goto LOOP


@micropython.asm_thumb
def _asm_fill_rgb565(r0, r1, r2):
    """
    Fill RGB565 buffer with alternating low/high bytes (optimized with word writes)
    Args:
        r0: buffer address
        r1: number of pixels to fill
        r2: 16-bit RGB565 color value

    Note: Uses r3, r4, r5 as scratch registers
    """
    # Create 32-bit word containing 2 pixels (color | (color << 16))
    lsl(r3, r2, 16)     # r3 = color << 16
    movw(r4, 0xFFFF)    # r4 = 0xFFFF (use movw for 16-bit immediate)
    and_(r2, r4)        # r2 = color & 0xFFFF (lower 16 bits)
    orr(r3, r2)         # r3 = (color << 16) | color (2 pixels in one word)

    # Calculate number of word writes (pixels / 2)
    mov(r4, r1)         # r4 = total pixels
    lsr(r4, r4, 1)      # r4 = pixels / 2 (number of words)

    # Word fill loop (write 2 pixels at once)
    label(WORD_LOOP)
    cmp(r4, 0)
    beq(PIXEL_LOOP_SETUP)
    str(r3, [r0, 0])    # Store word (2 pixels at once)
    add(r0, r0, 4)      # r0 += 4
    sub(r4, r4, 1)      # r4--
    b(WORD_LOOP)

    # Handle remaining pixel (if odd number of pixels)
    label(PIXEL_LOOP_SETUP)
    mov(r4, 1)          # r4 = 1
    and_(r1, r4)        # r1 = original pixel count & 1 (remainder)

    # Single pixel write for remainder
    label(PIXEL_LOOP)
    cmp(r1, 0)
    beq(END)
    strh(r2, [r0, 0])   # Store halfword (1 pixel = 2 bytes)

    label(END)



class FrameBufferBase:
    """
    Base FrameBuffer class with shared public API

    Subclasses implement format-specific methods:
    - _pixel_impl(x, y, c) -> int
    - _hline_impl(x, y, w, c)
    - _vline_impl(x, y, h, c)
    - _fill_rect_impl(x, y, w, h, c)
    """

    def __init__(self, buffer, width, height, stride=None):
        """
        Initialize framebuffer

        Args:
            buffer: bytearray or buffer protocol object
            width: Width in pixels
            height: Height in pixels
            stride: Optional stride in pixels (defaults to width)
        """
        self.buffer = buffer
        self.width = width
        self.height = height
        self.stride = stride if stride is not None else width

    def pixel(self, x, y, c=-1):
        """
        Get or set pixel value at (x, y)

        Args:
            x: X coordinate
            y: Y coordinate
            c: Color value (optional). If omitted, returns current pixel value.

        Returns:
            Current pixel value (if c not provided), or 0 (if c provided)
        """
        raise NotImplementedError("Subclass must implement pixel()")

    def hline(self, x, y, w, c):
        """Draw horizontal line starting at (x, y) with width w and color c"""
        raise NotImplementedError("Subclass must implement hline()")

    def vline(self, x, y, h, c):
        """Draw vertical line starting at (x, y) with height h and color c"""
        raise NotImplementedError("Subclass must implement vline()")

    def fill(self, c):
        """Fill entire framebuffer with color c"""
        self.fill_rect(0, 0, self.width, self.height, c)

    def fill_rect(self, x, y, w, h, c):
        """
        Fill rectangle with color c

        Args:
            x: Starting X coordinate
            y: Starting Y coordinate
            w: Width in pixels
            h: Height in pixels
            c: Color value
        """
        # Bounds checking and clipping (matches C implementation)
        if h < 1 or w < 1 or x + w <= 0 or y + h <= 0 or y >= self.height or x >= self.width:
            return

        # Clip to framebuffer bounds
        xend = min(self.width, x + w)
        yend = min(self.height, y + h)
        x = max(x, 0)
        y = max(y, 0)
        w = xend - x
        h = yend - y

        # Call format-specific implementation
        self._fill_rect_impl(x, y, w, h, c)

    def rect(self, x, y, w, h, c, f=False):
        """
        Draw rectangle outline or filled rectangle

        Args:
            x: Starting X coordinate
            y: Starting Y coordinate
            w: Width in pixels
            h: Height in pixels
            c: Color value
            f: Fill flag (optional). If True, draws filled rectangle.
        """
        if f:
            self.fill_rect(x, y, w, h, c)
        else:
            # Outline rectangle - draw 4 lines
            self.fill_rect(x, y, w, 1, c)                  # Top edge
            self.fill_rect(x, y + h - 1, w, 1, c)          # Bottom edge
            self.fill_rect(x, y, 1, h, c)                  # Left edge
            self.fill_rect(x + w - 1, y, 1, h, c)          # Right edge

    def blit(self, fbuf, x, y, key=-1, palette=None):
        """
        Blit another framebuffer into this one at position (x, y)

        Args:
            fbuf: Source FrameBuffer or tuple (buffer, width, height, format[, stride])
            x: Destination X coordinate
            y: Destination Y coordinate
            key: Transparency color (-1 = no transparency)
            palette: Optional palette FrameBuffer for color translation (height=1)
        """
        # Parse source framebuffer
        if isinstance(fbuf, tuple):
            if not (4 <= len(fbuf) <= 5):
                raise ValueError("Tuple must be (buffer, width, height, format[, stride])")

            src_buf, src_width, src_height, src_format = fbuf[:4]
            src_stride = fbuf[4] if len(fbuf) == 5 else src_width

            # Create temporary FrameBuffer wrapper
            source = _create_framebuffer(src_buf, src_width, src_height, src_format, src_stride)
        else:
            # Assume it's a FrameBuffer object
            source = fbuf
            src_width = source.width
            src_height = source.height

        # Parse palette if provided
        pal = None
        if palette is not None:
            if isinstance(palette, tuple):
                if not (4 <= len(palette) <= 5):
                    raise ValueError("Palette tuple must be (buffer, width, height, format[, stride])")

                pal_buf, pal_width, pal_height, pal_format = palette[:4]
                pal_stride = palette[4] if len(palette) == 5 else pal_width
                pal = _create_framebuffer(pal_buf, pal_width, pal_height, pal_format, pal_stride)
            else:
                pal = palette

            # Validate palette: height must be 1
            if pal.height != 1:
                raise ValueError("Palette height must be 1")

        # Early bounds check
        if (x >= self.width or
            y >= self.height or
            -x >= src_width or
            -y >= src_height):
            # Completely out of bounds, no-op
            return

        # Check if we can use optimized fast path
        # Fast path 1: same format, no palette, source has _blit_same_format
        can_use_same_format = (pal is None and
                              hasattr(self, 'FORMAT') and
                              hasattr(source, 'FORMAT') and
                              self.FORMAT == source.FORMAT and
                              hasattr(self, '_blit_same_format'))

        # Fast path 2: MONO_HMSB -> RGB565 with palette (for text/icon rendering)
        can_use_mono_palette = (pal is not None and
                               hasattr(self, 'FORMAT') and
                               hasattr(source, 'FORMAT') and
                               self.FORMAT == RGB565 and
                               source.FORMAT == MONO_HMSB and
                               hasattr(self, '_blit_mono_hmsb_palette'))

        if can_use_same_format:
            # Use viper-optimized same-format blit
            self._blit_same_format(source.buffer, src_width, src_height,
                                  source.stride, x, y, key)
        elif can_use_mono_palette:
            # Use viper-optimized MONO_HMSB -> RGB565 palette blit
            self._blit_mono_hmsb_palette(source.buffer, src_width, src_height,
                                        source.stride, x, y, key, pal.buffer)
        else:
            # Fall back to general-purpose pixel-by-pixel blit
            # Calculate clipping
            x0 = max(0, x)              # destination start X (clipped)
            y0 = max(0, y)              # destination start Y (clipped)
            x1 = max(0, -x)             # source start X offset
            y1 = max(0, -y)             # source start Y offset
            x0end = min(self.width, x + src_width)      # destination end X
            y0end = min(self.height, y + src_height)    # destination end Y

            # Blit loop
            for cy0 in range(y0, y0end):
                cx1 = x1
                for cx0 in range(x0, x0end):
                    # Get pixel from source (pass -1 to indicate GET operation)
                    col = source.pixel(cx1, y1, -1)

                    # Apply palette translation if provided
                    if pal is not None:
                        col = pal.pixel(col, 0, -1)

                    # Set pixel in destination if not transparent
                    if col != key:
                        self.pixel(cx0, cy0, col)

                    cx1 += 1
                y1 += 1


# ====================================================================
# FACTORY FUNCTION FOR C API COMPATIBILITY
# ====================================================================

def _create_framebuffer(buffer, width, height, format, stride=None):
    """Factory function - creates appropriate subclass based on format"""
    # Validate parameters
    if stride is None:
        stride = width

    if width < 1 or height < 1 or width > 0xffff or height > 0xffff or stride > 0xffff or stride < width:
        raise ValueError("Invalid framebuffer dimensions")

    # Calculate required buffer size
    bpp = 1
    height_required = height
    width_required = width
    strides_required = height - 1
    stride_for_calc = stride  # Use separate variable for calculation

    if format == MONO_VLSB:
        height_required = (height + 7) & ~7
        strides_required = height_required - 8
    elif format == MONO_HLSB or format == MONO_HMSB:
        stride_for_calc = (stride + 7) & ~7
        width_required = (width + 7) & ~7
    elif format == GS2_HMSB:
        stride_for_calc = (stride + 3) & ~3
        width_required = (width + 3) & ~3
        bpp = 2
    elif format == GS4_HMSB:
        stride_for_calc = (stride + 1) & ~1
        width_required = (width + 1) & ~1
        bpp = 4
    elif format == GS8:
        bpp = 8
    elif format == RGB565:
        bpp = 16
    else:
        raise ValueError("Invalid format")

    # Validate buffer size
    required_size = (strides_required * stride_for_calc + (height_required - strides_required) * width_required) * bpp // 8
    if len(buffer) < required_size:
        raise ValueError("Buffer too small")

    # Lazy imports to avoid circular dependencies
    if format == MONO_VLSB:
        from framebuf_mono_vlsb import FrameBufferMONO_VLSB
        return FrameBufferMONO_VLSB(buffer, width, height, stride)
    elif format == RGB565:
        from framebuf_rgb565 import FrameBufferRGB565
        return FrameBufferRGB565(buffer, width, height, stride)
    elif format == GS4_HMSB:
        from framebuf_gs4_hmsb import FrameBufferGS4_HMSB
        return FrameBufferGS4_HMSB(buffer, width, height, stride)
    elif format == MONO_HLSB:
        from framebuf_mono_hlsb import FrameBufferMONO_HLSB
        return FrameBufferMONO_HLSB(buffer, width, height, stride)
    elif format == MONO_HMSB:
        from framebuf_mono_hmsb import FrameBufferMONO_HMSB
        return FrameBufferMONO_HMSB(buffer, width, height, stride)
    elif format == GS2_HMSB:
        from framebuf_gs2_hmsb import FrameBufferGS2_HMSB
        return FrameBufferGS2_HMSB(buffer, width, height, stride)
    elif format == GS8:
        from framebuf_gs8 import FrameBufferGS8
        return FrameBufferGS8(buffer, width, height, stride)

# Shadow FrameBuffer name with factory for C API compatibility
FrameBuffer = _create_framebuffer
