# Benchmark Results

**Implementation**: Pure Python with `@micropython.viper` decorator
**Hardware**: Pico2 W
**MicroPython**: v1.27
**Date**: 2026-01-06

## MONO_VLSB 128x64 (SSD1306 OLED)

| Operation                    | C Time | Python Time | Ratio  |
| ---------------------------- | ------ | ----------- | ------ |
| fill(1)                      | 566 µs | 328 µs      | 0.58x  |
| pixel(50, 30, 1)             | 13 µs  | 32 µs       | 2.41x  |
| hline(0, 32, 128, 1)         | 24 µs  | 178 µs      | 7.32x  |
| vline(64, 0, 64, 1)          | 27 µs  | 176 µs      | 6.45x  |
| fill_rect(10, 10, 50, 30, 1) | 119 µs | 781 µs      | 6.52x  |
| blit(sprite_8x8, 60, 28)     | 52 µs  | 2.8 ms      | 53.92x |
| line(0, 0, 127, 63, 1)       | 91 µs  | 1.5 ms      | 16.67x |
| text('Hello!', 10, 10, 1)    | 80 µs  | 1.5 ms      | 18.61x |
| scroll(1, 0)                 | 4.9 ms | 254.4 ms    | 52.02x |
| ellipse(64, 32, 30, 20, 1)   | 110 µs | 3.0 ms      | 27.28x |
| ellipse(..., filled)         | 321 µs | 15.4 ms     | 47.77x |
| poly(triangle, outline)      | 89 µs  | 1.3 ms      | 14.84x |
| poly(triangle, filled)       | 291 µs | 6.6 ms      | 22.47x |

## RGB565 128x64 (Color Display)

| Operation                         | C Time | Python Time | Ratio  |
| --------------------------------- | ------ | ----------- | ------ |
| fill(0xFFFF)                      | 349 µs | 263 µs      | 0.76x  |
| pixel(50, 30, 0xF800)             | 13 µs  | 32 µs       | 2.39x  |
| hline(0, 32, 100, 0x07E0)         | 20 µs  | 153 µs      | 7.64x  |
| vline(64, 0, 50, 0x001F)          | 22 µs  | 144 µs      | 6.49x  |
| fill_rect(10, 10, 50, 30, 0xF800) | 79 µs  | 467 µs      | 5.86x  |
| blit(sprite_8x8, 60, 28)          | 43 µs  | 179 µs      | 4.08x  |
| line(0, 0, 127, 63, 0xF800)       | 82 µs  | 1.5 ms      | 18.15x |
| text('Hello!', 10, 10, 0x07E0)    | 71 µs  | 1.5 ms      | 20.74x |
| scroll(1, 0)                      | 3.8 ms | 3.5 ms      | 0.93x  |
| ellipse(64, 32, 30, 20, 0x001F)   | 98 µs  | 3.0 ms      | 30.90x |
| ellipse(..., filled)              | 241 µs | 14.7 ms     | 60.80x |
| poly(triangle, outline)           | 82 µs  | 1.3 ms      | 15.96x |
| poly(triangle, filled)            | 270 µs | 6.4 ms      | 23.67x |

## GS8 128x64 (8-bit Grayscale)

| Operation                     | C Time | Python Time | Ratio  |
| ----------------------------- | ------ | ----------- | ------ |
| fill(128)                     | 65 µs  | 195 µs      | 2.99x  |
| pixel(50, 30, 255)            | 13 µs  | 32 µs       | 2.39x  |
| hline(0, 32, 100, 200)        | 16 µs  | 128 µs      | 7.73x  |
| vline(64, 0, 50, 150)         | 27 µs  | 513 µs      | 18.77x |
| fill_rect(10, 10, 50, 30, 64) | 34 µs  | 350 µs      | 10.28x |
| blit(sprite_8x8, 60, 28)      | 45 µs  | 177 µs      | 3.90x  |
| line(0, 0, 127, 63, 200)      | 81 µs  | 1.5 ms      | 18.38x |
| text('Hello!', 10, 10, 255)   | 70 µs  | 1.5 ms      | 20.65x |
| scroll(1, 0)                  | 4.0 ms | 3.4 ms      | 0.86x  |
| ellipse(64, 32, 30, 20, 180)  | 97 µs  | 3.0 ms      | 30.58x |
| ellipse(..., filled)          | 190 µs | 14.6 ms     | 76.72x |
| poly(triangle, outline)       | 80 µs  | 1.3 ms      | 16.19x |
| poly(triangle, filled)        | 259 µs | 6.5 ms      | 24.97x |

