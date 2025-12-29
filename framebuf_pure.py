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
    import framebuf_pure as framebuf

    buf = bytearray(200)  # 50x32 MONO_VLSB: ((32+7)//8)*50 = 200 bytes
    fb = framebuf.FrameBuffer(buf, 50, 32, framebuf.MONO_VLSB)

    fb.pixel(10, 10, 1)
    fb.hline(0, 0, 50, 1)
    fb.vline(0, 0, 32, 1)
    fb.fill(0)
"""

import micropython
from uctypes import addressof

# Format constants (match C implementation)
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


class FrameBuffer:
    """
    FrameBuffer class - pure Python implementation matching C API
    """

    def __init__(self, buffer, width, height, format, stride=None):
        """
        Initialize framebuffer

        Args:
            buffer: bytearray or buffer protocol object
            width: Width in pixels
            height: Height in pixels
            format: One of the format constants (MONO_VLSB, RGB565, etc.)
            stride: Optional stride in pixels (defaults to width)
        """
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format
        self.stride = stride if stride is not None else width

        # Cache function references to eliminate dispatch overhead
        # This is the key optimization that C uses with function pointer tables
        # Dictionary maps format to (pixel, fill_rect, hline, vline) implementations
        draw_callbacks = {
            MONO_VLSB: (self._pixel_mono_vlsb, self._fill_rect_mono_vlsb,
                       self._hline_mono_vlsb, self._vline_mono_vlsb),
            RGB565: (self._pixel_rgb565, self._fill_rect_rgb565,
                    self._hline_rgb565, self._vline_rgb565),
            GS4_HMSB: (self._pixel_gs4_hmsb, self._fill_rect_gs4_hmsb,
                      self._hline_gs4_hmsb, self._vline_gs4_hmsb),
            MONO_HLSB: (self._pixel_mono_hlsb, self._fill_rect_mono_hlsb,
                       self._hline_mono_hlsb, self._vline_mono_hlsb),
            MONO_HMSB: (self._pixel_mono_hmsb, self._fill_rect_mono_hmsb,
                       self._hline_mono_hmsb, self._vline_mono_hmsb),
            GS2_HMSB: (self._pixel_gs2_hmsb, self._fill_rect_gs2_hmsb,
                      self._hline_gs2_hmsb, self._vline_gs2_hmsb),
            GS8: (self._pixel_gs8, self._fill_rect_gs8,
                 self._hline_gs8, self._vline_gs8),
        }

        # Unpack cached function references for this format
        self._pixel_impl, self._fill_rect_impl, self._hline_impl, self._vline_impl = draw_callbacks[format]

    # ====================================================================
    # PUBLIC API
    # ====================================================================

    def pixel(self, x, y, c=-1):
        """
        Get or set pixel value at (x, y)

        Optimized: Uses cached function reference to eliminate dispatch overhead.
        This matches the C implementation's function pointer table approach.

        Args:
            x: X coordinate
            y: Y coordinate
            c: Color value (optional). If omitted, returns current pixel value.
               If provided, sets pixel to this color.

        Returns:
            Current pixel value (if c not provided), or 0 (if c provided)
        """
        return self._pixel_impl(x, y, c)

    def hline(self, x, y, w, c):
        """
        Draw horizontal line starting at (x, y) with width w and color c

        Optimized: Uses cached function reference to eliminate dispatch overhead.

        Args:
            x: Starting X coordinate
            y: Y coordinate
            w: Width in pixels
            c: Color value
        """
        self._hline_impl(x, y, w, c)

    def vline(self, x, y, h, c):
        """
        Draw vertical line starting at (x, y) with height h and color c

        Optimized: Uses cached function reference to eliminate dispatch overhead.

        Args:
            x: X coordinate
            y: Starting Y coordinate
            h: Height in pixels
            c: Color value
        """
        self._vline_impl(x, y, h, c)

    def fill(self, c):
        """
        Fill entire framebuffer with color c

        Args:
            c: Color value
        """
        # Use fill_rect to fill entire buffer
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
            f: Fill flag (optional). If True, draws filled rectangle. If False, draws outline.
        """
        if f:
            # Filled rectangle
            self.fill_rect(x, y, w, h, c)
        else:
            # Outline rectangle - draw 4 lines
            self.fill_rect(x, y, w, 1, c)                  # Top edge
            self.fill_rect(x, y + h - 1, w, 1, c)          # Bottom edge
            self.fill_rect(x, y, 1, h, c)                  # Left edge
            self.fill_rect(x + w - 1, y, 1, h, c)          # Right edge

    # ====================================================================
    # MONO_VLSB IMPLEMENTATIONS
    # Format 0: Monochrome, vertical byte layout, LSB first
    # Buffer size: ((height + 7) // 8) * width bytes
    # Byte index: (y >> 3) * stride + x
    # Bit offset: y & 0x07 (bit 0 = top, bit 7 = bottom of byte)
    # ====================================================================

    @micropython.viper
    def _pixel_mono_vlsb(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for MONO_VLSB format - optimized"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check - unsigned comparison handles negative values
        if uint(x) >= uint(width) or uint(y) >= uint(height):
            return 0

        buf = ptr8(self.buffer)
        index = uint((y >> 3) * stride + x)
        offset = uint(y & 0x07)
        mask = uint(1 << offset)

        if c == -1:  # Get pixel
            return int((buf[index] >> offset) & 1)
        else:  # Set pixel
            if c:
                buf[index] |= mask
            else:
                buf[index] &= uint(~mask & 0xFF)
            return 0

    @micropython.viper
    def _hline_mono_vlsb(self, x: int, y: int, w: int, c: int):
        """Horizontal line for MONO_VLSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        byte_row = uint(y >> 3)
        bit_offset = uint(y & 7)
        mask = uint(1 << bit_offset)
        offset = uint(byte_row * stride + x)

        if c:
            # Set bits
            for i in range(w):
                buf[offset + i] |= mask
        else:
            # Clear bits
            inv_mask = uint(~mask & 0xFF)
            for i in range(w):
                buf[offset + i] &= inv_mask

    @micropython.viper
    def _vline_mono_vlsb(self, x: int, y: int, h: int, c: int):
        """Vertical line for MONO_VLSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)

        # Set each pixel in the vertical line
        for i in range(h):
            y_pos = y + i
            byte_offset = uint((y_pos >> 3) * stride + x)
            bit_offset = uint(y_pos & 7)
            mask = uint(1 << bit_offset)

            if c:
                buf[byte_offset] |= mask
            else:
                buf[byte_offset] &= uint(~mask & 0xFF)

    @micropython.viper
    def _fill_rect_mono_vlsb(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for MONO_VLSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Check if this is a full-buffer fill - use optimized path
        if x == 0 and y == 0 and w == width and h == height:
            buf = ptr8(self.buffer)
            buf_len = int(len(self.buffer))
            fill_byte = uint(0xFF if c else 0x00)

            # Fill entire buffer
            for i in range(buf_len):
                buf[i] = fill_byte

            # Handle partial bits in last byte row if height not multiple of 8
            remaining_bits = height & 7
            if remaining_bits and c:
                num_byte_rows = (height + 7) >> 3
                mask = uint((1 << remaining_bits) - 1)
                offset_base = uint((num_byte_rows - 1) * stride)
                for col in range(width):
                    buf[offset_base + col] &= mask
        else:
            # Partial rectangle - use hline for each row (matches C implementation)
            for yy in range(h):
                self._hline_mono_vlsb(x, y + yy, w, c)

    # ====================================================================
    # RGB565 IMPLEMENTATIONS
    # Format 1: 16-bit RGB color, little-endian
    # Buffer size: width * height * 2 bytes
    # Byte index: (y * stride + x) * 2
    # Color format: RRRRRGGGGGGBBBBB (5 red, 6 green, 5 blue)
    # ====================================================================

    @micropython.viper
    def _pixel_rgb565(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for RGB565 format - optimized with ptr16"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check - unsigned comparison handles negative values
        if uint(x) >= uint(width) or uint(y) >= uint(height):
            return 0

        # Use ptr16 for direct 16-bit access (more efficient than byte manipulation)
        buf = ptr16(self.buffer)
        index = uint(y * stride + x)

        if c == -1:  # Get pixel
            return int(buf[index])
        else:  # Set pixel
            buf[index] = uint(c & 0xFFFF)
            return 0

    @micropython.viper
    def _hline_rgb565(self, x: int, y: int, w: int, c: int):
        """Horizontal line for RGB565 format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        offset = uint((y * stride + x) * 2)
        c_low = uint(c & 0xFF)
        c_high = uint((c >> 8) & 0xFF)

        # Write 2 bytes per pixel
        for i in range(w):
            idx = offset + (i * 2)
            buf[idx] = c_low
            buf[idx + 1] = c_high

    @micropython.viper
    def _vline_rgb565(self, x: int, y: int, h: int, c: int):
        """Vertical line for RGB565 format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        c_low = uint(c & 0xFF)
        c_high = uint((c >> 8) & 0xFF)
        row_bytes = uint(stride * 2)

        # Write 2 bytes per pixel, advance by row stride
        for i in range(h):
            offset = uint(((y + i) * stride + x) * 2)
            buf[offset] = c_low
            buf[offset + 1] = c_high

    @micropython.viper
    def _fill_rect_rgb565(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for RGB565 format - optimized with asm_thumb"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Check if this is a full-buffer fill - use optimized asm path
        if x == 0 and y == 0 and w == width and h == height:
            total_pixels = height * stride
            buf_addr = int(addressof(self.buffer))
            _asm_fill_rgb565(buf_addr, total_pixels, c)
        else:
            # Partial fill - use row-by-row approach like C
            buf = ptr16(self.buffer)
            c_val = uint(c & 0xFFFF)
            for yy in range(h):
                offset = uint((y + yy) * stride + x)
                for xx in range(w):
                    buf[offset + xx] = c_val

    # ====================================================================
    # GS4_HMSB IMPLEMENTATIONS
    # Format 2: 4-bit grayscale, horizontal MSB, 2 pixels per byte
    # Buffer size: ((width + 1) // 2) * height bytes
    # Byte index: (y * stride + x) >> 1
    # Even x: upper nibble (bits 7:4)
    # Odd x: lower nibble (bits 3:0)
    # ====================================================================

    @micropython.viper
    def _pixel_gs4_hmsb(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for GS4_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        buf = ptr8(self.buffer)
        index = uint((y * stride + x) >> 1)

        if c == -1:  # Get pixel
            if x & 1:  # Odd x, lower nibble
                return int(buf[index] & 0x0F)
            else:  # Even x, upper nibble
                return int(buf[index] >> 4)
        else:  # Set pixel
            if x & 1:  # Odd x, lower nibble
                buf[index] = uint((buf[index] & 0xF0) | (c & 0x0F))
            else:  # Even x, upper nibble
                buf[index] = uint((buf[index] & 0x0F) | ((c & 0x0F) << 4))
            return 0

    @micropython.viper
    def _hline_gs4_hmsb(self, x: int, y: int, w: int, c: int):
        """Horizontal line for GS4_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        row_offset = uint((y * stride) >> 1)
        c_nibble = uint(c & 0x0F)

        # Three-phase approach: odd start, paired middle, odd end
        i = 0

        # Phase 1: Handle first pixel if x is odd
        if x & 1:
            idx = uint((x + i) >> 1)
            buf[row_offset + idx] = uint((buf[row_offset + idx] & 0xF0) | c_nibble)
            i += 1

        # Phase 2: Handle pixel pairs (write full bytes)
        c_byte = uint((c_nibble << 4) | c_nibble)
        while i + 1 < w:
            idx = uint((x + i) >> 1)
            buf[row_offset + idx] = c_byte
            i += 2

        # Phase 3: Handle last pixel if remaining
        if i < w:
            idx = uint((x + i) >> 1)
            buf[row_offset + idx] = uint((buf[row_offset + idx] & 0x0F) | (c_nibble << 4))

    @micropython.viper
    def _vline_gs4_hmsb(self, x: int, y: int, h: int, c: int):
        """Vertical line for GS4_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        c_nibble = uint(c & 0x0F)
        is_odd = x & 1

        for i in range(h):
            row_offset = uint(((y + i) * stride) >> 1)
            idx = uint(x >> 1)

            if is_odd:  # Odd x, lower nibble
                buf[row_offset + idx] = uint((buf[row_offset + idx] & 0xF0) | c_nibble)
            else:  # Even x, upper nibble
                buf[row_offset + idx] = uint((buf[row_offset + idx] & 0x0F) | (c_nibble << 4))

    @micropython.viper
    def _fill_rect_gs4_hmsb(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for GS4_HMSB format"""
        # Check if full-buffer fill for optimization
        if x == 0 and y == 0 and w == int(self.width) and h == int(self.height):
            buf = ptr8(self.buffer)
            height = int(self.height)
            stride = int(self.stride)
            c_nibble = uint(c & 0x0F)
            c_byte = uint((c_nibble << 4) | c_nibble)
            bytes_per_row = int((stride + 1) >> 1)
            total_bytes = height * bytes_per_row
            for i in range(total_bytes):
                buf[i] = c_byte
        else:
            # Partial rectangle - use hline for each row
            for yy in range(h):
                self._hline_gs4_hmsb(x, y + yy, w, c)

    # ====================================================================
    # MONO_HLSB IMPLEMENTATIONS
    # Format 3: Monochrome, horizontal byte layout, LSB first
    # Buffer size: ((width + 7) // 8) * height bytes
    # Byte index: (y * stride + x) >> 3
    # Bit offset: 7 - (x & 0x07) - NOTE: bit 7 is leftmost pixel!
    # This is the TRICKY one - reversed bit ordering from MONO_HMSB
    # ====================================================================

    @micropython.viper
    def _pixel_mono_hlsb(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for MONO_HLSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        index = uint(y * bytes_per_row + (x >> 3))
        offset = uint(7 - (x & 0x07))  # LSB: bit 7 is leftmost

        if c == -1:  # Get pixel
            return int((buf[index] >> offset) & 1)
        else:  # Set pixel
            if c:
                buf[index] |= uint(1 << offset)
            else:
                buf[index] &= uint(~(1 << offset) & 0xFF)
            return 0

    @micropython.viper
    def _hline_mono_hlsb(self, x: int, y: int, w: int, c: int):
        """Horizontal line for MONO_HLSB format - handles byte spanning"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        row_offset = uint(y * bytes_per_row)

        # Calculate byte and bit positions
        start_byte = uint(x >> 3)
        start_bit = uint(x & 7)
        end_pos = x + w - 1
        end_byte = uint(end_pos >> 3)

        if c:
            # Set pixels
            if start_byte == end_byte:
                # All pixels in one byte
                for i in range(w):
                    bit = uint(7 - ((x + i) & 7))
                    buf[row_offset + start_byte] |= uint(1 << bit)
            else:
                # Handle first partial byte
                for i in range(8 - start_bit):
                    bit = uint(7 - ((x + i) & 7))
                    buf[row_offset + start_byte] |= uint(1 << bit)

                # Handle full bytes in the middle
                for byte_idx in range(start_byte + 1, end_byte):
                    buf[row_offset + byte_idx] = 0xFF

                # Handle last partial byte
                end_bit = int(end_pos & 7)
                for i in range(end_bit + 1):
                    bit = uint(7 - i)
                    buf[row_offset + end_byte] |= uint(1 << bit)
        else:
            # Clear pixels
            if start_byte == end_byte:
                # All pixels in one byte
                for i in range(w):
                    bit = uint(7 - ((x + i) & 7))
                    buf[row_offset + start_byte] &= uint(~(1 << bit) & 0xFF)
            else:
                # Handle first partial byte
                for i in range(8 - start_bit):
                    bit = uint(7 - ((x + i) & 7))
                    buf[row_offset + start_byte] &= uint(~(1 << bit) & 0xFF)

                # Handle full bytes in the middle
                for byte_idx in range(start_byte + 1, end_byte):
                    buf[row_offset + byte_idx] = 0x00

                # Handle last partial byte
                end_bit = int(end_pos & 7)
                for i in range(end_bit + 1):
                    bit = uint(7 - i)
                    buf[row_offset + end_byte] &= uint(~(1 << bit) & 0xFF)

    @micropython.viper
    def _vline_mono_hlsb(self, x: int, y: int, h: int, c: int):
        """Vertical line for MONO_HLSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        byte_in_row = uint(x >> 3)
        bit_offset = uint(7 - (x & 7))
        mask = uint(1 << bit_offset)

        if c:
            for i in range(h):
                row_offset = uint((y + i) * bytes_per_row)
                buf[row_offset + byte_in_row] |= mask
        else:
            inv_mask = uint(~mask & 0xFF)
            for i in range(h):
                row_offset = uint((y + i) * bytes_per_row)
                buf[row_offset + byte_in_row] &= inv_mask

    @micropython.viper
    def _fill_rect_mono_hlsb(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for MONO_HLSB format - optimized with viper"""
        # Check if full-buffer fill for optimization
        if x == 0 and y == 0 and w == int(self.width) and h == int(self.height):
            buf = ptr8(self.buffer)
            height = int(self.height)
            stride = int(self.stride)
            bytes_per_row = int((stride + 7) >> 3)
            fill_byte = uint(0xFF if c else 0x00)

            # Calculate partial pixels in last byte of each row
            partial_pixels = int(stride & 0x07)

            if partial_pixels > 0:
                # Each row has a partial last byte
                # For HLSB: bits 7...(8-partial_pixels) are used
                mask = uint((0xFF << (8 - partial_pixels)) & 0xFF)
                last_byte_fill = uint(fill_byte & mask)

                for row in range(height):
                    offset = uint(row * bytes_per_row)
                    # Fill all full bytes in this row
                    for i in range(bytes_per_row - 1):
                        buf[offset + i] = fill_byte
                    # Fill partial last byte with mask
                    buf[offset + bytes_per_row - 1] = last_byte_fill
            else:
                # All bytes are complete, fast fill
                total_bytes = height * bytes_per_row
                for i in range(total_bytes):
                    buf[i] = fill_byte
        else:
            # Partial rectangle - use hline for each row
            for yy in range(h):
                self._hline_mono_hlsb(x, y + yy, w, c)

    # ====================================================================
    # MONO_HMSB IMPLEMENTATIONS
    # Format 4: Monochrome, horizontal byte layout, MSB first
    # Buffer size: ((width + 7) // 8) * height bytes
    # Byte index: (y * stride + x) >> 3
    # Bit offset: x & 0x07 - NOTE: bit 0 is leftmost pixel!
    # Simpler than HLSB - normal bit ordering
    # ====================================================================

    @micropython.viper
    def _pixel_mono_hmsb(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for MONO_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        index = uint(y * bytes_per_row + (x >> 3))
        offset = uint(x & 0x07)  # HMSB: bit 0 is leftmost

        if c == -1:  # Get pixel
            return int((buf[index] >> offset) & 1)
        else:  # Set pixel
            if c:
                buf[index] |= uint(1 << offset)
            else:
                buf[index] &= uint(~(1 << offset) & 0xFF)
            return 0

    @micropython.viper
    def _hline_mono_hmsb(self, x: int, y: int, w: int, c: int):
        """Horizontal line for MONO_HMSB format - handles byte spanning"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        row_offset = uint(y * bytes_per_row)

        # Calculate byte and bit positions
        start_byte = uint(x >> 3)
        start_bit = uint(x & 7)
        end_pos = x + w - 1
        end_byte = uint(end_pos >> 3)

        if c:
            # Set pixels
            if start_byte == end_byte:
                # All pixels in one byte
                for i in range(w):
                    bit = uint((x + i) & 7)
                    buf[row_offset + start_byte] |= uint(1 << bit)
            else:
                # Handle first partial byte
                for i in range(8 - start_bit):
                    bit = uint((x + i) & 7)
                    buf[row_offset + start_byte] |= uint(1 << bit)

                # Handle full bytes in the middle
                for byte_idx in range(start_byte + 1, end_byte):
                    buf[row_offset + byte_idx] = 0xFF

                # Handle last partial byte
                end_bit = int(end_pos & 7)
                for i in range(end_bit + 1):
                    buf[row_offset + end_byte] |= uint(1 << i)
        else:
            # Clear pixels
            if start_byte == end_byte:
                # All pixels in one byte
                for i in range(w):
                    bit = uint((x + i) & 7)
                    buf[row_offset + start_byte] &= uint(~(1 << bit) & 0xFF)
            else:
                # Handle first partial byte
                for i in range(8 - start_bit):
                    bit = uint((x + i) & 7)
                    buf[row_offset + start_byte] &= uint(~(1 << bit) & 0xFF)

                # Handle full bytes in the middle
                for byte_idx in range(start_byte + 1, end_byte):
                    buf[row_offset + byte_idx] = 0x00

                # Handle last partial byte
                end_bit = int(end_pos & 7)
                for i in range(end_bit + 1):
                    buf[row_offset + end_byte] &= uint(~(1 << i) & 0xFF)

    @micropython.viper
    def _vline_mono_hmsb(self, x: int, y: int, h: int, c: int):
        """Vertical line for MONO_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        byte_in_row = uint(x >> 3)
        bit_offset = uint(x & 7)
        mask = uint(1 << bit_offset)

        if c:
            for i in range(h):
                row_offset = uint((y + i) * bytes_per_row)
                buf[row_offset + byte_in_row] |= mask
        else:
            inv_mask = uint(~mask & 0xFF)
            for i in range(h):
                row_offset = uint((y + i) * bytes_per_row)
                buf[row_offset + byte_in_row] &= inv_mask

    @micropython.viper
    def _fill_rect_mono_hmsb(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for MONO_HMSB format - optimized with viper"""
        # Check if full-buffer fill for optimization
        if x == 0 and y == 0 and w == int(self.width) and h == int(self.height):
            buf = ptr8(self.buffer)
            height = int(self.height)
            stride = int(self.stride)
            bytes_per_row = int((stride + 7) >> 3)
            fill_byte = uint(0xFF if c else 0x00)

            # Calculate partial pixels in last byte of each row
            partial_pixels = int(stride & 0x07)

            if partial_pixels > 0:
                # Each row has a partial last byte
                # For HMSB: bits 0...(partial_pixels-1) are used
                mask = uint((1 << partial_pixels) - 1)
                last_byte_fill = uint(fill_byte & mask)

                for row in range(height):
                    offset = uint(row * bytes_per_row)
                    # Fill all full bytes in this row
                    for i in range(bytes_per_row - 1):
                        buf[offset + i] = fill_byte
                    # Fill partial last byte with mask
                    buf[offset + bytes_per_row - 1] = last_byte_fill
            else:
                # All bytes are complete, fast fill
                total_bytes = height * bytes_per_row
                for i in range(total_bytes):
                    buf[i] = fill_byte
        else:
            # Partial rectangle - use hline for each row
            for yy in range(h):
                self._hline_mono_hmsb(x, y + yy, w, c)

    # ====================================================================
    # GS2_HMSB IMPLEMENTATIONS
    # Format 5: 2-bit grayscale, horizontal MSB, 4 pixels per byte
    # Buffer size: ((width + 3) // 4) * height bytes
    # Byte index: (y * stride + x) >> 2
    # Shift: (x & 0x3) << 1
    # Each pixel uses 2 bits, packed 4 per byte
    # ====================================================================

    @micropython.viper
    def _pixel_gs2_hmsb(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for GS2_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        buf = ptr8(self.buffer)
        index = uint((y * stride + x) >> 2)
        shift = uint((x & 0x3) << 1)
        mask = uint(0x3 << shift)

        if c == -1:  # Get pixel
            return int((buf[index] >> shift) & 0x3)
        else:  # Set pixel
            color = uint((c & 0x3) << shift)
            buf[index] = uint((buf[index] & ~mask) | color)
            return 0

    @micropython.viper
    def _hline_gs2_hmsb(self, x: int, y: int, w: int, c: int):
        """Horizontal line for GS2_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        row_offset = uint((y * stride) >> 2)
        c_bits = uint(c & 0x3)

        # Set pixels one by one (simpler and safer for 2-bit format)
        for i in range(w):
            x_pos = x + i
            idx = uint(x_pos >> 2)
            shift = uint((x_pos & 0x3) << 1)
            mask = uint(0x3 << shift)
            color = uint(c_bits << shift)
            buf[row_offset + idx] = uint((buf[row_offset + idx] & ~mask) | color)

    @micropython.viper
    def _vline_gs2_hmsb(self, x: int, y: int, h: int, c: int):
        """Vertical line for GS2_HMSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        c_bits = uint(c & 0x3)
        shift = uint((x & 0x3) << 1)
        mask = uint(0x3 << shift)
        color = uint(c_bits << shift)
        byte_in_row = uint(x >> 2)

        for i in range(h):
            row_offset = uint(((y + i) * stride) >> 2)
            buf[row_offset + byte_in_row] = uint((buf[row_offset + byte_in_row] & ~mask) | color)

    @micropython.viper
    def _fill_rect_gs2_hmsb(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for GS2_HMSB format"""
        # Check if full-buffer fill for optimization
        if x == 0 and y == 0 and w == int(self.width) and h == int(self.height):
            buf = ptr8(self.buffer)
            height = int(self.height)
            stride = int(self.stride)
            c_bits = uint(c & 0x3)
            c_byte = uint((c_bits << 6) | (c_bits << 4) | (c_bits << 2) | c_bits)
            bytes_per_row = int((stride + 3) >> 2)
            total_bytes = height * bytes_per_row
            for i in range(total_bytes):
                buf[i] = c_byte
        else:
            # Partial rectangle - use hline for each row
            for yy in range(h):
                self._hline_gs2_hmsb(x, y + yy, w, c)

    # ====================================================================
    # GS8 IMPLEMENTATIONS
    # Format 6: 8-bit grayscale
    # Buffer size: width * height bytes
    # Byte index: y * stride + x
    # Simplest format: 1 byte per pixel, direct addressing
    # ====================================================================

    @micropython.viper
    def _pixel_gs8(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for GS8 format - optimized"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check - unsigned comparison handles negative values
        if uint(x) >= uint(width) or uint(y) >= uint(height):
            return 0

        buf = ptr8(self.buffer)
        index = uint(y * stride + x)

        if c == -1:  # Get pixel
            return int(buf[index])
        else:  # Set pixel
            buf[index] = uint(c & 0xFF)
            return 0

    @micropython.viper
    def _hline_gs8(self, x: int, y: int, w: int, c: int):
        """Horizontal line for GS8 format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        offset = uint(y * stride + x)
        c_byte = uint(c & 0xFF)

        # Simple sequential byte writes
        for i in range(w):
            buf[offset + i] = c_byte

    @micropython.viper
    def _vline_gs8(self, x: int, y: int, h: int, c: int):
        """Vertical line for GS8 format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check and clip
        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        c_byte = uint(c & 0xFF)

        # Write 1 byte per pixel, advance by stride
        for i in range(h):
            offset = uint((y + i) * stride + x)
            buf[offset] = c_byte

    @micropython.viper
    def _fill_rect_gs8(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for GS8 format - optimized with asm_thumb"""
        height = int(self.height)
        stride = int(self.stride)
        c_byte = int(c & 0xFF)

        # Check if this is a full-buffer fill - use optimized asm path
        if x == 0 and y == 0 and w == int(self.width) and h == height:
            total_bytes = height * stride
            buf_addr = int(addressof(self.buffer))
            _asm_fill_byte(buf_addr, total_bytes, c_byte)
        else:
            # Partial fill - use memset per row like C implementation
            for yy in range(h):
                offset = uint((y + yy) * stride + x)
                # Fill this row using asm helper for speed
                buf_addr = int(addressof(self.buffer)) + offset
                _asm_fill_byte(buf_addr, w, c_byte)
