#!/usr/bin/env python3
"""
Test script for source directory scanning.
"""
import tempfile
import logging
import sys
from pathlib import Path
from source_scanner import SourceScanner

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


def test_direct_media_files():
    """Test scanning a directory that directly contains media files."""
    print("\n" + "="*60)
    print("TEST 1: Direct media files (backward compatible)")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir)
        (source / "video.mp4").write_bytes(b"video")
        (source / "photo.jpg").write_bytes(b"photo")

        scanner = SourceScanner()
        detected = scanner.scan(source)

        assert len(detected) == 1, f"Expected 1 source, got {len(detected)}"
        assert detected[0].source_dir == source
        assert detected[0].file_count == 2
        print(f"  Detected: {detected[0]}")

    print("✓ PASSED: Direct media files detected as single source")


def test_gopro_structure():
    """Test scanning a GoPro SD card structure."""
    print("\n" + "="*60)
    print("TEST 2: GoPro directory structure")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        volume = Path(tmpdir)
        gopro_dir = volume / "DCIM" / "100GOPRO"
        gopro_dir.mkdir(parents=True)
        (gopro_dir / "GOPR0001.MP4").write_bytes(b"video1")
        (gopro_dir / "GOPR0002.MP4").write_bytes(b"video2")
        (gopro_dir / "GOPR0003.MP4").write_bytes(b"video3")

        scanner = SourceScanner()
        detected = scanner.scan(volume)

        assert len(detected) == 1, f"Expected 1 source, got {len(detected)}"
        assert detected[0].device_hint == 'gopro'
        assert detected[0].file_count == 3
        assert detected[0].source_dir == gopro_dir
        print(f"  Detected: {detected[0]}")

    print("✓ PASSED: GoPro structure detected correctly")


def test_dji_structure():
    """Test scanning a DJI SD card structure."""
    print("\n" + "="*60)
    print("TEST 3: DJI directory structure")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        volume = Path(tmpdir)
        dji_dir = volume / "DCIM" / "DJI_001"
        dji_dir.mkdir(parents=True)
        (dji_dir / "DJI_0001.MOV").write_bytes(b"video")
        (dji_dir / "DJI_0001.SRT").write_bytes(b"telemetry")
        (dji_dir / "DJI_0002.MOV").write_bytes(b"video2")

        scanner = SourceScanner()
        detected = scanner.scan(volume)

        assert len(detected) == 1, f"Expected 1 source, got {len(detected)}"
        assert detected[0].device_hint == 'dji'
        assert detected[0].file_count == 3
        print(f"  Detected: {detected[0]}")

    print("✓ PASSED: DJI structure detected correctly")


def test_tascam_structure():
    """Test scanning a Tascam recorder structure."""
    print("\n" + "="*60)
    print("TEST 4: Tascam directory structure")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        volume = Path(tmpdir)
        music_dir = volume / "MUSIC"
        music_dir.mkdir()
        (music_dir / "recording_001.wav").write_bytes(b"audio1")
        (music_dir / "recording_002.wav").write_bytes(b"audio2")

        scanner = SourceScanner()
        detected = scanner.scan(volume)

        assert len(detected) == 1, f"Expected 1 source, got {len(detected)}"
        assert detected[0].device_hint == 'tascam'
        assert detected[0].file_count == 2
        print(f"  Detected: {detected[0]}")

    print("✓ PASSED: Tascam structure detected correctly")


def test_multiple_subdirectories():
    """Test scanning with multiple media subdirectories."""
    print("\n" + "="*60)
    print("TEST 5: Multiple subdirectories")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        volume = Path(tmpdir)

        # GoPro dirs
        gp1 = volume / "DCIM" / "100GOPRO"
        gp2 = volume / "DCIM" / "101GOPRO"
        gp1.mkdir(parents=True)
        gp2.mkdir(parents=True)
        (gp1 / "GOPR0001.MP4").write_bytes(b"video1")
        (gp2 / "GOPR0010.MP4").write_bytes(b"video2")
        (gp2 / "GOPR0011.MP4").write_bytes(b"video3")

        scanner = SourceScanner()
        detected = scanner.scan(volume)

        assert len(detected) == 2, f"Expected 2 sources, got {len(detected)}"
        print(f"  Source 1: {detected[0]}")
        print(f"  Source 2: {detected[1]}")

        # Verify both are detected
        dirs = [d.source_dir for d in detected]
        assert gp1 in dirs, "100GOPRO should be detected"
        assert gp2 in dirs, "101GOPRO should be detected"

    print("✓ PASSED: Multiple subdirectories detected correctly")


def test_empty_volume():
    """Test scanning an empty volume."""
    print("\n" + "="*60)
    print("TEST 6: Empty volume")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        volume = Path(tmpdir)

        scanner = SourceScanner()
        detected = scanner.scan(volume)

        assert len(detected) == 0, f"Expected 0 sources, got {len(detected)}"

    print("✓ PASSED: Empty volume returns no sources")


def test_macos_metadata_excluded():
    """Test that macOS metadata files are not counted."""
    print("\n" + "="*60)
    print("TEST 7: macOS metadata files excluded")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        source = Path(tmpdir)
        (source / "video.mp4").write_bytes(b"video")
        (source / "._video.mp4").write_bytes(b"metadata")

        scanner = SourceScanner()
        detected = scanner.scan(source)

        assert len(detected) == 1
        assert detected[0].file_count == 1, f"Expected 1 file (excluding ._), got {detected[0].file_count}"

    print("✓ PASSED: macOS metadata files excluded from count")


def test_mixed_device_volume():
    """Test a volume with mixed device types."""
    print("\n" + "="*60)
    print("TEST 8: Mixed device types on one volume")
    print("="*60)

    with tempfile.TemporaryDirectory() as tmpdir:
        volume = Path(tmpdir)

        # DJI in DCIM
        dji = volume / "DCIM" / "DJI_001"
        dji.mkdir(parents=True)
        (dji / "DJI_0001.MOV").write_bytes(b"drone")

        # Audio in MUSIC
        music = volume / "MUSIC"
        music.mkdir()
        (music / "recording.wav").write_bytes(b"audio")

        scanner = SourceScanner()
        detected = scanner.scan(volume)

        assert len(detected) == 2, f"Expected 2 sources, got {len(detected)}"
        hints = {d.device_hint for d in detected}
        assert 'dji' in hints, "Should detect DJI"
        assert 'tascam' in hints, "Should detect Tascam"
        for d in detected:
            print(f"  {d}")

    print("✓ PASSED: Mixed device types detected correctly")


if __name__ == "__main__":
    try:
        test_direct_media_files()
        test_gopro_structure()
        test_dji_structure()
        test_tascam_structure()
        test_multiple_subdirectories()
        test_empty_volume()
        test_macos_metadata_excluded()
        test_mixed_device_volume()

        print("\n" + "="*60)
        print("ALL SOURCE SCANNER TESTS PASSED ✓")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
