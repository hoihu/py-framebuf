"""
Simple script to run framebuffer benchmarks
Upload this along with fb_opt.py and test.py to your MicroPython device
"""

try:
    # Local import - works when files are in same directory
    import test


    print("="*60)
    print("MicroPython Framebuffer Benchmark Suite")
    print("="*60)
    print()
    print("This will compare:")
    print("  1. Built-in C framebuffer module")
    print("  2. Pure Python with @micropython.viper")
    print("  3. Pure Python with @micropython.native")
    print()
    print("Starting benchmarks...")
    print()

    # Run quick verification first
    print("Step 1: Quick Verification Test")
    print("-" * 60)
    if test.quick_test():
        print("\n✓ Verification passed!\n")

        # Run full benchmark suite
        print("Step 2: Full Benchmark Suite")
        print("-" * 60)
        test.run_standard_benchmarks()

        print("\n" + "="*60)
        print("Benchmark complete!")
        print("="*60)
    else:
        print("\n✗ Verification failed!")
        print("Please check the implementation.")

except ImportError as e:
    print("Error: Missing required modules")
    print("Details: {}".format(e))
    print("\nMake sure you have uploaded:")
    print("  - framebuffer_pure.py")
    print("  - test.py")
    print("  - run.py (this file)")

except Exception as e:
    print("Unexpected error: {}".format(e))
    import sys
    sys.print_exception(e)