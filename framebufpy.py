"""
Pure Python MicroPython Framebuffer Implementation
===================================================

A 1:1 compatible replacement for the built-in C framebuf module,
optimized with @micropython.viper for performance.

Supports all 7 color modes:
- MONO_VLSB (0): Monochrome vertical LSB
- RGB565 (1): 16-bit RGB color
- GS4_HMSB (2): 4-bit grayscale horizontal MSB
- MONO_HLSB (3): Monochrome horizontal LSB
- MONO_HMSB (4): Monochrome horizontal MSB
- GS2_HMSB (5): 2-bit grayscale horizontal MSB
- GS8 (6): 8-bit grayscale

Usage:
    import framebuf

    buf = bytearray(200)  # 50x32 MONO_VLSB: ((32+7)//8)*50 = 200 bytes
    fb = framebuf.FrameBuffer(buf, 50, 32, framebuf.MONO_VLSB)

    fb.pixel(10, 10, 1)
    fb.hline(0, 0, 50, 1)
    fb.vline(0, 0, 32, 1)
    fb.fill(0)
"""

import micropython
from uctypes import addressof
from font_petme128_8x8 import FONT_PETME128_8X8

# Format constants
MONO_VLSB = 0
RGB565 = 1
GS4_HMSB = 2
MONO_HLSB = 3
MONO_HMSB = 4
GS2_HMSB = 5
GS8 = 6

# Aliases for compatibility
MVLSB = MONO_VLSB

# Ellipse quadrant masks
# Q2 Q1
# Q3 Q4
ELLIPSE_MASK_FILL = 0x10
ELLIPSE_MASK_ALL = 0x0f
ELLIPSE_MASK_Q1 = 0x01  # Top-right
ELLIPSE_MASK_Q2 = 0x02  # Top-left
ELLIPSE_MASK_Q3 = 0x04  # Bottom-left
ELLIPSE_MASK_Q4 = 0x08  # Bottom-right


# ====================================================================
# ASM_THUMB OPTIMIZED HELPERS
# Fast bulk memory fill operations using ARM Thumb-2 assembly
# ====================================================================

@micropython.asm_thumb
def _asm_fill_byte(r0, r1, r2):
    """
    Fill memory with a byte value using assembly (optimized with word writes)
    Args:
        r0: buffer address
        r1: number of bytes to fill
        r2: byte value to fill
    """
    # Replicate byte across all 4 positions in a 32-bit word
    # r3 = r2 | (r2 << 8) | (r2 << 16) | (r2 << 24)
    mov(r3, r2)         # r3 = byte
    lsl(r4, r2, 8)      # r4 = byte << 8
    orr(r3, r4)         # r3 = byte | (byte << 8)
    lsl(r4, r3, 16)     # r4 = (r3) << 16
    orr(r3, r4)         # r3 now has byte replicated 4 times

    # Calculate number of words (r1 / 4)
    mov(r4, r1)         # r4 = total bytes
    lsr(r4, r4, 2)      # r4 = total bytes / 4 (number of words)

    # Word fill loop
    label(WORD_LOOP)
    cmp(r4, 0)
    beq(BYTE_LOOP_SETUP)
    str(r3, [r0, 0])    # Store word (4 bytes at once)
    add(r0, r0, 4)      # r0 += 4
    sub(r4, r4, 1)      # r4--
    b(WORD_LOOP)

    # Handle remaining bytes (0-3 bytes)
    label(BYTE_LOOP_SETUP)
    mov(r4, 3)          # r4 = 3
    and_(r1, r4)        # r1 = original length & 3 (remainder)

    # Byte fill loop for remainder
    label(BYTE_LOOP)
    cmp(r1, 0)
    beq(END)
    strb(r2, [r0, 0])   # Store byte
    add(r0, r0, 1)      # r0++
    sub(r1, r1, 1)      # r1--
    b(BYTE_LOOP)

    label(END)


