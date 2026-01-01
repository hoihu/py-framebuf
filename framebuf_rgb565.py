"""RGB565 (16-bit RGB color) format implementation"""

import micropython
from uctypes import addressof
from framebufpy import FrameBufferBase, RGB565, MONO_HMSB, _asm_fill_rgb565

class FrameBufferRGB565(FrameBufferBase):
    """FrameBuffer for RGB565 format"""
    FORMAT = RGB565

    @micropython.viper
    def pixel(self, x: int, y: int, c: int) -> int:
        """Pixel implementation for RGB565 format - optimized with ptr16"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Bounds check - unsigned comparison handles negative values
        if uint(x) >= uint(width) or uint(y) >= uint(height):
            return 0

        # Use ptr16 for direct 16-bit access (more efficient than byte manipulation)
        buf = ptr16(self.buffer)
        index = uint(y * stride + x)

        if c == -1:  # Get pixel
            return int(buf[index])
        else:  # Set pixel
            buf[index] = uint(c & 0xFFFF)
            return 0

    @micropython.viper
    def _setpixel(self, x: int, y: int, c: int):
        """Set pixel without bounds checking (internal use only)"""
        stride = int(self.stride)
        buf = ptr16(self.buffer)
        index = uint(y * stride + x)
        buf[index] = uint(c & 0xFFFF)

    @micropython.viper
    def _fill_rect_impl(self, x: int, y: int, w: int, h: int, c: int):
        """Fill rectangle for RGB565 format - optimized with asm_thumb"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Check if this is a full-buffer fill - use optimized asm path
        if x == 0 and y == 0 and w == width and h == height:
            total_pixels = height * stride
            buf_addr = int(addressof(self.buffer))
            _asm_fill_rgb565(buf_addr, total_pixels, c)
        else:
            # Partial fill - use row-by-row approach like C
            buf = ptr16(self.buffer)
            c_val = uint(c & 0xFFFF)
            for yy in range(h):
                offset = uint((y + yy) * stride + x)
                for xx in range(w):
                    buf[offset + xx] = c_val

    @micropython.viper
    def _blit_same_format(self, src_buf, src_w: int, src_h: int, src_stride: int,
                          x: int, y: int, key: int):
        """Optimized blit for RGB565 same-format (no palette)"""
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
        dst_buf = ptr16(self.buffer)
        s_buf = ptr16(src_buf)

        # Blit loop - optimized with direct 16-bit access
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
            key_val: int = key & 0xFFFF
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
    def _blit_mono_hmsb_palette(self, src_buf, src_w: int, src_h: int, src_stride: int,
                                x: int, y: int, key: int, pal_buf):
        """Optimized blit for MONO_HMSB -> RGB565 with 2-color palette"""
        width = int(self.width)
        height = int(self.height)
        stride = int(self.stride)

        # Calculate clipping
        x0: int = x if x >= 0 else 0
        y0: int = y if y >= 0 else 0
        x1: int = -x if x < 0 else 0
        y1: int = -y if y < 0 else 0

        x0end: int = width if (x + src_w) >= width else (x + src_w)
        y0end: int = height if (y + src_h) >= height else (y + src_h)

        # Early return if completely out of bounds
        if x0 >= x0end or y0 >= y0end:
            return

        # Get palette colors (2-color palette: index 0 and 1)
        p_buf = ptr16(pal_buf)
        pal0: int = int(p_buf[0])  # Background color
        pal1: int = int(p_buf[1])  # Foreground color

        # Setup destination buffer
        dst_buf = ptr16(self.buffer)
        s_buf = ptr8(src_buf)

        # Calculate source stride in bytes (each byte holds 8 horizontal pixels)
        src_stride_bytes: int = (src_stride + 7) >> 3

        if key == -1:
            # Fast path: no transparency
            cy0: int = y0
            while cy0 < y0end:
                cx1: int = x1
                cx0: int = x0
                dst_offset = uint(cy0 * stride + x0)

                while cx0 < x0end:
                    # Calculate source byte and bit position
                    byte_offset: int = y1 * src_stride_bytes + (cx1 >> 3)
                    bit_offset: int = cx1 & 7  # HMSB: bit 0 is leftmost

                    # Extract bit value
                    byte_val: int = int(s_buf[byte_offset])
                    bit_val: int = (byte_val >> bit_offset) & 1

                    # Map to palette color
                    color: int = pal1 if bit_val else pal0
                    dst_buf[dst_offset] = uint(color)

                    dst_offset += 1
                    cx1 += 1
                    cx0 += 1
                y1 += 1
                cy0 += 1
        else:
            # With transparency
            key_val: int = key & 0xFFFF
            cy0: int = y0
            while cy0 < y0end:
                cx1: int = x1
                cx0: int = x0
                dst_offset = uint(cy0 * stride + x0)

                while cx0 < x0end:
                    # Calculate source byte and bit position
                    byte_offset: int = y1 * src_stride_bytes + (cx1 >> 3)
                    bit_offset: int = cx1 & 7  # HMSB: bit 0 is leftmost

                    # Extract bit value
                    byte_val: int = int(s_buf[byte_offset])
                    bit_val: int = (byte_val >> bit_offset) & 1

                    # Map to palette color
                    color: int = pal1 if bit_val else pal0

                    # Only write if not transparent
                    if color != key_val:
                        dst_buf[dst_offset] = uint(color)

                    dst_offset += 1
                    cx1 += 1
                    cx0 += 1
                y1 += 1
                cy0 += 1
