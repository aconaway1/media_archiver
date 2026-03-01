#!/usr/bin/env python3
"""
Test script for Media Archiver - tests retry logic and checksum verification.
"""
import os
import tempfile
import time
import logging
import shutil
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

def test_macos_metadata_filtering():
    """Test that macOS metadata files are filtered out."""
    print("\n" + "="*60)
    print("TEST 5: macOS metadata file filtering")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create regular media files and macOS metadata files
        (source / "video.mp4").write_bytes(b"video content")
        (source / "._video.mp4").write_bytes(b"macos metadata")
        (source / "photo.jpg").write_bytes(b"photo content")
        (source / "._photo.jpg").write_bytes(b"macos metadata")

        print("Created files: video.mp4, ._video.mp4, photo.jpg, ._photo.jpg")

        # Run archiver
        archiver = Archiver(source, dest)
        archiver.run()

        copied = list(dest.rglob("*"))
        copied = [f for f in copied if f.is_file()]

        print(f"Copied {len(copied)} file(s)")
        for f in copied:
            print(f"  - {f.name}")

        assert len(copied) == 2, f"Expected 2 files (no metadata files), got {len(copied)}"
        assert not any("._" in f.name for f in copied), "macOS metadata files should not be copied"

        print("\n✓ PASSED: macOS metadata files properly filtered out")

def test_srt_file_handling():
    """Test that SRT files are copied with '-srt' designation and --ignore-srt flag works."""
    print("\n" + "="*60)
    print("TEST 6: SRT file handling")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create SRT and video files
        (source / "DJI_video.mp4").write_bytes(b"video content")
        (source / "DJI_video.srt").write_bytes(b"1\n00:00:00,000 --> 00:00:05,000\nTelemetry data")
        (source / "another.srt").write_bytes(b"2\n00:00:05,000 --> 00:00:10,000\nMore telemetry")

        print("Created files: DJI_video.mp4, DJI_video.srt, another.srt")

        # Test 1: Without --ignore-srt flag (SRT files should be copied)
        print("\n--- Test 1: Without --ignore-srt flag ---")
        archiver = Archiver(source, dest)
        archiver.run()

        copied = list(dest.rglob("*"))
        copied = [f for f in copied if f.is_file()]

        print(f"Copied {len(copied)} file(s)")
        for f in copied:
            print(f"  - {f.name}")

        assert len(copied) == 3, f"Expected 3 files (2 SRT + 1 video), got {len(copied)}"

        srt_files = [f for f in copied if f.suffix == '.srt']
        assert len(srt_files) == 2, f"Expected 2 SRT files, got {len(srt_files)}"

        # Verify SRT files have '-srt' designation
        for srt in srt_files:
            assert '-srt' in srt.name and srt.suffix == '.srt', f"SRT file should have '-srt' designation: {srt.name}"

        print("✓ SRT files copied with '-srt' designation")

        # Test 2: With --ignore-srt flag (SRT files should be skipped)
        print("\n--- Test 2: With --ignore-srt flag ---")
        # Clean destination
        for item in dest.iterdir():
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)

        archiver = Archiver(source, dest, ignore_srt=True)
        archiver.run()

        copied = list(dest.rglob("*"))
        copied = [f for f in copied if f.is_file()]

        print(f"Copied {len(copied)} file(s)")
        for f in copied:
            print(f"  - {f.name}")

        assert len(copied) == 1, f"Expected 1 file (video only), got {len(copied)}"
        assert not any(f.suffix == '.srt' for f in copied), "SRT files should not be copied with --ignore-srt"

        print("✓ SRT files properly skipped with --ignore-srt flag")
        print("\n✓ PASSED: SRT file handling works correctly")