@micropython.asm_thumb
def _asm_fill_word(r0, r1, r2):
    """
    Fill memory with a 32-bit word value using assembly (for 4-byte aligned fills)
    Args:
        r0: buffer address (must be 4-byte aligned)
        r1: number of words to fill (total_bytes // 4)
        r2: 32-bit word value to fill
    """
    label(LOOP)
    str(r2, [r0, 0])   # Store word at r0
    add(r0, r0, 4)      # r0 += 4
    sub(r1, r1, 1)      # r1--
    bne(LOOP)           # if r1 != 0 goto LOOP


@micropython.asm_thumb
def _asm_fill_rgb565(r0, r1, r2):
    """
    Fill RGB565 buffer with alternating low/high bytes (optimized with word writes)
    Args:
        r0: buffer address
        r1: number of pixels to fill
        r2: 16-bit RGB565 color value

    Note: Uses r3, r4, r5 as scratch registers
    """
    # Create 32-bit word containing 2 pixels (color | (color << 16))
    lsl(r3, r2, 16)     # r3 = color << 16
    movw(r4, 0xFFFF)    # r4 = 0xFFFF (use movw for 16-bit immediate)
    and_(r2, r4)        # r2 = color & 0xFFFF (lower 16 bits)
    orr(r3, r2)         # r3 = (color << 16) | color (2 pixels in one word)

    # Calculate number of word writes (pixels / 2)
    mov(r4, r1)         # r4 = total pixels
    lsr(r4, r4, 1)      # r4 = pixels / 2 (number of words)

    # Word fill loop (write 2 pixels at once)
    label(WORD_LOOP)
    cmp(r4, 0)
    beq(PIXEL_LOOP_SETUP)
    str(r3, [r0, 0])    # Store word (2 pixels at once)
    add(r0, r0, 4)      # r0 += 4
    sub(r4, r4, 1)      # r4--
    b(WORD_LOOP)

    # Handle remaining pixel (if odd number of pixels)
    label(PIXEL_LOOP_SETUP)
    mov(r4, 1)          # r4 = 1
    and_(r1, r4)        # r1 = original pixel count & 1 (remainder)

    # Single pixel write for remainder
    label(PIXEL_LOOP)
    cmp(r1, 0)
    beq(END)
    strh(r2, [r0, 0])   # Store halfword (1 pixel = 2 bytes)

    label(END)


