"""
Pure MicroPython Framebuffer Implementation
Comparable to the built-in C framebuffer module, optimized with @micropython.native and @micropython.viper
"""
import micropython
import framebuf
from uctypes import addressof


class FrameBufferPure:
    """Pure MicroPython framebuffer implementation with native/viper optimizations"""

    def __init__(self, buffer, width, height, format):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format

        # Calculate bits per pixel based on format
        if format == framebuf.MONO_VLSB or format == framebuf.MONO_HLSB:
            self.bpp = 1
        elif format == framebuf.RGB565:
            self.bpp = 16
        elif format == framebuf.GS4_HMSB:
            self.bpp = 4
        elif format == framebuf.GS8:
            self.bpp = 8
        else:
            self.bpp = 1  # default

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
        """Set or get pixel value using viper for maximum performance"""
        w = int(self.width)
        h = int(self.height)

        # Bounds check
        if x < 0 or x >= w or y < 0 or y >= h:
            return 0

        buf = ptr8(self.buffer)
        fmt = int(self.format)

        # MONO_VLSB format (most common for small displays)
        if fmt == 0:  # framebuf.MONO_VLSB
            byte_offset = (y >> 3) * w + x
            bit_offset = y & 7

            if c == -1:  # Get pixel
                return (buf[byte_offset] >> bit_offset) & 1
            else:  # Set pixel
                if c:
                    buf[byte_offset] |= (1 << bit_offset)
                else:
                    buf[byte_offset] &= ~(1 << bit_offset)
                return 0

        # RGB565 format
        elif fmt == 1:  # framebuf.RGB565
            offset = (y * w + x) * 2
            if c == -1:  # Get pixel
                return buf[offset] | (buf[offset + 1] << 8)
            else:  # Set pixel
                buf[offset] = c & 0xFF
                buf[offset + 1] = (c >> 8) & 0xFF
                return 0

        # GS8 format
        elif fmt == 5:  # framebuf.GS8
            offset = y * w + x
            if c == -1:  # Get pixel
                return buf[offset]
            else:  # Set pixel
                buf[offset] = c & 0xFF
                return 0

        return 0

    @micropython.native
    def fill(self, c: int):
        """Fill entire framebuffer with color"""
        if self.format == framebuf.MONO_VLSB:
            # For MONO_VLSB, we need to set all pixels, respecting display geometry
            num_byte_rows = (self.height + 7) // 8
            remaining_bits = self.height % 8

            if c:
                # Fill with 1s
                for col in range(self.width):
                    for byte_row in range(num_byte_rows):
                        offset = byte_row * self.width + col
                        if byte_row == num_byte_rows - 1 and remaining_bits != 0:
                            # Last byte row with partial bits
                            self.buffer[offset] = (1 << remaining_bits) - 1
                        else:
                            # Full byte
                            self.buffer[offset] = 0xFF
            else:
                # Fill with 0s
                for i in range(len(self.buffer)):
                    self.buffer[i] = 0x00

        elif self.format == framebuf.MONO_HLSB:
            # Similar logic for MONO_HLSB (horizontal orientation)
            if c:
                for i in range(len(self.buffer)):
                    self.buffer[i] = 0xFF
                # Handle last byte of each row if width not multiple of 8
                remaining_bits = self.width % 8
                if remaining_bits != 0:
                    mask = (1 << remaining_bits) - 1
                    bytes_per_row = (self.width + 7) // 8
                    for row in range(self.height):
                        self.buffer[row * bytes_per_row + bytes_per_row - 1] = mask
            else:
                for i in range(len(self.buffer)):
                    self.buffer[i] = 0x00

        elif self.format == framebuf.RGB565:
            for i in range(0, len(self.buffer), 2):
                self.buffer[i] = c & 0xFF
                self.buffer[i + 1] = (c >> 8) & 0xFF
        elif self.format == framebuf.GS8:
            for i in range(len(self.buffer)):
                self.buffer[i] = c & 0xFF

    @micropython.viper
    def hline(self, x: int, y: int, w: int, c: int):
        """Draw horizontal line using viper"""
        fb_w = int(self.width)
        fb_h = int(self.height)

        # Bounds check and clip
        if y < 0 or y >= fb_h or x >= fb_w:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > fb_w:
            w = fb_w - x

        if w <= 0:
            return

        buf = ptr8(self.buffer)
        fmt = int(self.format)

        # MONO_VLSB format
        if fmt == 0:  # framebuf.MONO_VLSB
            byte_row = y >> 3
            bit_offset = y & 7
            mask = 1 << bit_offset

            offset = byte_row * fb_w + x

            if c:
                for i in range(w):
                    buf[offset + i] |= mask
            else:
                inv_mask = ~mask & 0xFF
                for i in range(w):
                    buf[offset + i] &= inv_mask

        # RGB565 format
        elif fmt == 1:  # framebuf.RGB565
            offset = (y * fb_w + x) * 2
            c_low = c & 0xFF
            c_high = (c >> 8) & 0xFF

            for i in range(w):
                buf[offset] = c_low
                buf[offset + 1] = c_high
                offset += 2

        # GS8 format
        elif fmt == 5:  # framebuf.GS8
            offset = y * fb_w + x
            color = c & 0xFF
            for i in range(w):
                buf[offset + i] = color

    @micropython.viper
    def vline(self, x: int, y: int, h: int, c: int):
        """Draw vertical line using viper"""
        fb_w = int(self.width)
        fb_h = int(self.height)

        # Bounds check and clip
        if x < 0 or x >= fb_w or y >= fb_h:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > fb_h:
            h = fb_h - y

        if h <= 0:
            return

        buf = ptr8(self.buffer)
        fmt = int(self.format)

        # MONO_VLSB format
        if fmt == 0:  # framebuf.MONO_VLSB
            for row in range(h):
                current_y = y + row
                byte_offset = (current_y >> 3) * fb_w + x
                bit_offset = current_y & 7

                if c:
                    buf[byte_offset] |= (1 << bit_offset)
                else:
                    buf[byte_offset] &= ~(1 << bit_offset)

        # RGB565 format
        elif fmt == 1:  # framebuf.RGB565
            c_low = c & 0xFF
            c_high = (c >> 8) & 0xFF

            for row in range(h):
                offset = ((y + row) * fb_w + x) * 2
                buf[offset] = c_low
                buf[offset + 1] = c_high

        # GS8 format
        elif fmt == 5:  # framebuf.GS8
            color = c & 0xFF
            for row in range(h):
                buf[(y + row) * fb_w + x] = color

    @micropython.native
    def rect(self, x: int, y: int, w: int, h: int, c: int, fill_rect: bool = False):
        """Draw rectangle (filled or outline)"""
        if fill_rect:
            for row in range(h):
                self.hline(x, y + row, w, c)
        else:
            self.hline(x, y, w, c)
            self.hline(x, y + h - 1, w, c)
            self.vline(x, y, h, c)
            self.vline(x + w - 1, y, h, c)

    @micropython.native
    def fill_rect(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle"""
        for row in range(h):
            self.hline(x, y + row, w, c)

    @micropython.native
    def line(self, x0: int, y0: int, x1: int, y1: int, c: int):
        """Draw line using Bresenham's algorithm"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.pixel(x0, y0, c)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy


class FrameBufferNative:
    """Pure MicroPython framebuffer using @micropython.native (less aggressive optimization)"""

    def __init__(self, buffer, width, height, format):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format

        if format == framebuf.MONO_VLSB or format == framebuf.MONO_HLSB:
            self.bpp = 1
        elif format == framebuf.RGB565:
            self.bpp = 16
        elif format == framebuf.GS4_HMSB:
            self.bpp = 4
        elif format == framebuf.GS8:
            self.bpp = 8
        else:
            self.bpp = 1

    @micropython.native
    def pixel(self, x: int, y: int, c: int = -1) -> int:
        """Set or get pixel value"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return 0

        # MONO_VLSB format
        if self.format == framebuf.MONO_VLSB:
            byte_offset = (y >> 3) * self.width + x
            bit_offset = y & 7

            if c == -1:
                return (self.buffer[byte_offset] >> bit_offset) & 1
            else:
                if c:
                    self.buffer[byte_offset] |= (1 << bit_offset)
                else:
                    self.buffer[byte_offset] &= ~(1 << bit_offset)
                return 0

        # RGB565 format
        elif self.format == framebuf.RGB565:
            offset = (y * self.width + x) * 2
            if c == -1:
                return self.buffer[offset] | (self.buffer[offset + 1] << 8)
            else:
                self.buffer[offset] = c & 0xFF
                self.buffer[offset + 1] = (c >> 8) & 0xFF
                return 0

        # GS8 format
        elif self.format == framebuf.GS8:
            offset = y * self.width + x
            if c == -1:
                return self.buffer[offset]
            else:
                self.buffer[offset] = c & 0xFF
                return 0

        return 0

    @micropython.native
    def fill(self, c: int):
        """Fill entire framebuffer"""
        if self.format == framebuf.MONO_VLSB:
            # For MONO_VLSB, we need to set all pixels, respecting display geometry
            num_byte_rows = (self.height + 7) // 8
            remaining_bits = self.height % 8

            if c:
                # Fill with 1s
                for col in range(self.width):
                    for byte_row in range(num_byte_rows):
                        offset = byte_row * self.width + col
                        if byte_row == num_byte_rows - 1 and remaining_bits != 0:
                            # Last byte row with partial bits
                            self.buffer[offset] = (1 << remaining_bits) - 1
                        else:
                            # Full byte
                            self.buffer[offset] = 0xFF
            else:
                # Fill with 0s
                for i in range(len(self.buffer)):
                    self.buffer[i] = 0x00

        elif self.format == framebuf.MONO_HLSB:
            # Similar logic for MONO_HLSB (horizontal orientation)
            if c:
                for i in range(len(self.buffer)):
                    self.buffer[i] = 0xFF
                # Handle last byte of each row if width not multiple of 8
                remaining_bits = self.width % 8
                if remaining_bits != 0:
                    mask = (1 << remaining_bits) - 1
                    bytes_per_row = (self.width + 7) // 8
                    for row in range(self.height):
                        self.buffer[row * bytes_per_row + bytes_per_row - 1] = mask
            else:
                for i in range(len(self.buffer)):
                    self.buffer[i] = 0x00

        elif self.format == framebuf.RGB565:
            for i in range(0, len(self.buffer), 2):
                self.buffer[i] = c & 0xFF
                self.buffer[i + 1] = (c >> 8) & 0xFF
        elif self.format == framebuf.GS8:
            for i in range(len(self.buffer)):
                self.buffer[i] = c & 0xFF

    @micropython.native
    def hline(self, x: int, y: int, w: int, c: int):
        """Draw horizontal line"""
        if y < 0 or y >= self.height or x >= self.width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > self.width:
            w = self.width - x

        if w <= 0:
            return

        for i in range(w):
            self.pixel(x + i, y, c)

    @micropython.native
    def vline(self, x: int, y: int, h: int, c: int):
        """Draw vertical line"""
        if x < 0 or x >= self.width or y >= self.height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > self.height:
            h = self.height - y

        if h <= 0:
            return

        for i in range(h):
            self.pixel(x, y + i, c)

    @micropython.native
    def rect(self, x: int, y: int, w: int, h: int, c: int, fill_rect: bool = False):
        """Draw rectangle"""
        if fill_rect:
            for row in range(h):
                self.hline(x, y + row, w, c)
        else:
            self.hline(x, y, w, c)
            self.hline(x, y + h - 1, w, c)
            self.vline(x, y, h, c)
            self.vline(x + w - 1, y, h, c)

    @micropython.native
    def fill_rect(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle"""
        for row in range(h):
            self.hline(x, y + row, w, c)

    @micropython.native
    def line(self, x0: int, y0: int, x1: int, y1: int, c: int):
        """Draw line using Bresenham's algorithm"""
        dx = abs(x1 - x0)
        dy = abs(y1 - y0)
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        while True:
            self.pixel(x0, y0, c)

            if x0 == x1 and y0 == y1:
                break

            e2 = 2 * err
            if e2 > -dy:
                err -= dy
                x0 += sx
            if e2 < dx:
                err += dx
                y0 += sy


class FrameBufferAsmThumb:
    """Pure MicroPython framebuffer using @micropython.asm_thumb for ARM assembly optimization"""

    def __init__(self, buffer, width, height, format):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format

        if format == framebuf.MONO_VLSB or format == framebuf.MONO_HLSB:
            self.bpp = 1
        elif format == framebuf.RGB565:
            self.bpp = 16
        elif format == framebuf.GS4_HMSB:
            self.bpp = 4
        elif format == framebuf.GS8:
            self.bpp = 8
        else:
            self.bpp = 1

    @micropython.native
    def pixel(self, x: int, y: int, c: int = -1) -> int:
        """Set or get pixel value - using native for compatibility"""
        if x < 0 or x >= self.width or y < 0 or y >= self.height:
            return 0

        # MONO_VLSB format
        if self.format == framebuf.MONO_VLSB:
            byte_offset = (y >> 3) * self.width + x
            bit_offset = y & 7

            if c == -1:
                return (self.buffer[byte_offset] >> bit_offset) & 1
            else:
                if c:
                    self.buffer[byte_offset] |= (1 << bit_offset)
                else:
                    self.buffer[byte_offset] &= ~(1 << bit_offset)
                return 0

        # RGB565 format
        elif self.format == framebuf.RGB565:
            offset = (y * self.width + x) * 2
            if c == -1:
                return self.buffer[offset] | (self.buffer[offset + 1] << 8)
            else:
                self.buffer[offset] = c & 0xFF
                self.buffer[offset + 1] = (c >> 8) & 0xFF
                return 0

        # GS8 format
        elif self.format == framebuf.GS8:
            offset = y * self.width + x
            if c == -1:
                return self.buffer[offset]
            else:
                self.buffer[offset] = c & 0xFF
                return 0

        return 0

    # Assembly helper for fast memory fill (byte-by-byte)
    @staticmethod
    @micropython.asm_thumb
    def _asm_memset(r0, r1, r2):
        # r0 = buffer address
        # r1 = value to fill
        # r2 = number of bytes
        label(LOOP)
        cmp(r2, 0)
        beq(END)
        strb(r1, [r0, 0])
        add(r0, 1)
        sub(r2, 1)
        b(LOOP)
        label(END)

    # Ultra-fast memory fill using 32-bit word writes (4x faster than byte writes)
    @staticmethod
    @micropython.asm_thumb
    def _asm_memset32(r0, r1, r2):
        # r0 = buffer address (should be 4-byte aligned for best performance)
        # r1 = byte value (0x00-0xFF)
        # r2 = number of bytes

        # Replicate byte to 32-bit word: 0xFF -> 0xFFFFFFFF
        mov(r3, r1)
        lsl(r3, r3, 8)
        orr(r1, r3)      # r1 = 0x__FF__FF
        mov(r3, r1)
        lsl(r3, r3, 16)
        orr(r1, r3)      # r1 = 0xFFFFFFFF

        # Calculate word count (r2 >> 2)
        lsr(r3, r2, 2)   # r3 = number of 32-bit words

        # Process 32-bit words (main loop)
        label(WORD_LOOP)
        cmp(r3, 0)
        beq(BYTE_REMAINDER)
        str(r1, [r0, 0])  # 32-bit write (4x faster!)
        add(r0, r0, 4)
        sub(r3, r3, 1)
        b(WORD_LOOP)

        # Handle remaining 0-3 bytes
        label(BYTE_REMAINDER)
        mov(r4, 3)        # Load constant 3 into r4
        and_(r2, r4)      # r2 &= 3 (bytes % 4)
        cmp(r2, 0)
        beq(END)

        label(BYTE_LOOP)
        strb(r1, [r0, 0])
        add(r0, r0, 1)
        sub(r2, r2, 1)
        cmp(r2, 0)
        bne(BYTE_LOOP)

        label(END)

    # Assembly helper for horizontal line in MONO_VLSB
    @staticmethod
    @micropython.asm_thumb
    def _asm_hline_mono_vlsb_set(r0, r1, r2, r3):
        # r0 = buffer base address
        # r1 = starting offset
        # r2 = mask (bit to set)
        # r3 = width (number of pixels)
        label(LOOP)
        cmp(r3, 0)
        beq(END)
        add(r0, r0, r1)  # buffer[offset] (r0 = r0 + r1)
        ldrb(r4, [r0, 0])
        mov(r5, r4)      # Save original
        orr(r5, r2)      # r5 |= r2 (set bit)
        strb(r5, [r0, 0])
        sub(r0, r0, r1)  # Restore base (r0 = r0 - r1)
        add(r1, 1)       # Next byte
        sub(r3, 1)       # Decrement counter
        b(LOOP)
        label(END)

    # Ultra-fast row fill for fill_rect optimization (MONO_VLSB)
    @staticmethod
    @micropython.asm_thumb
    def _asm_fill_row_mono(r0, r1, r2):
        # r0 = buffer address at row start offset
        # r1 = width in bytes
        # r2 = fill value (0x00 or 0xFF)

        # For small widths, use byte loop
        cmp(r1, 4)
        blt(BYTE_FILL)

        # Replicate byte to 32-bit word
        mov(r3, r2)
        lsl(r3, r3, 8)
        orr(r2, r3)      # r2 = 0x__FF__FF
        mov(r3, r2)
        lsl(r3, r3, 16)
        orr(r2, r3)      # r2 = 0xFFFFFFFF

        # Calculate word count
        lsr(r3, r1, 2)   # r3 = bytes / 4

        # Word loop for bulk of data
        label(WORD_FILL)
        cmp(r3, 0)
        beq(BYTE_REMAINDER)
        str(r2, [r0, 0])
        add(r0, r0, 4)
        sub(r3, r3, 1)
        b(WORD_FILL)

        # Handle remainder bytes
        label(BYTE_REMAINDER)
        mov(r4, 3)        # Load constant 3 into r4
        and_(r1, r4)      # r1 &= 3 (bytes % 4)
        cmp(r1, 0)
        beq(END)

        # Byte fill for remainder or small widths
        label(BYTE_FILL)
        cmp(r1, 0)
        beq(END)
        strb(r2, [r0, 0])
        add(r0, r0, 1)
        sub(r1, r1, 1)
        b(BYTE_FILL)

        label(END)

    @micropython.native
    def fill(self, c: int):
        """Fill entire framebuffer with color - optimized with asm_thumb helpers"""
        if self.format == framebuf.MONO_VLSB:
            # For MONO_VLSB, we need to set all pixels, respecting display geometry
            num_byte_rows = (self.height + 7) // 8
            remaining_bits = self.height % 8

            if c:
                # Fill with 1s - use optimized memset32
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0xFF, len(self.buffer))

                # Handle partial bits in last byte row if needed
                if remaining_bits != 0:
                    mask = (1 << remaining_bits) - 1
                    for col in range(self.width):
                        offset = (num_byte_rows - 1) * self.width + col
                        self.buffer[offset] = mask
            else:
                # Fill with 0s - use 32-bit word assembly helper for maximum speed
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0, len(self.buffer))

        elif self.format == framebuf.MONO_HLSB:
            # Similar logic for MONO_HLSB
            if c:
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0xFF, len(self.buffer))
                # Handle last byte of each row if width not multiple of 8
                remaining_bits = self.width % 8
                if remaining_bits != 0:
                    mask = (1 << remaining_bits) - 1
                    bytes_per_row = (self.width + 7) // 8
                    for row in range(self.height):
                        self.buffer[row * bytes_per_row + bytes_per_row - 1] = mask
            else:
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0, len(self.buffer))

        elif self.format == framebuf.RGB565:
            for i in range(0, len(self.buffer), 2):
                self.buffer[i] = c & 0xFF
                self.buffer[i + 1] = (c >> 8) & 0xFF
        elif self.format == framebuf.GS8:
            buf_addr = int(addressof(self.buffer))
            self._asm_memset32(buf_addr, c & 0xFF, len(self.buffer))

    @micropython.native
    def hline(self, x: int, y: int, w: int, c: int):
        """Draw horizontal line - optimized for MONO_VLSB"""
        if y < 0 or y >= self.height or x >= self.width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > self.width:
            w = self.width - x

        if w <= 0:
            return

        # For MONO_VLSB, use assembly optimization
        if self.format == framebuf.MONO_VLSB:
            byte_row = y >> 3
            bit_offset = y & 7
            mask = 1 << bit_offset
            offset = byte_row * self.width + x

            if c:
                # Use assembly for setting bits
                buf_addr = int(addressof(self.buffer))
                self._asm_hline_mono_vlsb_set(buf_addr, offset, mask, w)
            else:
                # Clear bits
                inv_mask = ~mask & 0xFF
                for i in range(w):
                    self.buffer[offset + i] &= inv_mask
        else:
            # Fall back to pixel-by-pixel for other formats
            for i in range(w):
                self.pixel(x + i, y, c)

    @micropython.native
    def vline(self, x: int, y: int, h: int, c: int):
        """Draw vertical line"""
        if x < 0 or x >= self.width or y >= self.height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > self.height:
            h = self.height - y

        if h <= 0:
            return

        for i in range(h):
            self.pixel(x, y + i, c)

    @micropython.native
    def rect(self, x: int, y: int, w: int, h: int, c: int, fill_rect: bool = False):
        """Draw rectangle"""
        if fill_rect:
            for row in range(h):
                self.hline(x, y + row, w, c)
        else:
            self.hline(x, y, w, c)
            self.hline(x, y + h - 1, w, c)
            self.vline(x, y, h, c)
            self.vline(x + w - 1, y, h, c)

    @micropython.viper
    def fill_rect(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle - optimized with @viper and inline bit manipulation"""
        # Bounds checking
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0

        width = int(self.width)
        height = int(self.height)

        if x >= width or y >= height or w <= 0 or h <= 0:
            return

        if x + w > width:
            w = width - x
        if y + h > height:
            h = height - y

        # MONO_VLSB format optimization with inline bit manipulation
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)

            # For each row, set the appropriate bit in each byte
            for row in range(h):
                y_pos = y + row
                byte_row = uint(y_pos >> 3)
                bit_offset = uint(y_pos & 7)
                mask = uint(1 << bit_offset)
                offset = uint(byte_row * width + x)

                # Inline bit manipulation for each pixel in the row
                if c:
                    # Set bits
                    for i in range(w):
                        buf[offset + i] |= mask
                else:
                    # Clear bits
                    inv_mask = uint(~mask & 0xFF)
                    for i in range(w):
                        buf[offset + i] &= inv_mask
        else:
            # Fallback for other formats
            for row in range(h):
                self.hline(x, y + row, w, c)

    @micropython.viper
    def line(self, x0: int, y0: int, x1: int, y1: int, c: int):
        """Draw line using Bresenham's algorithm - optimized with @viper and inline pixel writes"""
        width = int(self.width)
        height = int(self.height)

        dx = int(abs(x1 - x0))
        dy = int(abs(y1 - y0))
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        # MONO_VLSB format optimization with inline pixel manipulation
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)

            while True:
                # Inline pixel set - NO function call overhead!
                if 0 <= x0 < width and 0 <= y0 < height:
                    byte_offset = uint((y0 >> 3) * width + x0)
                    bit_offset = uint(y0 & 7)

                    if c:
                        buf[byte_offset] |= (1 << bit_offset)
                    else:
                        buf[byte_offset] &= ~(1 << bit_offset)

                if x0 == x1 and y0 == y1:
                    break

                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy
        else:
            # Fallback for other formats
            while True:
                self.pixel(x0, y0, c)

                if x0 == x1 and y0 == y1:
                    break

                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy

