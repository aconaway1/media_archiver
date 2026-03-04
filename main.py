#!/usr/bin/env python3
"""
Media Archiver CLI - Archive and rename media files to standardized format.
"""
import argparse
import sys
import logging
from pathlib import Path
from archiver import Archiver

logger = logging.getLogger(__name__)


def load_config() -> dict:
    """Load configuration from config.yml if it exists."""
    config_path = Path(__file__).parent / 'config.yml'
    if not config_path.exists():
        return {}
    try:
        import yaml
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        return config if isinstance(config, dict) else {}
    except Exception as e:
        print(f"WARNING: Failed to parse config.yml: {e}", file=sys.stderr)
        return {}


def validate_paths(source: Path, destination: Path) -> bool:
    """Validate that source exists and destination is writable."""
    if not source.exists():
        logger.error(f"Source directory does not exist: {source}")
        return False

    if not source.is_dir():
        logger.error(f"Source path is not a directory: {source}")
        return False

    if not destination.exists():
        try:
            destination.mkdir(parents=True, exist_ok=True)
            logger.info(f"Created destination directory: {destination}")
        except PermissionError:
            logger.error(f"Permission denied creating destination directory: {destination}")
            return False
        except Exception as e:
            logger.error(f"Error creating destination directory: {e}")
            return False

    if not destination.is_dir():
        logger.error(f"Destination path is not a directory: {destination}")
        return False

    # Test write permissions
    try:
        test_file = destination / ".write_test"
        test_file.touch()
        test_file.unlink()
    except PermissionError:
        logger.error(f"No write permission in destination directory: {destination}")
        return False
    except Exception as e:
        logger.error(f"Cannot write to destination directory: {e}")
        return False

    return True


def run_archiver(source: Path, destination: Path, args) -> None:
    """Run the archiver for a single source directory."""
    try:
        archiver = Archiver(
            source, destination,
            skip_raw=args.skip_raw,
            overwrite=args.overwrite,
            ignore_srt=args.ignore_srt,
            device_tag=args.device_tag,
            recent_days=args.recent,
        )
        archiver.run()
    except Exception as e:
        logger.error(f"Error processing {source}: {e}")


def prompt_for_confirmation(detected_sources) -> bool:
    """Display detected media sources and ask user to confirm processing."""
    from source_scanner import MEDIA_EXTENSIONS

    print("\nDetected media sources:")
    print("-" * 50)

    for src in detected_sources:
        print(f"  [{src.device_hint}] {src.source_dir} ({src.file_count} files)")

    print(f"\nTotal: {len(detected_sources)} source directories")
    print()

    try:
        response = input("Process these sources? [y/N] ").strip().lower()
        return response in ('y', 'yes')
    except (EOFError, KeyboardInterrupt):
        print()
        return False


def main():
    config = load_config()

    parser = argparse.ArgumentParser(
        description='Archive and rename media files to standardized format (YYYYMMDD-HHMMSS.sss)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py --source ./media --destination ./archive
  python main.py --source /Volumes/SDCard --destination ~/Videos/Archive
        """
    )

    parser.add_argument(
        '--source',
        type=Path,
        default=None,
        help='Source directory containing media files to archive'
    )
    parser.add_argument(
        '--destination',
        type=Path,
        default=None,
        help='Destination directory where renamed files will be copied'
    )
    parser.add_argument(
        '--skip-raw',
        action='store_true',
        help='Skip raw image files (.raw, .dng, .cr2, .nef, .arw, .gpr)'
    )
    parser.add_argument(
        '--overwrite',
        action='store_true',
        help='Overwrite destination files if content differs (use with caution)'
    )
    parser.add_argument(
        '--ignore-srt',
        action='store_true',
        help='Skip SRT subtitle/telemetry files'
    )
    parser.add_argument(
        '--device-tag',
        type=str,
        default=None,
        help='Freeform tag appended to filenames to identify the source device (e.g., gopro-a, drone-mavic3)'
    )
    parser.add_argument(
        '--recent',
        type=int,
        nargs='?',
        const=1,
        default=1,
        metavar='N',
        help='Only archive files modified within the last N days (default: 1). Use --recent 0 to process all files.'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable debug logging to see timing information and detailed diagnostics'
    )
    parser.add_argument(
        '-y', '--yes',
        action='store_true',
        help='Skip confirmation prompt when multiple source directories are detected'
    )

    # Apply config values as argparse defaults (CLI always overrides)
    config_defaults = {}
    for config_key in ('source', 'destination', 'skip_raw', 'overwrite',
                        'ignore_srt', 'device_tag', 'recent', 'verbose', 'yes'):
        if config_key in config:
            value = config[config_key]
            if config_key in ('source', 'destination') and isinstance(value, str):
                value = Path(value).expanduser()
            config_defaults[config_key] = value
    parser.set_defaults(**config_defaults)

    args = parser.parse_args()

    # Configure logging based on verbose flag
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s'
    )

    # Validate required arguments
    if args.source is None:
        parser.error("--source is required (via CLI or config.yml)")
    if args.destination is None:
        parser.error("--destination is required (via CLI or config.yml)")

    source = Path(args.source).expanduser()
    destination = Path(args.destination).expanduser()

    if not source.exists():
        logger.error(f"Source directory does not exist: {source}")
        sys.exit(1)

    # Scan source for media directories
    from source_scanner import SourceScanner
    scanner = SourceScanner()
    detected = scanner.scan(source)

    if not detected:
        logger.error(f"No media files found in {source} or its subdirectories")
        sys.exit(1)

    # Single direct source (media files in source root) - backward compatible, no prompt
    if len(detected) == 1 and detected[0].source_dir == source:
        if not validate_paths(source, destination):
            sys.exit(1)
        run_archiver(source, destination, args)
    else:
        # Multiple subdirectories found - confirm with user (unless --yes)
        if not args.yes and not prompt_for_confirmation(detected):
            logger.info("Cancelled by user.")
            sys.exit(0)
        elif args.yes:
            for src in detected:
                logger.info(f"  [{src.device_hint}] {src.source_dir} ({src.file_count} files)")

        total_success = 0
        for idx, src in enumerate(detected, 1):
            logger.info(f"\n--- [{idx}/{len(detected)}] Processing: {src.source_dir} ({src.device_hint}) ---")
            if not validate_paths(src.source_dir, destination):
                logger.error(f"Skipping {src.source_dir}: path validation failed")
                continue
            run_archiver(src.source_dir, destination, args)
            total_success += 1

        logger.info(f"\nCompleted: processed {total_success}/{len(detected)} source directories")


if __name__ == '__main__':
    main()