class FrameBufferBase:
    """
    Base FrameBuffer class with shared public API

    Subclasses implement format-specific methods:
    - _pixel_impl(x, y, c) -> int
    - _hline_impl(x, y, w, c)
    - _vline_impl(x, y, h, c)
    - _fill_rect_impl(x, y, w, h, c)
    """

    def __init__(self, buffer, width, height, stride=None):
        """
        Initialize framebuffer

        Args:
            buffer: bytearray or buffer protocol object
            width: Width in pixels
            height: Height in pixels
            stride: Optional stride in pixels (defaults to width)
        """
        self.buffer = buffer
        self.width = width
        self.height = height
        self.stride = stride if stride is not None else width

    def pixel(self, x, y, c=-1):
        """
        Get or set pixel value at (x, y)

        Args:
            x: X coordinate
            y: Y coordinate
            c: Color value (optional). If omitted, returns current pixel value.

        Returns:
            Current pixel value (if c not provided), or 0 (if c provided)
        """
        raise NotImplementedError("Subclass must implement pixel()")

    def _setpixel(self, x, y, c):
        """
        Set pixel value at (x, y) without bounds checking (internal use only)

        Args:
            x: X coordinate (must be valid)
            y: Y coordinate (must be valid)
            c: Color value
        """
        raise NotImplementedError("Subclass must implement _setpixel()")

    def hline(self, x, y, w, c):
        """Draw horizontal line starting at (x, y) with width w and color c"""
        self.fill_rect(x, y, w, 1, c)

    def vline(self, x, y, h, c):
        """Draw vertical line starting at (x, y) with height h and color c"""
        self.fill_rect(x, y, 1, h, c)

    def fill(self, c):
        """Fill entire framebuffer with color c"""
        self.fill_rect(0, 0, self.width, self.height, c)

    def fill_rect(self, x, y, w, h, c):
        """
        Fill rectangle with color c

        Args:
            x: Starting X coordinate
            y: Starting Y coordinate
            w: Width in pixels
            h: Height in pixels
            c: Color value
        """
        # Bounds checking and clipping (matches C implementation)
        if h < 1 or w < 1 or x + w <= 0 or y + h <= 0 or y >= self.height or x >= self.width:
            return

        # Clip to framebuffer bounds
        xend = min(self.width, x + w)
        yend = min(self.height, y + h)
        x = max(x, 0)
        y = max(y, 0)
        w = xend - x
        h = yend - y

        # Call format-specific implementation
        self._fill_rect_impl(x, y, w, h, c)

    def rect(self, x, y, w, h, c, f=False):
        """
        Draw rectangle outline or filled rectangle

        Args:
            x: Starting X coordinate
            y: Starting Y coordinate
            w: Width in pixels
            h: Height in pixels
            c: Color value
            f: Fill flag (optional). If True, draws filled rectangle.
        """
        if f:
            self.fill_rect(x, y, w, h, c)
        else:
            # Outline rectangle - draw 4 lines
            self.fill_rect(x, y, w, 1, c)                  # Top edge
            self.fill_rect(x, y + h - 1, w, 1, c)          # Bottom edge
            self.fill_rect(x, y, 1, h, c)                  # Left edge
            self.fill_rect(x + w - 1, y, 1, h, c)          # Right edge

    def blit(self, fbuf, x, y, key=-1, palette=None):
        """
        Blit another framebuffer into this one at position (x, y)

        Args:
            fbuf: Source FrameBuffer or tuple (buffer, width, height, format[, stride])
            x: Destination X coordinate
            y: Destination Y coordinate
            key: Transparency color (-1 = no transparency)
            palette: Optional palette FrameBuffer for color translation (height=1)
        """
        # Parse source framebuffer
        if isinstance(fbuf, tuple):
            if not (4 <= len(fbuf) <= 5):
                raise ValueError("Tuple must be (buffer, width, height, format[, stride])")

            src_buf, src_width, src_height, src_format = fbuf[:4]
            src_stride = fbuf[4] if len(fbuf) == 5 else src_width

            # Create temporary FrameBuffer wrapper
            source = _create_framebuffer(src_buf, src_width, src_height, src_format, src_stride)
        else:
            # Assume it's a FrameBuffer object
            source = fbuf
            src_width = source.width
            src_height = source.height

        # Parse palette if provided
        pal = None
        if palette is not None:
            if isinstance(palette, tuple):
                if not (4 <= len(palette) <= 5):
                    raise ValueError("Palette tuple must be (buffer, width, height, format[, stride])")

                pal_buf, pal_width, pal_height, pal_format = palette[:4]
                pal_stride = palette[4] if len(palette) == 5 else pal_width
                pal = _create_framebuffer(pal_buf, pal_width, pal_height, pal_format, pal_stride)
            else:
                pal = palette

            # Validate palette: height must be 1
            if pal.height != 1:
                raise ValueError("Palette height must be 1")

        # Early bounds check
        if (x >= self.width or
            y >= self.height or
            -x >= src_width or
            -y >= src_height):
            # Completely out of bounds, no-op
            return

        # Check if we can use optimized fast path
        # Fast path 1: same format, no palette, source has _blit_same_format
        can_use_same_format = (pal is None and
                              hasattr(self, 'FORMAT') and
                              hasattr(source, 'FORMAT') and
                              self.FORMAT == source.FORMAT and
                              hasattr(self, '_blit_same_format'))

        # Fast path 2: MONO_HMSB -> RGB565 with palette (for text/icon rendering)
        can_use_mono_palette = (pal is not None and
                               hasattr(self, 'FORMAT') and
                               hasattr(source, 'FORMAT') and
                               self.FORMAT == RGB565 and
                               source.FORMAT == MONO_HMSB and
                               hasattr(self, '_blit_mono_hmsb_palette'))

        if can_use_same_format:
            # Use viper-optimized same-format blit
            self._blit_same_format(source.buffer, src_width, src_height,
                                  source.stride, x, y, key)
        elif can_use_mono_palette:
            # Use viper-optimized MONO_HMSB -> RGB565 palette blit
            self._blit_mono_hmsb_palette(source.buffer, src_width, src_height,
                                        source.stride, x, y, key, pal.buffer)
        else:
            # Fall back to general-purpose pixel-by-pixel blit
            # Calculate clipping
            x0 = max(0, x)              # destination start X (clipped)
            y0 = max(0, y)              # destination start Y (clipped)
            x1 = max(0, -x)             # source start X offset
            y1 = max(0, -y)             # source start Y offset
            x0end = min(self.width, x + src_width)      # destination end X
            y0end = min(self.height, y + src_height)    # destination end Y

            # Blit loop
            for cy0 in range(y0, y0end):
                cx1 = x1
                for cx0 in range(x0, x0end):
                    # Get pixel from source (pass -1 to indicate GET operation)
                    col = source.pixel(cx1, y1, -1)

                    # Apply palette translation if provided
                    if pal is not None:
                        col = pal.pixel(col, 0, -1)

                    # Set pixel in destination if not transparent
                    if col != key:
                        self.pixel(cx0, cy0, col)

                    cx1 += 1
                y1 += 1
    @micropython.viper
    def line(self, x1: int, y1: int, x2: int, y2: int, col: int):
        """
        Draw a line from (x1, y1) to (x2, y2) using Bresenham's algorithm

        Args:
            x1: Start X coordinate
            y1: Start Y coordinate
            x2: End X coordinate
            y2: End Y coordinate
            col: Color value
        """
        # Calculate deltas and steps
        dx = x2 - x1
        if dx > 0:
            sx = 1
        else:
            dx = -dx
            sx = -1

        dy = y2 - y1
        if dy > 0:
            sy = 1
        else:
            dy = -dy
            sy = -1

        # Check if line is steep (|dy| > |dx|)
        # If steep, swap x/y to avoid gaps in the line
        steep = False
        if dy > dx:
            # Swap x1 <-> y1
            temp = x1
            x1 = y1
            y1 = temp
            # Swap dx <-> dy
            temp = dx
            dx = dy
            dy = temp
            # Swap sx <-> sy
            temp = sx
            sx = sy
            sy = temp
            steep = True

        # Bresenham's algorithm - iterate along the primary axis
        width = int(self.width)
        height = int(self.height)
        e = 2 * dy - dx

        for i in range(dx):
            # Plot pixel with bounds checking
            if steep:
                # Steep line: y is primary axis, so check (y1, x1)
                if 0 <= y1 < width and 0 <= x1 < height:
                    self._setpixel(y1, x1, col)
            else:
                # Shallow line: x is primary axis, so check (x1, y1)
                if 0 <= x1 < width and 0 <= y1 < height:
                    self._setpixel(x1, y1, col)

            # Update error term and step along secondary axis if needed
            while e >= 0:
                y1 += sy
                e -= 2 * dx

            # Step along primary axis
            x1 += sx
            e += 2 * dy

        # Draw final pixel (x2, y2) with bounds checking
        if 0 <= x2 < width and 0 <= y2 < height:
            self._setpixel(x2, y2, col)

    @micropython.viper
    def _render_text(self, text_bytes, text_len: int, font_data, x: int, y: int, col: int):
        """
        Render text string (viper-optimized)

        Args:
            text_bytes: String as bytes
            text_len: Length of string
            font_data: Font data bytearray
            x: Starting X coordinate
            y: Starting Y coordinate
            col: Color value
        """
        width = int(self.width)
        height = int(self.height)
        font = ptr8(font_data)
        text = ptr8(text_bytes)

        x_pos = x

        # Process each character
        for i in range(text_len):
            # Get character code
            chr_code = int(text[i])

            # Validate range (use checkerboard for invalid chars)
            if chr_code < 32 or chr_code > 127:
                chr_code = 127

            # Get font data offset for this character (8 bytes per char)
            font_offset = (chr_code - 32) * 8

            # Render 8 columns (each character is 8 pixels wide)
            for j in range(8):
                x_col = x_pos + j
                if 0 <= x_col < width:  # Clip X coordinate
                    # Get column data (vertical line of 8 pixels, LSB at top)
                    vline_data = int(font[font_offset + j])
                    y_pixel = y

                    # Scan over vertical column (8 pixels)
                    for row in range(8):
                        if vline_data & (1 << row):  # Check if pixel is set
                            if 0 <= y_pixel < height:  # Clip Y coordinate
                                self.pixel(x_col, y_pixel, col)
                        y_pixel += 1

            x_pos += 8  # Move to next character position

    def text(self, s, x, y, col=1):
        """
        Render text using 8x8 font

        Args:
            s: String to render
            x: Starting X coordinate
            y: Starting Y coordinate
            col: Color value (default 1)
        """
        # Convert string to bytes for viper processing
        text_bytes = s.encode('utf-8') if isinstance(s, str) else s
        self._render_text(text_bytes, len(text_bytes), FONT_PETME128_8X8, x, y, col)

    @micropython.viper
    def scroll(self, xstep: int, ystep: int):
        """
        Scroll the framebuffer by xstep and ystep pixels

        Args:
            xstep: Horizontal scroll distance (positive = right, negative = left)
            ystep: Vertical scroll distance (positive = down, negative = up)
        """
        width = int(self.width)
        height = int(self.height)

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
            while x != xend:
                # Get pixel from source position
                col = self.pixel(x - xstep, y - ystep, -1)
                # Set pixel at destination position
                self.pixel(x, y, col)
                x += dx
            y += dy

    @micropython.viper
    def _draw_ellipse_points(self, cx: int, cy: int, x: int, y: int, col: int, mask: int):
        """
        Helper for ellipse() - draws 4-way symmetric points with quadrant masking

        Args:
            cx: Center X
            cy: Center Y
            x: X offset from center
            y: Y offset from center
            col: Color value
            mask: Quadrant mask (ELLIPSE_MASK_*)
        """
        # Local constants for viper
        MASK_FILL = int(0x10)
        MASK_Q1 = int(0x01)
        MASK_Q2 = int(0x02)
        MASK_Q3 = int(0x04)
        MASK_Q4 = int(0x08)

        if mask & MASK_FILL:
            # Fill mode: draw horizontal spans
            if mask & MASK_Q1:
                self.fill_rect(cx, cy - y, x + 1, 1, col)
            if mask & MASK_Q2:
                self.fill_rect(cx - x, cy - y, x + 1, 1, col)
            if mask & MASK_Q3:
                self.fill_rect(cx - x, cy + y, x + 1, 1, col)
            if mask & MASK_Q4:
                self.fill_rect(cx, cy + y, x + 1, 1, col)
        else:
            # Outline mode: draw individual pixels
            if mask & MASK_Q1:
                self.pixel(cx + x, cy - y, col)
            if mask & MASK_Q2:
                self.pixel(cx - x, cy - y, col)
            if mask & MASK_Q3:
                self.pixel(cx - x, cy + y, col)
            if mask & MASK_Q4:
                self.pixel(cx + x, cy + y, col)

    @micropython.native
    def ellipse(self, cx, cy, xradius, yradius, col, fill=False, mask=0x0f):
        """
        Draw an ellipse using the midpoint ellipse algorithm

        Args:
            cx: Center X coordinate
            cy: Center Y coordinate
            xradius: X radius (horizontal)
            yradius: Y radius (vertical)
            col: Color value
            fill: Fill flag (optional, default False)
            mask: Quadrant mask (optional, default 0x0f = all quadrants)
        """
        # Combine fill flag with mask
        ellipse_mask = mask & 0x0f  # MASK_ALL
        if fill:
            ellipse_mask |= 0x10  # MASK_FILL

        # Special case: zero radius (single point)
        if xradius == 0 and yradius == 0:
            if ellipse_mask & 0x0f:
                self.pixel(cx, cy, col)
            return

        # Phase 1: Top/bottom arcs (where slope dy/dx > -1)
        two_asquare = 2 * xradius * xradius
        two_bsquare = 2 * yradius * yradius
        x = xradius
        y = 0
        xchange = yradius * yradius * (1 - 2 * xradius)
        ychange = xradius * xradius
        ellipse_error = 0
        stoppingx = two_bsquare * xradius
        stoppingy = 0

        while stoppingx >= stoppingy:
            self._draw_ellipse_points(cx, cy, x, y, col, ellipse_mask)
            y += 1
            stoppingy += two_asquare
            ellipse_error += ychange
            ychange += two_asquare
            if (2 * ellipse_error + xchange) > 0:
                x -= 1
                stoppingx -= two_bsquare
                ellipse_error += xchange
                xchange += two_bsquare

        # Phase 2: Left/right arcs (where slope dy/dx < -1)
        x = 0
        y = yradius
        xchange = yradius * yradius
        ychange = xradius * xradius * (1 - 2 * yradius)
        ellipse_error = 0
        stoppingx = 0
        stoppingy = two_asquare * yradius

        while stoppingx <= stoppingy:
            self._draw_ellipse_points(cx, cy, x, y, col, ellipse_mask)
            x += 1
            stoppingx += two_bsquare
            ellipse_error += xchange
            xchange += two_bsquare
            if (2 * ellipse_error + ychange) > 0:
                y -= 1
                stoppingy -= two_asquare
                ellipse_error += ychange
                ychange += two_asquare


    @micropython.native
    def poly(self, x, y, coords, col, fill=False):
        """
        Draw a polygon outline or filled polygon

        Args:
            x: X offset for polygon
            y: Y offset for polygon
            coords: Array/list of coordinates [x1, y1, x2, y2, ...]
            col: Color value
            fill: Fill flag (optional, default False)
        """
        # Get number of coordinate pairs
        # Supports array.array, list, tuple, etc.
        n_coords = len(coords)
        if n_coords < 2:
            return

        n_poly = n_coords // 2  # Number of vertices
        if n_poly == 0:
            return

        if not fill:
            # Outline mode: draw lines between consecutive points
            px1 = coords[0]
            py1 = coords[1]

            # Iterate backwards through coords (matching C implementation)
            i = n_poly * 2 - 1
            while i >= 0:
                py2 = coords[i]
                i -= 1
                px2 = coords[i]
                i -= 1

                # Draw line from (px1, py1) to (px2, py2)
                self.line(x + px1, y + py1, x + px2, y + py2, col)

                px1 = px2
                py1 = py2
        else:
            # Fill mode: scanline algorithm
            # Find vertical extent of polygon
            y_min = coords[1]
            y_max = coords[1]
            for i in range(1, n_poly):
                py = coords[i * 2 + 1]
                if py < y_min:
                    y_min = py
                if py > y_max:
                    y_max = py

            # For each scanline
            for row in range(y_min, y_max + 1):
                # Find edge intersections (nodes)
                nodes = []

                # Start from first vertex
                px1 = coords[0]
                py1 = coords[1]

                # Iterate backwards through vertices
                i = n_poly * 2 - 1
                while i >= 0:
                    py2 = coords[i]
                    i -= 1
                    px2 = coords[i]
                    i -= 1

                    # Check if edge crosses this scanline
                    # Avoid duplicating pixels at vertices by excluding bottom pixel
                    if py1 != py2 and ((py1 > row >= py2) or (py1 <= row < py2)):
                        # Calculate intersection using fixed-point math
                        # node = px1 + (px2-px1) * (row-py1) / (py2-py1)
                        # Use fixed point with 32x scaling for precision
                        node = (32 * px1 + 32 * (px2 - px1) * (row - py1) // (py2 - py1) + 16) // 32
                        nodes.append(node)
                    elif row == max(py1, py2):
                        # Handle local minima/maxima to fill missing pixels
                        if py1 < py2:
                            self.pixel(x + px2, y + py2, col)
                        elif py2 < py1:
                            self.pixel(x + px1, y + py1, col)
                        else:
                            # Horizontal edge
                            self.line(x + px1, y + py1, x + px2, y + py2, col)

                    px1 = px2
                    py1 = py2

                if not nodes:
                    continue

                # Sort nodes left-to-right using bubble sort (matching C)
                i = 0
                while i < len(nodes) - 1:
                    if nodes[i] > nodes[i + 1]:
                        # Swap
                        nodes[i], nodes[i + 1] = nodes[i + 1], nodes[i]
                        if i > 0:
                            i -= 1
                    else:
                        i += 1

                # Fill between pairs of nodes
                for i in range(0, len(nodes), 2):
                    if i + 1 < len(nodes):
                        self.fill_rect(x + nodes[i], y + row, nodes[i + 1] - nodes[i] + 1, 1, col)


# ====================================================================
# FACTORY FUNCTION FOR C API COMPATIBILITY
# ====================================================================

def _create_framebuffer(buffer, width, height, format, stride=None):
    """Factory function - creates appropriate subclass based on format"""
    # Validate parameters
    if stride is None:
        stride = width

    if width < 1 or height < 1 or width > 0xffff or height > 0xffff or stride > 0xffff or stride < width:
        raise ValueError("Invalid framebuffer dimensions")

    # Calculate required buffer size
    bpp = 1
    height_required = height
    width_required = width
    strides_required = height - 1
    stride_for_calc = stride  # Use separate variable for calculation

    if format == MONO_VLSB:
        height_required = (height + 7) & ~7
        strides_required = height_required - 8
    elif format == MONO_HLSB or format == MONO_HMSB:
        stride_for_calc = (stride + 7) & ~7
        width_required = (width + 7) & ~7
    elif format == GS2_HMSB:
        stride_for_calc = (stride + 3) & ~3
        width_required = (width + 3) & ~3
        bpp = 2
    elif format == GS4_HMSB:
        stride_for_calc = (stride + 1) & ~1
        width_required = (width + 1) & ~1
        bpp = 4
    elif format == GS8:
        bpp = 8
    elif format == RGB565:
        bpp = 16
    else:
        raise ValueError("Invalid format")

    # Validate buffer size
    required_size = (strides_required * stride_for_calc + (height_required - strides_required) * width_required) * bpp // 8
    if len(buffer) < required_size:
        raise ValueError("Buffer too small")

    # Lazy imports to avoid circular dependencies
    if format == MONO_VLSB:
        from framebuf_mono_vlsb import FrameBufferMONO_VLSB
        return FrameBufferMONO_VLSB(buffer, width, height, stride)
    elif format == RGB565:
        from framebuf_rgb565 import FrameBufferRGB565
        return FrameBufferRGB565(buffer, width, height, stride)
    elif format == GS4_HMSB:
        from framebuf_gs4_hmsb import FrameBufferGS4_HMSB
        return FrameBufferGS4_HMSB(buffer, width, height, stride)
    elif format == MONO_HLSB:
        from framebuf_mono_hlsb import FrameBufferMONO_HLSB
        return FrameBufferMONO_HLSB(buffer, width, height, stride)
    elif format == MONO_HMSB:
        from framebuf_mono_hmsb import FrameBufferMONO_HMSB
        return FrameBufferMONO_HMSB(buffer, width, height, stride)
    elif format == GS2_HMSB:
        from framebuf_gs2_hmsb import FrameBufferGS2_HMSB
        return FrameBufferGS2_HMSB(buffer, width, height, stride)
    elif format == GS8:
        from framebuf_gs8 import FrameBufferGS8
        return FrameBufferGS8(buffer, width, height, stride)

# Shadow FrameBuffer name with factory for C API compatibility
FrameBuffer = _create_framebuffer
