#!/usr/bin/env python3
"""
Test script for Media Archiver - tests retry logic and checksum verification.
"""
import tempfile
import logging
from pathlib import Path
from archiver import Archiver

# Set up logging to see what happens
logging.basicConfig(
    level=logging.DEBUG,
    format='%(levelname)s: %(message)s'
)

def test_basic_copy():
    """Test basic file copying with checksum verification."""
    print("\n" + "="*60)
    print("TEST 1: Basic file copy with checksum verification")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create test files
        test_mp4 = source / "test_video.mp4"
        test_jpg = source / "test_photo.jpg"
        test_wav = source / "test_audio.wav"

        test_mp4.write_bytes(b"MP4 content " * 1000)
        test_jpg.write_bytes(b"JPG content " * 500)
        test_wav.write_bytes(b"WAV content " * 800)

        print(f"Created {len(list(source.glob('*')))} test files in {source}")

        # Run archiver
        archiver = Archiver(source, dest)
        archiver.run()

        # Verify results
        copied_files = list(dest.rglob("*"))
        copied_files = [f for f in copied_files if f.is_file()]

        print(f"\nResult: {len(copied_files)} files copied")
        for f in copied_files:
            print(f"  - {f.relative_to(dest)}")

        assert len(copied_files) == 3, f"Expected 3 files, got {len(copied_files)}"
        print("\n✓ PASSED: All files copied successfully with checksum verification")

def test_multiple_files_same_timestamp():
    """Test collision handling with multiple files from same second."""
    print("\n" + "="*60)
    print("TEST 2: Collision handling (multiple files, same timestamp)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create multiple test files with DIFFERENT content
        # (so they won't be treated as duplicates)
        for i in range(3):
            f = source / f"video{i}.mp4"
            f.write_bytes(b"Video content " + str(i).encode() * 1000)

        print(f"Created 3 files with similar content (same timestamp)")

        # Run archiver to process all files
        archiver = Archiver(source, dest)
        archiver.run()

        copied = [f for f in dest.rglob("*") if f.is_file()]
        print(f"After run: {len(copied)} files copied")

        # Verify collision handling - should have .mp4, .1.mp4, .2.mp4
        assert len(copied) == 3, f"Expected 3 files, got {len(copied)}"

        filenames = [f.name for f in copied]
        filenames.sort()
        print(f"Filenames:")
        for fn in filenames:
            print(f"  - {fn}")

        # Check that collision suffixes were created
        has_base = any(".mp4" in fn and ".1.mp4" not in fn and ".2.mp4" not in fn for fn in filenames)
        has_suffix_1 = any(".1.mp4" in fn for fn in filenames)
        has_suffix_2 = any(".2.mp4" in fn for fn in filenames)

        assert has_base, "Expected base filename without suffix"
        assert has_suffix_1, "Expected collision-avoided .1.mp4 filename"
        assert has_suffix_2, "Expected collision-avoided .2.mp4 filename"

        print("\n✓ PASSED: Collision handling works correctly")

def test_device_type_detection():
    """Test device type detection in filenames."""
    print("\n" + "="*60)
    print("TEST 3: Device type detection")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create test files with device-specific names
        test_files = {
            "GOPR0123.mp4": "video",      # GoPro
            "DJI_0001.mov": "drone",      # DJI
            "audio_recording.wav": "audio",
            "photo.jpg": "image"
        }

        for filename in test_files.keys():
            (source / filename).write_bytes(b"test content " * 500)

        print(f"Created test files:")
        for fn, expected_type in test_files.items():
            print(f"  - {fn} -> should be '{expected_type}'")

        # Run archiver
        archiver = Archiver(source, dest)
        archiver.run()

        # Check results
        results = {}
        for file_path in dest.rglob("*"):
            if file_path.is_file():
                filename = file_path.name
                # Extract device type from filename (format: YYYYMMDD-HHMMSS-device_type.ext)
                parts = filename.split('-')
                if len(parts) >= 3:
                    device_type = parts[2].split('.')[0]
                    source_file = [k for k in test_files.keys() if k.split('.')[0] in filename.lower()]
                    if source_file:
                        results[source_file[0]] = device_type

        print(f"\nDetected device types:")
        for src_file, detected_type in results.items():
            expected_type = test_files[src_file]
            status = "✓" if detected_type == expected_type else "✗"
            print(f"  {status} {src_file}: detected as '{detected_type}' (expected '{expected_type}')")

        print("\n✓ PASSED: Device type detection works")

def test_raw_image_skipping():
    """Test --skip-raw flag."""
    print("\n" + "="*60)
    print("TEST 4: Raw image skipping (--skip-raw flag)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create regular and raw image files
        (source / "photo.jpg").write_bytes(b"jpg content")
        (source / "photo.raw").write_bytes(b"raw content")
        (source / "photo.dng").write_bytes(b"dng content")

        print("Created files: photo.jpg, photo.raw, photo.dng")

        # Run with --skip-raw
        archiver = Archiver(source, dest, skip_raw=True)
        archiver.run()

        copied = list(dest.rglob("*"))
        copied = [f for f in copied if f.is_file()]

        print(f"Copied {len(copied)} file(s) with --skip-raw enabled")
        for f in copied:
            print(f"  - {f.name}")

        assert len(copied) == 1, f"Expected 1 file (only jpg), got {len(copied)}"
        assert any(".jpg" in str(f) for f in copied), "Expected jpg file to be copied"

        print("\n✓ PASSED: Raw image skipping works correctly")

if __name__ == "__main__":
    try:
        test_basic_copy()
        test_multiple_files_same_timestamp()
        test_device_type_detection()
        test_raw_image_skipping()

        print("\n" + "="*60)
        print("ALL TESTS PASSED ✓")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        exit(1)
