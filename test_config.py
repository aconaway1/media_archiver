#!/usr/bin/env python3
"""
Test script for YAML config file loading.
"""
import tempfile
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')


def test_no_config_file():
    """Test that missing config file returns empty dict."""
    print("\n" + "="*60)
    print("TEST 1: No config file")
    print("="*60)

    # Temporarily patch the config path
    import main
    original_file = main.__file__

    with tempfile.TemporaryDirectory() as tmpdir:
        # Point to a directory with no config.yml
        main.__file__ = str(Path(tmpdir) / 'main.py')
        config = main.load_config()
        main.__file__ = original_file

    assert config == {}, f"Expected empty dict, got {config}"
    print("✓ PASSED: Missing config file returns empty dict")


def test_config_with_values():
    """Test that config values are loaded correctly."""
    print("\n" + "="*60)
    print("TEST 2: Config with values")
    print("="*60)

    import main

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / 'config.yml'
        config_path.write_text(
            "destination: ~/Videos/Archive\n"
            "skip_raw: true\n"
            "recent: 7\n"
            "device_tag: mavic3\n"
        )
        original_file = main.__file__
        main.__file__ = str(Path(tmpdir) / 'main.py')
        config = main.load_config()
        main.__file__ = original_file

    assert config['destination'] == '~/Videos/Archive', f"Unexpected destination: {config.get('destination')}"
    assert config['skip_raw'] == True, f"Unexpected skip_raw: {config.get('skip_raw')}"
    assert config['recent'] == 7, f"Unexpected recent: {config.get('recent')}"
    assert config['device_tag'] == 'mavic3', f"Unexpected device_tag: {config.get('device_tag')}"

    print(f"  destination: {config['destination']}")
    print(f"  skip_raw: {config['skip_raw']}")
    print(f"  recent: {config['recent']}")
    print(f"  device_tag: {config['device_tag']}")
    print("✓ PASSED: Config values loaded correctly")


def test_malformed_yaml():
    """Test that malformed YAML returns empty dict gracefully."""
    print("\n" + "="*60)
    print("TEST 3: Malformed YAML")
    print("="*60)

    import main

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / 'config.yml'
        config_path.write_text("this is: [not: valid: yaml: {{{}}")
        original_file = main.__file__
        main.__file__ = str(Path(tmpdir) / 'main.py')
        config = main.load_config()
        main.__file__ = original_file

    assert config == {}, f"Expected empty dict for malformed YAML, got {config}"
    print("✓ PASSED: Malformed YAML returns empty dict")


def test_empty_config():
    """Test that empty config file returns empty dict."""
    print("\n" + "="*60)
    print("TEST 4: Empty config file")
    print("="*60)

    import main

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / 'config.yml'
        config_path.write_text("")
        original_file = main.__file__
        main.__file__ = str(Path(tmpdir) / 'main.py')
        config = main.load_config()
        main.__file__ = original_file

    assert config == {}, f"Expected empty dict for empty config, got {config}"
    print("✓ PASSED: Empty config file returns empty dict")


if __name__ == "__main__":
    try:
        test_no_config_file()
        test_config_with_values()
        test_malformed_yaml()
        test_empty_config()

        print("\n" + "="*60)
        print("ALL CONFIG TESTS PASSED ✓")
        print("="*60)
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
