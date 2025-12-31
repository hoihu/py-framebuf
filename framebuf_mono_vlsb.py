"""MONO_VLSB (Monochrome Vertical LSB) format implementation"""

import micropython
from framebufpy import FrameBufferBase, MONO_VLSB

class FrameBufferMONO_VLSB(FrameBufferBase):
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
                self.hline(x, y + yy, w, c)
