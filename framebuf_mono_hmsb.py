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
                self.hline(x, y + yy, w, c)
