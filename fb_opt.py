"""
Pure MicroPython Framebuffer Implementation
Comparable to the built-in C framebuffer module, optimized with @micropython.native and @micropython.viper
"""
import micropython
import framebuf


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

    # Assembly helper for fast memory fill
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

    # Assembly helper for horizontal line in MONO_VLSB
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

    @micropython.native
    def fill(self, c: int):
        """Fill entire framebuffer with color - optimized with asm_thumb helpers"""
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
                # Fill with 0s - use assembly helper for speed
                buf_addr = int(micropython.addressof(self.buffer))
                self._asm_memset(buf_addr, 0, len(self.buffer))

        elif self.format == framebuf.MONO_HLSB:
            # Similar logic for MONO_HLSB
            if c:
                buf_addr = int(micropython.addressof(self.buffer))
                self._asm_memset(buf_addr, 0xFF, len(self.buffer))
                # Handle last byte of each row if width not multiple of 8
                remaining_bits = self.width % 8
                if remaining_bits != 0:
                    mask = (1 << remaining_bits) - 1
                    bytes_per_row = (self.width + 7) // 8
                    for row in range(self.height):
                        self.buffer[row * bytes_per_row + bytes_per_row - 1] = mask
            else:
                buf_addr = int(micropython.addressof(self.buffer))
                self._asm_memset(buf_addr, 0, len(self.buffer))

        elif self.format == framebuf.RGB565:
            for i in range(0, len(self.buffer), 2):
                self.buffer[i] = c & 0xFF
                self.buffer[i + 1] = (c >> 8) & 0xFF
        elif self.format == framebuf.GS8:
            buf_addr = int(micropython.addressof(self.buffer))
            self._asm_memset(buf_addr, c & 0xFF, len(self.buffer))

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
                buf_addr = int(micropython.addressof(self.buffer))
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