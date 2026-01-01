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
    def _setpixel(self, x: int, y: int, c: int):
        """Set pixel without bounds checking for GS4_HMSB format"""
        stride = int(self.stride)
        buf = ptr8(self.buffer)
        index = uint((y * stride + x) >> 1)

        if x & 1:  # Odd x, lower nibble
            buf[index] = uint((buf[index] & 0xF0) | (c & 0x0F))
        else:  # Even x, upper nibble
            buf[index] = uint((buf[index] & 0x0F) | ((c & 0x0F) << 4))



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
            # Partial rectangle - use _setpixel for each pixel
            buf = ptr8(self.buffer)
            stride = int(self.stride)
            c_nibble = uint(c & 0x0F)
            for yy in range(h):
                row_y = y + yy
                row_offset = uint((row_y * stride) >> 1)
                for xx in range(w):
                    x_pos = x + xx
                    index = uint(row_offset + (x_pos >> 1))
                    if x_pos & 1:  # Odd x, lower nibble
                        buf[index] = uint((buf[index] & 0xF0) | c_nibble)
                    else:  # Even x, upper nibble
                        buf[index] = uint((buf[index] & 0x0F) | (c_nibble << 4))