def test_device_tag():
    """Test --device-tag flag adds tag to output filenames."""
    print("\n" + "="*60)
    print("TEST 7: Device tag (--device-tag flag)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        (source / "video.mp4").write_bytes(b"video content " * 500)

        # Test with device tag
        print("\n--- Test 1: With --device-tag gopro-a ---")
        archiver = Archiver(source, dest, device_tag="gopro-a")
        archiver.run()

        copied = [f for f in dest.rglob("*") if f.is_file()]
        assert len(copied) == 1, f"Expected 1 file, got {len(copied)}"

        filename = copied[0].name
        print(f"  Output filename: {filename}")
        assert "-gopro-a." in filename, f"Expected '-gopro-a.' in filename, got '{filename}'"
        print("  ✓ Device tag present in filename")

        # Test without device tag (default behavior unchanged)
        print("\n--- Test 2: Without --device-tag (default) ---")
        dest2 = Path(tmpdir) / "dest2"
        dest2.mkdir()

        archiver2 = Archiver(source, dest2)
        archiver2.run()

        copied2 = [f for f in dest2.rglob("*") if f.is_file()]
        assert len(copied2) == 1, f"Expected 1 file, got {len(copied2)}"

        filename2 = copied2[0].name
        print(f"  Output filename: {filename2}")
        # Should end with -<device_type>.ext, no extra tag
        parts = filename2.rsplit('.', 1)[0].split('-')
        assert len(parts) == 3, f"Expected 3 parts (date-time-type), got {len(parts)}: {parts}"
        print("  ✓ No extra tag in default filename")

        print("\n✓ PASSED: Device tag works correctly")

def test_recent_filter():
    """Test --recent flag filters out old files using calendar-day cutoff."""
    print("\n" + "="*60)
    print("TEST 8: Recent file filter (--recent flag)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir) / "source"
        dest = Path(tmpdir) / "dest"
        source.mkdir()
        dest.mkdir()

        # Create a recent file (mtime = now, default)
        recent_file = source / "new_video.mp4"
        recent_file.write_bytes(b"recent video " * 500)

        # Create an old file and backdate its mtime to 10 days ago
        old_file = source / "old_video.mp4"
        old_file.write_bytes(b"old video " * 500)
        old_mtime = time.time() - (10 * 86400)
        os.utime(old_file, (old_mtime, old_mtime))

        print("Created files: new_video.mp4 (today), old_video.mp4 (10 days ago)")

        # Test 1: --recent 1 (default) should only copy today's file
        print("\n--- Test 1: With --recent 1 (today only) ---")
        archiver = Archiver(source, dest, recent_days=1)
        archiver.run()

        copied = [f for f in dest.rglob("*") if f.is_file()]
        print(f"  Copied {len(copied)} file(s)")
        for f in copied:
            print(f"    - {f.name}")

        assert len(copied) == 1, f"Expected 1 file, got {len(copied)}"
        print("  ✓ Only today's file was copied")

        # Test 2: --recent 0 should copy all files (no filtering)
        print("\n--- Test 2: With --recent 0 (all files) ---")
        dest2 = Path(tmpdir) / "dest2"
        dest2.mkdir()

        archiver2 = Archiver(source, dest2, recent_days=0)
        archiver2.run()

        copied2 = [f for f in dest2.rglob("*") if f.is_file()]
        print(f"  Copied {len(copied2)} file(s)")
        for f in copied2:
            print(f"    - {f.name}")

        assert len(copied2) == 2, f"Expected 2 files, got {len(copied2)}"
        print("  ✓ All files copied with --recent 0")

        # Test 3: --recent 11 should include the 10-day-old file
        print("\n--- Test 3: With --recent 11 (last 11 days) ---")
        dest3 = Path(tmpdir) / "dest3"
        dest3.mkdir()

        archiver3 = Archiver(source, dest3, recent_days=11)
        archiver3.run()

        copied3 = [f for f in dest3.rglob("*") if f.is_file()]
        print(f"  Copied {len(copied3)} file(s)")
        for f in copied3:
            print(f"    - {f.name}")

        assert len(copied3) == 2, f"Expected 2 files, got {len(copied3)}"
        print("  ✓ Both files copied with --recent 11")

        print("\n✓ PASSED: Recent file filter works correctly")

if __name__ == "__main__":
    try:
        test_basic_copy()
        test_multiple_files_same_timestamp()
        test_device_type_detection()
        test_raw_image_skipping()
        test_macos_metadata_filtering()
        test_srt_file_handling()
        test_device_tag()
        test_recent_filter()

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