class FrameBufferHybridOptimized:
    """
    Hybrid MicroPython framebuffer combining best strategies:
    - @viper for pixel, hline, vline (inline buffer access)
    - @asm_thumb helpers for fill operations (32-bit word writes)
    - @viper for line (inline pixel writes)
    - Strategic mix for maximum performance
    """

    def __init__(self, buffer, width, height, format):
        self.buffer = buffer
        self.width = width
        self.height = height
        self.format = format

        if format == framebuf.MONO_VLSB or format == framebuf.MONO_HLSB:
            self.bpp = 1
        elif format == framebuf.RGB565:
            self.bpp = 16
        elif format == framebuf.GS4_HMSB:
            self.bpp = 4
        elif format == framebuf.GS8:
            self.bpp = 8
        else:
            self.bpp = 1

    # ========================================================================
    # ASM THUMB HELPERS (shared from FrameBufferAsmThumb)
    # ========================================================================

    @staticmethod
    @micropython.asm_thumb
    def _asm_memset32(r0, r1, r2):
        # r0 = buffer address
        # r1 = byte value (0x00-0xFF)
        # r2 = number of bytes

        # Replicate byte to 32-bit word: 0xFF -> 0xFFFFFFFF
        mov(r3, r1)
        lsl(r3, r3, 8)
        orr(r1, r3)
        mov(r3, r1)
        lsl(r3, r3, 16)
        orr(r1, r3)

        # Calculate word count (r2 >> 2)
        lsr(r3, r2, 2)

        # Process 32-bit words (main loop)
        label(WORD_LOOP)
        cmp(r3, 0)
        beq(BYTE_REMAINDER)
        str(r1, [r0, 0])
        add(r0, r0, 4)
        sub(r3, r3, 1)
        b(WORD_LOOP)

        # Handle remaining 0-3 bytes
        label(BYTE_REMAINDER)
        mov(r4, 3)
        and_(r2, r4)
        cmp(r2, 0)
        beq(END)

        label(BYTE_LOOP)
        strb(r1, [r0, 0])
        add(r0, r0, 1)
        sub(r2, r2, 1)
        cmp(r2, 0)
        bne(BYTE_LOOP)

        label(END)

    # ========================================================================
    # VIPER-OPTIMIZED PRIMITIVES
    # ========================================================================

    @micropython.viper
    def pixel(self, x: int, y: int, c: int = -1) -> int:
        """Set or get pixel value - @viper with inline buffer access"""
        width = int(self.width)
        height = int(self.height)

        if x < 0 or x >= width or y < 0 or y >= height:
            return 0

        # MONO_VLSB format
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)
            byte_offset = uint((y >> 3) * width + x)
            bit_offset = uint(y & 7)

            if c == -1:
                return int((buf[byte_offset] >> bit_offset) & 1)
            else:
                if c:
                    buf[byte_offset] |= (1 << bit_offset)
                else:
                    buf[byte_offset] &= ~(1 << bit_offset)
                return 0

        # RGB565 format
        elif int(self.format) == 1:  # framebuf.RGB565 = 1
            buf = ptr8(self.buffer)
            offset = uint((y * width + x) * 2)
            if c == -1:
                return int(buf[offset] | (buf[offset + 1] << 8))
            else:
                buf[offset] = c & 0xFF
                buf[offset + 1] = (c >> 8) & 0xFF
                return 0

        # GS8 format
        elif int(self.format) == 5:  # framebuf.GS8 = 5
            buf = ptr8(self.buffer)
            offset = uint(y * width + x)
            if c == -1:
                return int(buf[offset])
            else:
                buf[offset] = c & 0xFF
                return 0

        return 0

    @micropython.viper
    def hline(self, x: int, y: int, w: int, c: int):
        """Draw horizontal line - @viper with inline bit manipulation"""
        width = int(self.width)
        height = int(self.height)

        if y < 0 or y >= height or x >= width:
            return

        if x < 0:
            w += x
            x = 0

        if x + w > width:
            w = width - x

        if w <= 0:
            return

        # MONO_VLSB format optimization
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)
            byte_row = uint(y >> 3)
            bit_offset = uint(y & 7)
            mask = uint(1 << bit_offset)
            offset = uint(byte_row * width + x)

            if c:
                # Set bits
                for i in range(w):
                    buf[offset + i] |= mask
            else:
                # Clear bits
                inv_mask = uint(~mask & 0xFF)
                for i in range(w):
                    buf[offset + i] &= inv_mask
        else:
            # Fallback for other formats
            for i in range(w):
                self.pixel(x + i, y, c)

    @micropython.viper
    def vline(self, x: int, y: int, h: int, c: int):
        """Draw vertical line - @viper with inline pixel writes"""
        width = int(self.width)
        height = int(self.height)

        if x < 0 or x >= width or y >= height:
            return

        if y < 0:
            h += y
            y = 0

        if y + h > height:
            h = height - y

        if h <= 0:
            return

        # MONO_VLSB format optimization
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)

            for i in range(h):
                y_pos = y + i
                byte_offset = uint((y_pos >> 3) * width + x)
                bit_offset = uint(y_pos & 7)

                if c:
                    buf[byte_offset] |= (1 << bit_offset)
                else:
                    buf[byte_offset] &= ~(1 << bit_offset)
        else:
            # Fallback for other formats
            for i in range(h):
                self.pixel(x, y + i, c)

    # ========================================================================
    # FILL OPERATIONS (Viper + ASM helpers)
    # ========================================================================

    @micropython.viper
    def fill(self, c: int):
        """Fill entire framebuffer - @viper calling @asm_thumb for bulk operations"""
        format_val = int(self.format)
        buf_len = int(len(self.buffer))

        if format_val == 0:  # MONO_VLSB
            num_byte_rows = int((int(self.height) + 7) >> 3)
            remaining_bits = int(self.height) & 7

            if c:
                # Fill with 1s using optimized memset32
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0xFF, buf_len)

                # Handle partial bits in last byte row if needed
                if remaining_bits != 0:
                    buf = ptr8(self.buffer)
                    mask = uint((1 << remaining_bits) - 1)
                    width = int(self.width)
                    offset_base = uint((num_byte_rows - 1) * width)

                    for col in range(width):
                        buf[offset_base + col] = mask
            else:
                # Fill with 0s
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0, buf_len)

        elif format_val == 4:  # MONO_HLSB
            if c:
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0xFF, buf_len)

                # Handle last byte of each row if width not multiple of 8
                remaining_bits = int(self.width) & 7
                if remaining_bits != 0:
                    buf = ptr8(self.buffer)
                    mask = uint((1 << remaining_bits) - 1)
                    bytes_per_row = int((int(self.width) + 7) >> 3)
                    height = int(self.height)

                    for row in range(height):
                        buf[row * bytes_per_row + bytes_per_row - 1] = mask
            else:
                buf_addr = int(addressof(self.buffer))
                self._asm_memset32(buf_addr, 0, buf_len)

        elif format_val == 1:  # RGB565
            buf = ptr8(self.buffer)
            for i in range(0, buf_len, 2):
                buf[i] = c & 0xFF
                buf[i + 1] = (c >> 8) & 0xFF

        elif format_val == 5:  # GS8
            buf_addr = int(addressof(self.buffer))
            self._asm_memset32(buf_addr, c & 0xFF, buf_len)

    @micropython.viper
    def fill_rect(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle - @viper with inline bit manipulation"""
        # Bounds checking
        if x < 0:
            w += x
            x = 0
        if y < 0:
            h += y
            y = 0

        width = int(self.width)
        height = int(self.height)

        if x >= width or y >= height or w <= 0 or h <= 0:
            return

        if x + w > width:
            w = width - x
        if y + h > height:
            h = height - y

        # MONO_VLSB format optimization with inline bit manipulation
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)

            # For each row, set the appropriate bit in each byte
            for row in range(h):
                y_pos = y + row
                byte_row = uint(y_pos >> 3)
                bit_offset = uint(y_pos & 7)
                mask = uint(1 << bit_offset)
                offset = uint(byte_row * width + x)

                # Inline bit manipulation for each pixel in the row
                if c:
                    # Set bits
                    for i in range(w):
                        buf[offset + i] |= mask
                else:
                    # Clear bits
                    inv_mask = uint(~mask & 0xFF)
                    for i in range(w):
                        buf[offset + i] &= inv_mask
        else:
            # Fallback for other formats
            for row in range(h):
                self.hline(x, y + row, w, c)

    @micropython.viper
    def line(self, x0: int, y0: int, x1: int, y1: int, c: int):
        """Draw line using Bresenham's algorithm - @viper with inline pixel writes"""
        width = int(self.width)
        height = int(self.height)

        dx = int(abs(x1 - x0))
        dy = int(abs(y1 - y0))
        sx = 1 if x0 < x1 else -1
        sy = 1 if y0 < y1 else -1
        err = dx - dy

        # MONO_VLSB format optimization with inline pixel manipulation
        if int(self.format) == 0:  # framebuf.MONO_VLSB = 0
            buf = ptr8(self.buffer)

            while True:
                # Inline pixel set - NO function call overhead!
                if 0 <= x0 < width and 0 <= y0 < height:
                    byte_offset = uint((y0 >> 3) * width + x0)
                    bit_offset = uint(y0 & 7)

                    if c:
                        buf[byte_offset] |= (1 << bit_offset)
                    else:
                        buf[byte_offset] &= ~(1 << bit_offset)

                if x0 == x1 and y0 == y1:
                    break

                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy
        else:
            # Fallback for other formats
            while True:
                self.pixel(x0, y0, c)

                if x0 == x1 and y0 == y1:
                    break

                e2 = 2 * err
                if e2 > -dy:
                    err -= dy
                    x0 += sx
                if e2 < dx:
                    err += dx
                    y0 += sy

    @micropython.viper
    def rect(self, x: int, y: int, w: int, h: int, c: int, fill: bool = False):
        """Draw rectangle - @viper"""
        if fill:
            self.fill_rect(x, y, w, h, c)
        else:
            self.hline(x, y, w, c)
            self.hline(x, y + h - 1, w, c)
            self.vline(x, y, h, c)
            self.vline(x + w - 1, y, h, c)
