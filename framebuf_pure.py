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

    # ====================================================================
    # PUBLIC API
    # ====================================================================

    def pixel(self, x, y, c=-1):
        """
        Get or set pixel value at (x, y)

        Args:
            x: X coordinate
            y: Y coordinate
            c: Color value (optional). If omitted, returns current pixel value.
               If provided, sets pixel to this color.

        Returns:
            Current pixel value (if c not provided), or 0 (if c provided)
        """
        if self.format == MONO_VLSB:
            return self._pixel_mono_vlsb(x, y, c)
        elif self.format == RGB565:
            return self._pixel_rgb565(x, y, c)
        elif self.format == GS4_HMSB:
            return self._pixel_gs4_hmsb(x, y, c)
        elif self.format == MONO_HLSB:
            return self._pixel_mono_hlsb(x, y, c)
        elif self.format == MONO_HMSB:
            return self._pixel_mono_hmsb(x, y, c)
        elif self.format == GS2_HMSB:
            return self._pixel_gs2_hmsb(x, y, c)
        elif self.format == GS8:
            return self._pixel_gs8(x, y, c)
        return 0

    def hline(self, x, y, w, c):
        """
        Draw horizontal line starting at (x, y) with width w and color c

        Args:
            x: Starting X coordinate
            y: Y coordinate
            w: Width in pixels
            c: Color value
        """
        if self.format == MONO_VLSB:
            self._hline_mono_vlsb(x, y, w, c)
        elif self.format == RGB565:
            self._hline_rgb565(x, y, w, c)
        elif self.format == GS4_HMSB:
            self._hline_gs4_hmsb(x, y, w, c)
        elif self.format == MONO_HLSB:
            self._hline_mono_hlsb(x, y, w, c)
        elif self.format == MONO_HMSB:
            self._hline_mono_hmsb(x, y, w, c)
        elif self.format == GS2_HMSB:
            self._hline_gs2_hmsb(x, y, w, c)
        elif self.format == GS8:
            self._hline_gs8(x, y, w, c)

    def vline(self, x, y, h, c):
        """
        Draw vertical line starting at (x, y) with height h and color c

        Args:
            x: X coordinate
            y: Starting Y coordinate
            h: Height in pixels
            c: Color value
        """
        if self.format == MONO_VLSB:
            self._vline_mono_vlsb(x, y, h, c)
        elif self.format == RGB565:
            self._vline_rgb565(x, y, h, c)
        elif self.format == GS4_HMSB:
            self._vline_gs4_hmsb(x, y, h, c)
        elif self.format == MONO_HLSB:
            self._vline_mono_hlsb(x, y, h, c)
        elif self.format == MONO_HMSB:
            self._vline_mono_hmsb(x, y, h, c)
        elif self.format == GS2_HMSB:
            self._vline_gs2_hmsb(x, y, h, c)
        elif self.format == GS8:
            self._vline_gs8(x, y, h, c)

    def fill(self, c):
        """
        Fill entire framebuffer with color c

        Args:
            c: Color value
        """
        if self.format == MONO_VLSB:
            self._fill_mono_vlsb(c)
        elif self.format == RGB565:
            self._fill_rgb565(c)
        elif self.format == GS4_HMSB:
            self._fill_gs4_hmsb(c)
        elif self.format == MONO_HLSB:
            self._fill_mono_hlsb(c)
        elif self.format == MONO_HMSB:
            self._fill_mono_hmsb(c)
        elif self.format == GS2_HMSB:
            self._fill_gs2_hmsb(c)
        elif self.format == GS8:
            self._fill_gs8(c)

    # ====================================================================
    # MONO_VLSB IMPLEMENTATIONS
    # Format 0: Monochrome, vertical byte layout, LSB first
    # Buffer size: ((height + 7) // 8) * width bytes
    # Byte index: (y >> 3) * stride + x
    # Bit offset: y & 0x07 (bit 0 = top, bit 7 = bottom of byte)
    # ====================================================================

    @micropython.viper
    def _pixel_mono_vlsb(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for MONO_VLSB format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        buf = ptr8(self.buffer)
        index = uint((y >> 3) * stride + x)
        offset = uint(y & 0x07)

        if c == -1:  # Get pixel
            return int((buf[index] >> offset) & 1)
        else:  # Set pixel
            if c:
                buf[index] |= uint(1 << offset)
            else:
                buf[index] &= uint(~(1 << offset) & 0xFF)
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
    def _fill_mono_vlsb(self, c: int):
        """Fill for MONO_VLSB format"""
        buf = ptr8(self.buffer)
        buf_len = int(len(self.buffer))
        height = int(self.height)
        width = int(self.width)
        stride = int(self.stride)

        fill_byte = uint(0xFF if c else 0x00)

        # Fill entire buffer
        for i in range(buf_len):
            buf[i] = fill_byte

        # Handle partial bits in last byte row if height not multiple of 8
        remaining_bits = height & 7
        if remaining_bits:
            num_byte_rows = (height + 7) >> 3
            if c:
                # Mask off unused bits in last byte row
                mask = uint((1 << remaining_bits) - 1)
                offset_base = uint((num_byte_rows - 1) * stride)

                for col in range(width):
                    buf[offset_base + col] = mask
            # If c is 0, already filled with 0x00, so partial bits are correct

    # ====================================================================
    # RGB565 IMPLEMENTATIONS
    # Format 1: 16-bit RGB color, little-endian
    # Buffer size: width * height * 2 bytes
    # Byte index: (y * stride + x) * 2
    # Color format: RRRRRGGGGGGBBBBB (5 red, 6 green, 5 blue)
    # ====================================================================

    @micropython.viper
    def _pixel_rgb565(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for RGB565 format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        buf = ptr8(self.buffer)
        index = uint((y * stride + x) * 2)

        if c == -1:  # Get pixel
            return int(buf[index] | (buf[index + 1] << 8))
        else:  # Set pixel
            buf[index] = uint(c & 0xFF)
            buf[index + 1] = uint((c >> 8) & 0xFF)
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
    def _fill_rgb565(self, c: int):
        """Fill for RGB565 format"""
        buf = ptr8(self.buffer)
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        c_low = uint(c & 0xFF)
        c_high = uint((c >> 8) & 0xFF)

        # Fill entire buffer with 2-byte pattern
        for y in range(height):
            for x in range(width):
                offset = uint((y * stride + x) * 2)
                buf[offset] = c_low
                buf[offset + 1] = c_high

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
    def _fill_gs4_hmsb(self, c: int):
        """Fill for GS4_HMSB format"""
        buf = ptr8(self.buffer)
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        c_nibble = uint(c & 0x0F)
        c_byte = uint((c_nibble << 4) | c_nibble)

        bytes_per_row = int((stride + 1) >> 1)

        # Fill entire buffer with doubled nibble pattern
        for y in range(height):
            row_offset = uint(y * bytes_per_row)
            for x in range(bytes_per_row):
                buf[row_offset + x] = c_byte

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
    def _fill_mono_hlsb(self, c: int):
        """Fill for MONO_HLSB format"""
        buf = ptr8(self.buffer)
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        bytes_per_row = int((stride + 7) >> 3)
        fill_byte = uint(0xFF if c else 0x00)

        # Fill all bytes
        for y in range(height):
            row_offset = uint(y * bytes_per_row)
            for x in range(bytes_per_row):
                buf[row_offset + x] = fill_byte

        # Handle partial bits in last byte of each row if width not multiple of 8
        remaining_bits = stride & 7
        if remaining_bits and c:
            # Mask off unused bits in last byte of each row
            last_byte_idx = bytes_per_row - 1
            # For HLSB, used bits are in upper part of byte
            mask = uint((0xFF << (8 - remaining_bits)) & 0xFF)

            for y in range(height):
                row_offset = uint(y * bytes_per_row)
                buf[row_offset + last_byte_idx] = mask

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
    def _fill_mono_hmsb(self, c: int):
        """Fill for MONO_HMSB format"""
        buf = ptr8(self.buffer)
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        bytes_per_row = int((stride + 7) >> 3)
        fill_byte = uint(0xFF if c else 0x00)

        # Fill all bytes
        for y in range(height):
            row_offset = uint(y * bytes_per_row)
            for x in range(bytes_per_row):
                buf[row_offset + x] = fill_byte

        # Handle partial bits in last byte of each row if width not multiple of 8
        remaining_bits = stride & 7
        if remaining_bits and c:
            # Mask off unused bits in last byte of each row
            last_byte_idx = bytes_per_row - 1
            # For HMSB, used bits are in lower part of byte (bits 0 to remaining_bits-1)
            mask = uint((1 << remaining_bits) - 1)

            for y in range(height):
                row_offset = uint(y * bytes_per_row)
                buf[row_offset + last_byte_idx] = mask

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
    def _fill_gs2_hmsb(self, c: int):
        """Fill for GS2_HMSB format"""
        buf = ptr8(self.buffer)
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        c_bits = uint(c & 0x3)
        # Replicate 2-bit value across all 4 positions in byte
        c_byte = uint((c_bits << 6) | (c_bits << 4) | (c_bits << 2) | c_bits)

        bytes_per_row = int((stride + 3) >> 2)

        # Fill entire buffer
        for y in range(height):
            row_offset = uint(y * bytes_per_row)
            for x in range(bytes_per_row):
                buf[row_offset + x] = c_byte

    # ====================================================================
    # GS8 IMPLEMENTATIONS
    # Format 6: 8-bit grayscale
    # Buffer size: width * height bytes
    # Byte index: y * stride + x
    # Simplest format: 1 byte per pixel, direct addressing
    # ====================================================================

    @micropython.viper
    def _pixel_gs8(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for GS8 format"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check
        if x < 0 or x >= width or y < 0 or y >= height:
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
    def _fill_gs8(self, c: int):
        """Fill for GS8 format"""
        buf = ptr8(self.buffer)
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        c_byte = uint(c & 0xFF)

        # Fill entire buffer
        for y in range(height):
            offset = uint(y * stride)
            for x in range(width):
                buf[offset + x] = c_byte
