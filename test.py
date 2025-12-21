"""
Framebuffer Performance Benchmarking Suite
Compares built-in C framebuffer module vs pure MicroPython implementations
"""
import framebuf
import time
import gc

# Local import - works when files are in same directory
try:
    from fb_opt import FrameBufferPure, FrameBufferNative, FrameBufferAsmThumb, FrameBufferHybridOptimized
except ImportError:
    # Try parent directory if in tests subdirectory
    import sys
    sys.path.insert(0, '..')
    from fb_opt import FrameBufferPure, FrameBufferNative, FrameBufferAsmThumb, FrameBufferHybridOptimized


class BenchmarkRunner:
    """Manages benchmark execution and reporting"""

    def __init__(self, width=200, height=100, format=framebuf.MONO_VLSB):
        self.width = width
        self.height = height
        self.format = format
        self.results = []

        # Calculate buffer size
        if format == framebuf.MONO_VLSB or format == framebuf.MONO_HLSB:
            self.buffer_size = ((height + 7) // 8) * width
        elif format == framebuf.RGB565:
            self.buffer_size = width * height * 2
        elif format == framebuf.GS8:
            self.buffer_size = width * height
        else:
            self.buffer_size = ((height + 7) // 8) * width

    def create_framebuffers(self):
        """Create four framebuffers for comparison"""
        # C implementation
        buf_c = bytearray(self.buffer_size)
        fb_builtin = framebuf.FrameBuffer(buf_c, self.width, self.height, self.format)

        # Viper implementation
        buf_viper = bytearray(self.buffer_size)
        fb_viper = FrameBufferPure(buf_viper, self.width, self.height, self.format)

        # Native implementation
        buf_native = bytearray(self.buffer_size)
        fb_native = FrameBufferNative(buf_native, self.width, self.height, self.format)

        # Asm Thumb implementation
        buf_asm = bytearray(self.buffer_size)
        fb_asm = FrameBufferAsmThumb(buf_asm, self.width, self.height, self.format)

        # Hybrid Optimized implementation
        buf_hybrid = bytearray(self.buffer_size)
        fb_hybrid = FrameBufferHybridOptimized(buf_hybrid, self.width, self.height, self.format)

        return (fb_builtin, buf_c), (fb_viper, buf_viper), (fb_native, buf_native), (fb_asm, buf_asm), (fb_hybrid, buf_hybrid)

    def time_operation(self, func, iterations=1000):
        """Time an operation with garbage collection"""
        gc.collect()
        start = time.ticks_us()
        for _ in range(iterations):
            func()
        end = time.ticks_us()
        return time.ticks_diff(end, start)

    def verify_buffers_match(self, buf1, buf2, buf3, buf4, buf5, test_name):
        """Verify all five buffers have identical content"""
        def show_diff(name1, name2, b1, b2):
            print("  ⚠ MISMATCH: {} vs {} in {}".format(name1, name2, test_name))
            print("    First 10 differences:")
            count = 0
            for i in range(min(len(b1), len(b2))):
                if b1[i] != b2[i]:
                    print("      byte[{}]: {}=0x{:02x} (0b{:08b})  {}=0x{:02x} (0b{:08b})".format(
                        i, name1, b1[i], b1[i], name2, b2[i], b2[i]))
                    count += 1
                    if count >= 10:
                        break
            if count < 10:
                print("    Total differences: {}".format(count))

        if buf1 != buf2:
            show_diff("C", "Viper", buf1, buf2)
            return False
        if buf1 != buf3:
            show_diff("C", "Native", buf1, buf3)
            return False
        if buf1 != buf4:
            show_diff("C", "AsmThumb", buf1, buf4)
            return False
        if buf1 != buf5:
            show_diff("C", "Hybrid", buf1, buf5)
            return False
        return True

    def benchmark_operation(self, name, setup_func, iterations=1000):
        """
        Benchmark a single operation across all implementations
        setup_func: function that takes (fb, buffer) and returns operation to benchmark
        """
        print("\n" + "=" * 60)
        print("Benchmarking: {}".format(name))
        print("=" * 60)

        # Create framebuffers
        (fb_c, buf_c), (fb_viper, buf_viper), (fb_native, buf_native), (fb_asm, buf_asm), (fb_hybrid, buf_hybrid) = self.create_framebuffers()

        # Setup operations
        op_c = setup_func(fb_c, buf_c)
        op_viper = setup_func(fb_viper, buf_viper)
        op_native = setup_func(fb_native, buf_native)
        op_asm = setup_func(fb_asm, buf_asm)
        op_hybrid = setup_func(fb_hybrid, buf_hybrid)

        # Run benchmarks
        time_c = self.time_operation(op_c, iterations)
        time_viper = self.time_operation(op_viper, iterations)
        time_native = self.time_operation(op_native, iterations)
        time_asm = self.time_operation(op_asm, iterations)
        time_hybrid = self.time_operation(op_hybrid, iterations)

        # Verify outputs match
        match = self.verify_buffers_match(buf_c, buf_viper, buf_native, buf_asm, buf_hybrid, name)

        # Calculate relative performance
        speedup_viper = (time_c / time_viper) if time_viper > 0 else 0
        speedup_native = (time_c / time_native) if time_native > 0 else 0
        speedup_asm = (time_c / time_asm) if time_asm > 0 else 0
        speedup_hybrid = (time_c / time_hybrid) if time_hybrid > 0 else 0

        # Display results
        print("Iterations: {}".format(iterations))
        print("\nResults:")
        print("  C (built-in):     {:>10} µs  (baseline)".format(time_c))
        print("  Viper:            {:>10} µs  ({:.2f}x)".format(time_viper, speedup_viper))
        print("  Native:           {:>10} µs  ({:.2f}x)".format(time_native, speedup_native))
        print("  AsmThumb:         {:>10} µs  ({:.2f}x)".format(time_asm, speedup_asm))
        print("  Hybrid:           {:>10} µs  ({:.2f}x)".format(time_hybrid, speedup_hybrid))
        print("\nOutput verification: {}".format('✓ PASS' if match else '✗ FAIL'))

        # Store results
        result = {
            'name': name,
            'iterations': iterations,
            'time_c': time_c,
            'time_viper': time_viper,
            'time_native': time_native,
            'time_asm': time_asm,
            'time_hybrid': time_hybrid,
            'speedup_viper': speedup_viper,
            'speedup_native': speedup_native,
            'speedup_asm': speedup_asm,
            'speedup_hybrid': speedup_hybrid,
            'match': match
        }
        self.results.append(result)

        return result

    def run_all_benchmarks(self):
        """Run complete benchmark suite"""
        print("\n" + "#" * 60)
        print("# FRAMEBUFFER PERFORMANCE BENCHMARK SUITE")
        print("# Resolution: {}x{}".format(self.width, self.height))
        print("# Format: {}".format(self._format_name()))
        print("# Buffer size: {} bytes".format(self.buffer_size))
        print("#" * 60)

        # 1. Pixel operations
        self.benchmark_operation(
            "pixel() - single pixel writes",
            lambda fb, buf: lambda: [fb.pixel(50, 50, 1) for _ in range(100)],
            iterations=100
        )

        # 2. Horizontal lines
        self.benchmark_operation(
            "hline() - horizontal line",
            lambda fb, buf: lambda: fb.hline(0, 50, self.width, 1),
            iterations=1000
        )

        # 3. Vertical lines
        self.benchmark_operation(
            "vline() - vertical line",
            lambda fb, buf: lambda: fb.vline(50, 0, self.height, 1),
            iterations=1000
        )

        # 4. Fill operation
        self.benchmark_operation(
            "fill() - fill entire buffer",
            lambda fb, buf: lambda: fb.fill(1),
            iterations=500
        )

        # 5. Fill rectangle
        self.benchmark_operation(
            "fill_rect() - 50x50 rectangle",
            lambda fb, buf: lambda: fb.fill_rect(10, 10, 50, 50, 1),
            iterations=500
        )

        # 6. Rectangle outline
        self.benchmark_operation(
            "rect() - 50x50 outline",
            lambda fb, buf: lambda: fb.rect(10, 10, 50, 50, 1, False),
            iterations=500
        )

        # 7. Line drawing
        self.benchmark_operation(
            "line() - diagonal line",
            lambda fb, buf: lambda: fb.line(0, 0, self.width-1, self.height-1, 1),
            iterations=200
        )

        # 8. Complex pattern - grid
        def draw_grid(fb, buf):
            def op():
                fb.fill(0)
                for x in range(0, self.width, 10):
                    fb.vline(x, 0, self.height, 1)
                for y in range(0, self.height, 10):
                    fb.hline(0, y, self.width, 1)
            return op

        self.benchmark_operation(
            "Complex: 10px grid pattern",
            draw_grid,
            iterations=100
        )

        # 9. Multiple pixel writes (scatter pattern)
        def scatter_pixels(fb, buf):
            def op():
                fb.fill(0)
                for i in range(min(100, self.width * self.height // 10)):
                    x = (i * 13) % self.width
                    y = (i * 17) % self.height
                    fb.pixel(x, y, 1)
            return op

        self.benchmark_operation(
            "pixel() - scatter pattern (100 pixels)",
            scatter_pixels,
            iterations=100
        )

        # 10. Multiple hlines (striped pattern)
        def horizontal_stripes(fb, buf):
            def op():
                fb.fill(0)
                for y in range(0, self.height, 2):
                    fb.hline(0, y, self.width, 1)
            return op

        self.benchmark_operation(
            "hline() - horizontal stripes",
            horizontal_stripes,
            iterations=100
        )

        # Print summary
        self.print_summary()

    def _format_name(self):
        """Get human-readable format name"""
        formats = {
            framebuf.MONO_VLSB: "MONO_VLSB",
            framebuf.RGB565: "RGB565",
            framebuf.GS8: "GS8"
        }
        return formats.get(self.format, "UNKNOWN")

    def print_summary(self):
        """Print summary of all benchmark results"""
        print("\n\n" + "#" * 60)
        print("# BENCHMARK SUMMARY")
        print("#" * 60 + "\n")

        print("{:<40} {:<12} {:<12} {:<12} {:<12} {:<12} {:<10} {:<10} {:<10} {:<10} {}".format(
            'Test', 'C (µs)', 'Viper', 'Native', 'AsmThumb', 'Hybrid', 'V-Speed', 'N-Speed', 'A-Speed', 'H-Speed', 'Match'))
        print("-" * 155)

        for r in self.results:
            match_symbol = "✓" if r['match'] else "✗"
            print("{:<40} {:<12} {:<12} {:<12} {:<12} {:<12} {:<10.2f} {:<10.2f} {:<10.2f} {:<10.2f} {}".format(
                r['name'], r['time_c'], r['time_viper'], r['time_native'], r['time_asm'], r['time_hybrid'],
                r['speedup_viper'], r['speedup_native'], r['speedup_asm'], r['speedup_hybrid'], match_symbol))

        # Calculate averages
        avg_viper = sum(r['speedup_viper'] for r in self.results) / len(self.results)
        avg_native = sum(r['speedup_native'] for r in self.results) / len(self.results)
        avg_asm = sum(r['speedup_asm'] for r in self.results) / len(self.results)
        avg_hybrid = sum(r['speedup_hybrid'] for r in self.results) / len(self.results)
        all_match = all(r['match'] for r in self.results)

        print("-" * 155)
        print("{:<40} {:<12} {:<12} {:<12} {:<12} {:<12} {:<10.2f} {:<10.2f} {:<10.2f} {:<10.2f}".format(
            'AVERAGE SPEEDUP:', '', '', '', '', '', avg_viper, avg_native, avg_asm, avg_hybrid))
        print("\nOverall verification: {}".format('✓ ALL TESTS PASSED' if all_match else '✗ SOME TESTS FAILED'))


def run_standard_benchmarks():
    """Run benchmarks with common configurations"""

    configs = [
        (200, 100, framebuf.MONO_VLSB, "200x100 MONO_VLSB"),
        (20, 20, framebuf.MONO_VLSB, "20x20 MONO_VLSB"),
        # Uncomment for additional formats (if supported)
        # (200, 100, framebuf.RGB565, "200x100 RGB565"),
        # (200, 100, framebuf.GS8, "200x100 GS8"),
    ]

    for width, height, fmt, name in configs:
        print("\n\n" + "=" * 60)
        print("CONFIGURATION: {}".format(name))
        print("=" * 60)

        runner = BenchmarkRunner(width, height, fmt)
        runner.run_all_benchmarks()


# Quick test functions
def quick_test():
    """Quick verification test to ensure implementations work"""
    print("Running quick verification test...")

    width, height = 20, 20
    fmt = framebuf.MONO_VLSB
    buffer_size = ((height + 7) // 8) * width

    # Create framebuffers
    buf_c = bytearray(buffer_size)
    buf_viper = bytearray(buffer_size)
    buf_native = bytearray(buffer_size)
    buf_asm = bytearray(buffer_size)
    buf_hybrid = bytearray(buffer_size)

    fb_builtin = framebuf.FrameBuffer(buf_c, width, height, fmt)
    fb_viper = FrameBufferPure(buf_viper, width, height, fmt)
    fb_native = FrameBufferNative(buf_native, width, height, fmt)
    fb_asm = FrameBufferAsmThumb(buf_asm, width, height, fmt)
    fb_hybrid = FrameBufferHybridOptimized(buf_hybrid, width, height, fmt)

    # Test operations
    tests = [
        ("fill", lambda fb: fb.fill(1)),
        ("pixel", lambda fb: fb.pixel(5, 5, 0)),
        ("hline", lambda fb: fb.hline(0, 10, width, 1)),
        ("vline", lambda fb: fb.vline(10, 0, height, 1)),
        ("rect", lambda fb: fb.rect(2, 2, 5, 5, 1)),
        ("fill_rect", lambda fb: fb.fill_rect(12, 12, 5, 5, 0)),
        ("line", lambda fb: fb.line(0, 0, width-1, height-1, 1)),
    ]

    all_pass = True
    for test_name, op in tests:
        # Clear buffers
        for b in [buf_c, buf_viper, buf_native, buf_asm, buf_hybrid]:
            for i in range(len(b)):
                b[i] = 0

        # Run operation
        op(fb_builtin)
        op(fb_viper)
        op(fb_native)
        op(fb_asm)
        op(fb_hybrid)

        # Verify
        if buf_c == buf_viper == buf_native == buf_asm == buf_hybrid:
            print("  ✓ {}".format(test_name))
        else:
            print("  ✗ {} - buffers don't match!".format(test_name))
            all_pass = False

    return all_pass


if __name__ == "__main__":
    print("Framebuffer Performance Benchmark Suite\n")

    # Run quick verification first
    if quick_test():
        print("\n✓ Quick verification passed! Starting full benchmarks...\n")
        run_standard_benchmarks()
    else:
        print("\n✗ Quick verification failed! Please check implementation.\n")
