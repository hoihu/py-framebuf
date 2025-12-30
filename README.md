# Pure Python MicroPython FrameBuffer Implementation

A pure Python implementation of MicroPython's framebuffer module using `@micropython.viper` and `@micropython.asm_thumb` optimizations. This therefore runs on ARM compatible HW only.

## Overview

This implementation provides some functionalities of the built-in `framebuf` module in MicroPython. It supports:

- All 7 color formats supported (MONO_VLSB, RGB565, GS4_HMSB, MONO_HLSB, MONO_HMSB, GS2_HMSB, GS8)
- API-compatible with the C implementation
- Optimized using viper decorators and ARM Thumb-2 assembly helpers
- Full blit support with transparency (key parameter) and palette color translation

## Background and Motivation

Some HW / Displays require other color format than the (hard coded) framebuf library from
MicroPython.

For example, a LED strip with WS2812 chips has 8 bits per color, making it a RGB888 format.

Or it may be that a DMA channel which streams the framebuffer to the display requires a certain layout
of the underlying buffer to work smoothly.

All this would be difficult to do in C code and would also require to re-compile MicroPython.

Using `@viper` and `@asm_thumb` enables to write pure-python code at reasonable speed. But how
fast can it be?

This repository tries to find an answer to this by benchmarking a viper / asm_thumb optimized
pure-python framebuf vs the C code of the built-in micropython module

Therefore - it's not meant as a replacement of the C-code of MicroPython, but rather as a test sceleton to benchmark things.

## Claude / KI setup

The code was written entirely using claude code with HW-in-the-loop.

Using claude's `skills` I convinced claude to use my pico-W modul to download the python files, execute the tests and do all the other tasks in agent mode. This allowed claude to do a lot of the work autonomously (YOLO).

I let claude run in a development setup recommended by anthropic, using a devcontainer with a
firewall and let the pico module be exposed via a rfc2217 serial-to-TCP server (copied from the
pyserial github repository). Claude can then talk to the board via port 2217.
I've added some firewall rules to let that port go through.

## Architecture

The implementation uses specialized subclasses for each format:

```python
# Factory function maintains C API compatibility
fb = framebuf.FrameBuffer(buf, 128, 64, framebuf.MONO_VLSB)

# Direct instantiation also available
fb = framebuf.FrameBufferMONO_VLSB(buf, 128, 64)
```

Each format has its own subclass (`FrameBufferMONO_VLSB`, `FrameBufferRGB565`, etc.) that directly overrides methods like `pixel()`, `hline()`, and `vline()` with `@micropython.viper` optimized implementations.

## Performance

Tested on MicroPython RP2040 Pico W Modul.

Comparing C implementation vs pure Python viper implementation (lower ratio is better)

### Fill Operations

| Format    | C (µs) | Viper (µs) | Ratio |
| --------- | ------ | ---------- | ----- |
| MONO_VLSB | 568.9  | 340.3      | 0.60× |
| MONO_HLSB | 633.2  | 329.5      | 0.52× |
| RGB565    | 184.7  | 201.1      | 1.09× |
| GS8       | 115.3  | 271.6      | 2.35× |

**Fill operations are 40-50% faster than C for monochrome formats**, nearly identical for RGB565, and 2-3× slower for grayscale formats.

### Line Operations (hline/vline)

| Format    | Operation | C (µs) | Viper (µs) | Ratio |
| --------- | --------- | ------ | ---------- | ----- |
| MONO_VLSB | hline     | 25.5   | 97.7       | 3.84× |
| MONO_VLSB | vline     | 28.4   | 88.0       | 3.09× |
| MONO_HLSB | hline     | 41.3   | 58.7       | 1.42× |
| RGB565    | hline     | 19.8   | 75.7       | 3.83× |
| GS8       | vline     | 46.2   | 89.5       | 1.94× |

**Line operations are 1.4-4.6× slower** than C depending on format.

### Pixel Operations

| Format    | C (µs) | Viper (µs) | Ratio |
| --------- | ------ | ---------- | ----- |
| MONO_VLSB | 876.5  | 5000       | 5.65× |
| RGB565    | 885.9  | 5000       | 5.59× |
| GS8       | 972.0  | 5000       | 5.18× |

**Individual pixel operations are 5-6× slower** than C.

_Note: Benchmarks measure 10,000 pixel operations (100 pixels × 100 iterations)_

## Testing

All 40 unit tests pass across all 7 formats:

- ✓ Pixel get/set operations
- ✓ Horizontal and vertical lines
- ✓ Fill operations
- ✓ Rectangle drawing
- ✓ Edge cases and bounds checking
- ✓ Blit operations (same format, cross-format with palette, transparency, stride, clipping)

## Usage

```python
import framebuf_pure as framebuf

# Create buffer for 128x64 monochrome display (SSD1306)
buf = bytearray(1024)  # ((64+7)//8) * 128
fb = framebuf.FrameBuffer(buf, 128, 64, framebuf.MONO_VLSB)

# Draw operations
fb.fill(0)                    # Clear screen
fb.pixel(10, 10, 1)           # Set pixel
fb.hline(0, 0, 128, 1)        # Horizontal line
fb.vline(0, 0, 64, 1)         # Vertical line
fb.rect(10, 10, 20, 20, 1)    # Rectangle outline
fb.fill_rect(40, 40, 10, 10, 1)  # Filled rectangle

# Blit operations
sprite = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_VLSB)
sprite.fill(1)
fb.blit(sprite, 50, 30)       # Copy sprite to position (50, 30)
fb.blit(sprite, 60, 40, key=0)  # Copy with transparency (skip color 0)

# Cross-format blit with palette
icon_mono = framebuf.FrameBuffer(bytearray(8), 8, 8, framebuf.MONO_HLSB)
icon_mono.pixel(3, 3, 1)
rgb_display = framebuf.FrameBuffer(bytearray(128), 8, 8, framebuf.RGB565)
palette = framebuf.FrameBuffer(bytearray(4), 2, 1, framebuf.RGB565)
palette.pixel(0, 0, 0x0000)   # Background: black
palette.pixel(1, 0, 0xF800)   # Foreground: red
rgb_display.blit(icon_mono, 0, 0, -1, palette)  # Convert mono to RGB
```

## Optimization Techniques

1. **ARM Thumb-2 Assembly** - Fast bulk memory operations for fill
2. **Viper Decorators** - Native code generation for hot paths
3. **Direct Method Overriding** - Subclasses override methods directly, eliminating indirection
4. **Format-Specific Optimization** - Each format has tailored implementations

## Limitations

- Pixel and line operations are 2-6× slower than C
- Flash usage may be higher, RAM usage should be roughly similar.
- Some edge cases may behave differently than C implementation
- Still needs more testing!

## Files

- `framebuf_pure.py` - Main implementation (1,253 lines)
- `test_framebuf.py` - Test suite (31 tests)
- `benchmark_framebuf.py` - Performance benchmarks