## Summary Statistics

### Performance by Category

| Category         | Operation Count | Faster (< 1x) | Similar (1-5x) | Slower (> 5x) |
| ---------------- | --------------- | ------------- | -------------- | ------------- |
| Total Operations | 39              | 4             | 6              | 29            |

### Pixel() Performance Across Formats

| Format    | C Time | Python Time | Ratio |
| --------- | ------ | ----------- | ----- |
| MONO_VLSB | 13 µs  | 32 µs       | 2.41x |
| RGB565    | 13 µs  | 32 µs       | 2.39x |
| GS8       | 13 µs  | 32 µs       | 2.39x |

### Fill() Performance Across Formats

| Format    | C Time | Python Time | Ratio |
| --------- | ------ | ----------- | ----- |
| MONO_VLSB | 566 µs | 328 µs      | 0.58x |
| RGB565    | 349 µs | 263 µs      | 0.76x |
| GS8       | 65 µs  | 195 µs      | 2.99x |

### Line() Performance Across Formats

| Format    | C Time | Python Time | Ratio  |
| --------- | ------ | ----------- | ------ |
| MONO_VLSB | 91 µs  | 1.5 ms      | 16.67x |
| RGB565    | 82 µs  | 1.5 ms      | 18.15x |
| GS8       | 81 µs  | 1.5 ms      | 18.38x |

### Text() Performance Across Formats

| Format    | C Time | Python Time | Ratio  |
| --------- | ------ | ----------- | ------ |
| MONO_VLSB | 80 µs  | 1.5 ms      | 18.61x |
| RGB565    | 71 µs  | 1.5 ms      | 20.74x |
| GS8       | 70 µs  | 1.5 ms      | 20.65x |

### Scroll() Performance Across Formats

| Format    | C Time | Python Time | Ratio  |
| --------- | ------ | ----------- | ------ |
| MONO_VLSB | 4.9 ms | 254.4 ms    | 52.02x |
| RGB565    | 3.8 ms | 3.5 ms      | 0.93x  |
| GS8       | 4.0 ms | 3.4 ms      | 0.86x  |

### Blit() Performance Across Formats

| Format    | C Time | Python Time | Ratio  |
| --------- | ------ | ----------- | ------ |
| MONO_VLSB | 52 µs  | 2.8 ms      | 53.92x |
| RGB565    | 43 µs  | 179 µs      | 4.08x  |
| GS8       | 45 µs  | 177 µs      | 3.90x  |

## Optimizations Applied

### fill() Method

- Assembly-optimized bulk memory fill using `@micropython.asm_thumb`
- Word-aligned writes (4 bytes at a time) for faster operation
- **Result**: Python faster than C for MONO_VLSB (0.58x) and RGB565 (0.76x)!

### scroll() Method

- Optimized memory copy operations for RGB565 and GS8 formats
- Native `_asm_scroll_*` functions using ARM Thumb-2 assembly
- **Result**: Python faster than C for RGB565 (0.93x) and GS8 (0.86x)!

### text() Method

- Font data imported at module level
- Full viper optimization with `_render_text()` function
- String converted to bytes, processed via `ptr8()` for direct memory access
- Character iteration, font lookup, and rendering all in viper
- **Result**: ~27% faster than previous (25-28x → 18-20x)

### line() Method

- Bresenham line algorithm implemented in viper
- **Result**: ~30% faster than previous (23-26x → 16-18x)

### blit() Method

- Optimized memory operations for RGB565 and GS8
- **Result**: RGB565 improved from 6.38x to 4.08x
