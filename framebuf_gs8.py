"""GS8 (8-bit grayscale) format implementation"""

import micropython
from uctypes import addressof
from framebufpy import FrameBufferBase, GS8, _asm_fill_byte

class FrameBufferGS8(FrameBufferBase):
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
    def _setpixel(self, x: int, y: int, c: int):
        """Set pixel without bounds checking (internal use only)"""
        stride = int(self.stride)
        buf = ptr8(self.buffer)
        index = uint(y * stride + x)
        buf[index] = uint(c & 0xFF)

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

    @micropython.viper
    def _blit_same_format(self, src_buf, src_w: int, src_h: int, src_stride: int,
                          x: int, y: int, key: int):
        """Optimized blit for GS8 same-format (no palette)"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Early bounds check
        if x >= width or y >= height or -x >= src_w or -y >= src_h:
            return

        # Calculate clipping - use int for all clip calculations
        x0: int = x if x >= 0 else 0
        y0: int = y if y >= 0 else 0
        x1: int = -x if x < 0 else 0
        y1: int = -y if y < 0 else 0
        temp_x: int = x + src_w
        temp_y: int = y + src_h
        x0end: int = temp_x if temp_x < width else width
        y0end: int = temp_y if temp_y < height else height

        # Direct buffer access
        dst_buf = ptr8(self.buffer)
        s_buf = ptr8(src_buf)

        # Blit loop - optimized with direct 8-bit access
        if key == -1:
            # Fast path: no transparency
            cy0: int = y0
            while cy0 < y0end:
                dst_offset = uint(cy0 * stride + x0)
                src_offset = uint(y1 * src_stride + x1)
                cx0: int = x0
                while cx0 < x0end:
                    dst_buf[dst_offset] = s_buf[src_offset]
                    dst_offset += 1
                    src_offset += 1
                    cx0 += 1
                y1 += 1
                cy0 += 1
        else:
            # With transparency check
            key_val: int = key & 0xFF
            cy0: int = y0
            while cy0 < y0end:
                dst_offset = uint(cy0 * stride + x0)
                src_offset = uint(y1 * src_stride + x1)
                cx0: int = x0
                while cx0 < x0end:
                    col_val: int = int(s_buf[src_offset])
                    if col_val != key_val:
                        dst_buf[dst_offset] = uint(col_val)
                    dst_offset += 1
                    src_offset += 1
                    cx0 += 1
                y1 += 1
                cy0 += 1

    @micropython.viper
    def scroll(self, xstep: int, ystep: int):
        """
        Optimized scroll for GS8 format using direct 8-bit buffer access

        Args:
            xstep: Horizontal scroll distance (positive = right, negative = left)
            ystep: Vertical scroll distance (positive = down, negative = up)
        """
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Early return if scroll distance >= dimension
        if xstep < 0:
            if -xstep >= width:
                return
        else:
            if xstep >= width:
                return

        if ystep < 0:
            if -ystep >= height:
                return
        else:
            if ystep >= height:
                return

        # Direct buffer access
        buf = ptr8(self.buffer)

        # Determine X iteration direction
        if xstep < 0:
            # Scrolling left: iterate left-to-right
            sx = 0
            xend = width + xstep
            dx = 1
        else:
            # Scrolling right: iterate right-to-left
            sx = width - 1
            xend = xstep - 1
            dx = -1

        # Determine Y iteration direction
        if ystep < 0:
            # Scrolling up: iterate top-to-bottom
            sy = 0
            yend = height + ystep
            dy = 1
        else:
            # Scrolling down: iterate bottom-to-top
            sy = height - 1
            yend = ystep - 1
            dy = -1

        # Copy pixels from (x-xstep, y-ystep) to (x, y)
        y = sy
        while y != yend:
            x = sx
            src_row_offset = uint((y - ystep) * stride)
            dst_row_offset = uint(y * stride)

            while x != xend:
                # Direct 8-bit copy
                src_index = src_row_offset + uint(x - xstep)
                dst_index = dst_row_offset + uint(x)
                buf[dst_index] = buf[src_index]
                x += dx
            y += dy
