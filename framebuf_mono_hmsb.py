"""MONO_HMSB (Monochrome Horizontal MSB) format implementation"""

import micropython
from framebufpy import FrameBufferBase, MONO_HMSB

class FrameBufferMONO_HMSB(FrameBufferBase):
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
    def _setpixel(self, x: int, y: int, c: int):
        """Set pixel without bounds checking for MONO_HMSB format"""
        stride = int(self.stride)
        buf = ptr8(self.buffer)
        bytes_per_row = uint((stride + 7) >> 3)
        index = uint(y * bytes_per_row + (x >> 3))
        offset = uint(x & 0x07)  # HMSB: bit 0 is leftmost

        if c:
            buf[index] |= uint(1 << offset)
        else:
            buf[index] &= uint(~(1 << offset) & 0xFF)


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
            # Partial rectangle - inline optimized row filling
            buf = ptr8(self.buffer)
            stride = int(self.stride)

            for yy in range(h):
                py = y + yy
                # For HMSB: horizontal packing, bit 0 is leftmost
                for xx in range(w):
                    px = x + xx
                    byte_index = uint(py * ((stride + 7) >> 3) + (px >> 3))
                    bit_offset = uint(px & 0x07)  # Bit 0 is pixel 0

                    if c:
                        buf[byte_index] |= uint(1 << bit_offset)
                    else:
                        buf[byte_index] &= uint(~(1 << bit_offset) & 0xFF)
