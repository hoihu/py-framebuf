"""GS4_HMSB (4-bit grayscale horizontal MSB) format implementation"""

import micropython
from framebufpy import FrameBufferBase, GS4_HMSB

class FrameBufferGS4_HMSB(FrameBufferBase):
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
                self.hline(x, y + yy, w, c)
