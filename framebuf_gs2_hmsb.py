"""GS2_HMSB (2-bit grayscale horizontal MSB) format implementation"""

import micropython
from framebufpy import FrameBufferBase, GS2_HMSB

class FrameBufferGS2_HMSB(FrameBufferBase):
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
    def _setpixel(self, x: int, y: int, c: int):
        """Set pixel without bounds checking for GS2_HMSB format"""
        stride = int(self.stride)
        buf = ptr8(self.buffer)
        index = uint((y * stride + x) >> 2)
        shift = uint((x & 0x3) << 1)
        mask = uint(0x3 << shift)
        color = uint((c & 0x3) << shift)
        buf[index] = uint((buf[index] & ~mask) | color)



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
            # Partial rectangle - use _setpixel for each pixel
            buf = ptr8(self.buffer)
            stride = int(self.stride)
            c_bits = uint(c & 0x3)
            for yy in range(h):
                row_y = y + yy
                row_offset = uint((row_y * stride) >> 2)
                for xx in range(w):
                    x_pos = x + xx
                    index = uint(row_offset + (x_pos >> 2))
                    shift = uint((x_pos & 0x3) << 1)
                    mask = uint(0x3 << shift)
                    color = uint(c_bits << shift)
                    buf[index] = uint((buf[index] & ~mask) | color)
