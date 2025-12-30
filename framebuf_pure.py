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

        # Early bounds check (match C implementation lines 748-756)
        if (x >= self.width or
            y >= self.height or
            -x >= src_width or
            -y >= src_height):
            # Completely out of bounds, no-op
            return

        # Calculate clipping (match C implementation lines 758-764)
        x0 = max(0, x)              # destination start X (clipped)
        y0 = max(0, y)              # destination start Y (clipped)
        x1 = max(0, -x)             # source start X offset
        y1 = max(0, -y)             # source start Y offset
        x0end = min(self.width, x + src_width)      # destination end X
        y0end = min(self.height, y + src_height)    # destination end Y

        # Blit loop (match C implementation lines 766-779)
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



class FrameBufferMONO_VLSB(FrameBuffer):
    """FrameBuffer for MONO_VLSB format"""
    FORMAT = MONO_VLSB

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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



class FrameBufferRGB565(FrameBuffer):
    """FrameBuffer for RGB565 format"""
    FORMAT = RGB565

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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



class FrameBufferGS4_HMSB(FrameBuffer):
    """FrameBuffer for GS4_HMSB format"""
    FORMAT = GS4_HMSB

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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



class FrameBufferMONO_HLSB(FrameBuffer):
    """FrameBuffer for MONO_HLSB format"""
    FORMAT = MONO_HLSB

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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



class FrameBufferMONO_HMSB(FrameBuffer):
    """FrameBuffer for MONO_HMSB format"""
    FORMAT = MONO_HMSB

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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



class FrameBufferGS2_HMSB(FrameBuffer):
    """FrameBuffer for GS2_HMSB format"""
    FORMAT = GS2_HMSB

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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



class FrameBufferGS8(FrameBuffer):
    """FrameBuffer for GS8 format"""
    FORMAT = GS8

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
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
    def hline(self, x: int, y: int, w: int, c: int):
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
    def vline(self, x: int, y: int, h: int, c: int):
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
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
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


# ====================================================================
# FACTORY FUNCTION FOR C API COMPATIBILITY
# ====================================================================

_FRAMEBUFFER_CLASSES = {
    MONO_VLSB: FrameBufferMONO_VLSB,
    RGB565: FrameBufferRGB565,
    GS4_HMSB: FrameBufferGS4_HMSB,
    MONO_HLSB: FrameBufferMONO_HLSB,
    MONO_HMSB: FrameBufferMONO_HMSB,
    GS2_HMSB: FrameBufferGS2_HMSB,
    GS8: FrameBufferGS8,
}

def _create_framebuffer(buffer, width, height, format, stride=None):
    """Factory function - creates appropriate subclass based on format"""
    # Validate parameters (match C implementation lines 280-282)
    if stride is None:
        stride = width

    if width < 1 or height < 1 or width > 0xffff or height > 0xffff or stride > 0xffff or stride < width:
        raise ValueError("Invalid framebuffer dimensions")

    # Calculate required buffer size (match C implementation lines 284-317, 322-323)
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

    cls = _FRAMEBUFFER_CLASSES[format]
    return cls(buffer, width, height, stride)

# Shadow FrameBuffer name with factory for C API compatibility
FrameBuffer = _create_framebuffer
