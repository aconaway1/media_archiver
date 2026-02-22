#!/usr/bin/env python3
"""
Media Archiver CLI - Archive and rename media files to standardized format.
"""
import argparse
import sys
import logging
from pathlib import Path
from archiver import Archiver

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s: %(message)s'
)
logger = logging.getLogger(__name__)


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


def main():
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
        required=True,
        help='Source directory containing media files to archive'
    )
    parser.add_argument(
        '--destination',
        type=Path,
        required=True,
        help='Destination directory where renamed files will be copied'
    )
    parser.add_argument(
        '--skip-raw',
        action='store_true',
        help='Skip raw image files (.raw, .dng, .cr2, .nef, .arw, .gpr)'
    )

    args = parser.parse_args()

    # Validate paths
    if not validate_paths(args.source, args.destination):
        sys.exit(1)

    # Run archiver
    try:
        archiver = Archiver(args.source, args.destination, skip_raw=args.skip_raw)
        archiver.run()
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
