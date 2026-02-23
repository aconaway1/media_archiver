#!/usr/bin/env python3
"""
Test the --overwrite flag functionality.
"""
import tempfile
import logging
import sys
from pathlib import Path
from archiver import Archiver

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)

def test_overwrite_flag():
    """Test the --overwrite flag with different file contents."""
    import time
    import os
    print("\n" + "="*60)
    print("TEST: --overwrite flag with different file contents")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Set a known timestamp for consistent filenames
        file_timestamp = 1708677439  # 2024-02-23 08:17:19

        # Test 1: Without --overwrite flag (should skip)
        print("\n--- Test 1: Without --overwrite flag ---")

        # Create initial destination file with ORIGINAL CONTENT
        date_dir = dest / "2024" / "02" / "23"
        date_dir.mkdir(parents=True, exist_ok=True)
        dest_file = date_dir / "20240223-023719-video.mp4"
        dest_file.write_bytes(b"ORIGINAL CONTENT" * 100)
        os.utime(dest_file, (file_timestamp, file_timestamp))
        print(f"✓ Created destination file with 'ORIGINAL CONTENT'")

        # Create source file with NEW CONTENT and same timestamp
        source_file = source / "source_video.mp4"
        source_file.write_bytes(b"NEW CONTENT" * 100)
        os.utime(source_file, (file_timestamp, file_timestamp))
        print(f"✓ Created source file with 'NEW CONTENT'")

        time.sleep(0.1)

        # Run archiver WITHOUT overwrite flag
        archiver = Archiver(source, dest, overwrite=False)
        archiver.run()

        # Check that original content is preserved
        with open(dest_file, 'rb') as f:
            content = f.read()
        if b"ORIGINAL" in content and b"NEW" not in content:
            print("✓ PASSED: Original file preserved (not overwritten)")
        else:
            print("✗ FAILED: Original file was overwritten!")
            return False

        # Test 2: WITH --overwrite flag (should replace)
        print("\n--- Test 2: With --overwrite flag ---")

        # Reset the destination file to ORIGINAL CONTENT
        dest_file.write_bytes(b"ORIGINAL CONTENT" * 100)
        os.utime(dest_file, (file_timestamp, file_timestamp))
        print(f"✓ Reset destination file to 'ORIGINAL CONTENT'")

        # Reset the source file to NEW CONTENT with same timestamp
        source_file.write_bytes(b"NEW CONTENT" * 100)
        os.utime(source_file, (file_timestamp, file_timestamp))
        print(f"✓ Reset source file to 'NEW CONTENT'")

        time.sleep(0.1)

        # Run archiver WITH overwrite flag
        archiver = Archiver(source, dest, overwrite=True)
        archiver.run()

        # Check that file was overwritten with new content
        with open(dest_file, 'rb') as f:
            content = f.read()
        if b"NEW" in content and b"ORIGINAL" not in content:
            print("✓ PASSED: File was overwritten with new content")
        else:
            print("✗ FAILED: File was not overwritten!")
            print(f"   Content found: {content[:50]}")
            return False

        return True

if __name__ == "__main__":
    try:
        if test_overwrite_flag():
            print("\n" + "="*60)
            print("✓ ALL OVERWRITE TESTS PASSED")
            print("="*60)
            sys.exit(0)
        else:
            sys.exit(1)
    except Exception as e:
        print(f"\n✗ TEST ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
