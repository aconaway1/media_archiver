"""
Core archiving logic for renaming and copying media files.
"""
import logging
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
from metadata import MetadataExtractor

logger = logging.getLogger(__name__)


class FileNamer:
    """Handles destination filename generation with collision detection."""

    def __init__(self, destination_dir: Path):
        self.destination_dir = destination_dir

    def get_destination_filename(self, dt: datetime, original_extension: str) -> Path:
        """
        Generate a destination filename with collision handling.

        Format: YYYYMMDD-HHMMSS.sss.ext
        On collision: YYYYMMDD-HHMMSS.ss1.ext, YYYYMMDD-HHMMSS.ss2.ext, etc.

        Args:
            dt: datetime object
            original_extension: file extension including dot (e.g., '.mp4')

        Returns:
            Path object for the destination file
        """
        # Format base filename: YYYYMMDD-HHMMSS.sss
        base_name = dt.strftime('%Y%m%d-%H%M%S') + f'.{dt.microsecond // 1000:03d}'
        base_filename = base_name + original_extension

        destination = self.destination_dir / base_filename

        # If file doesn't exist, return it
        if not destination.exists():
            return destination

        # Handle collision with incrementing suffix
        logger.warning(f"Destination file already exists: {base_filename}")
        counter = 1
        while counter < 1000:  # Safety limit
            # Format: YYYYMMDD-HHMMSS.ss1.ext becomes .ss1, .ss2, etc.
            collision_filename = f"{base_name}.ss{counter}{original_extension}"
            destination = self.destination_dir / collision_filename

            if not destination.exists():
                logger.info(f"Using collision-avoided filename: {collision_filename}")
                return destination

            counter += 1

        # Should not reach here
        raise RuntimeError(f"Could not find available filename for timestamp {base_name}")


class Archiver:
    """Main archiver that orchestrates file discovery, renaming, and copying."""

    SUPPORTED_EXTENSIONS = {'.mp4', '.mov', '.m4a', '.wav', '.aac'}

    def __init__(self, source_dir: Path, destination_dir: Path):
        self.source_dir = Path(source_dir)
        self.destination_dir = Path(destination_dir)
        self.file_namer = FileNamer(self.destination_dir)
        self.metadata_extractor = MetadataExtractor()

    def run(self):
        """Run the archiving process."""
        logger.info(f"Starting archiver: {self.source_dir} -> {self.destination_dir}")

        media_files = self._discover_media_files()

        if not media_files:
            logger.info("No media files found in source directory")
            return

        logger.info(f"Found {len(media_files)} media file(s) to process")

        processed = 0
        skipped = 0

        for source_file in sorted(media_files):
            try:
                if self._process_file(source_file):
                    processed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error processing {source_file.name}: {e}")
                skipped += 1

        logger.info(f"Processing complete: {processed} copied, {skipped} skipped/failed")

    def _discover_media_files(self) -> list[Path]:
        """Discover all supported media files in source directory."""
        media_files = []

        try:
            for file_path in self.source_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    media_files.append(file_path)
        except PermissionError:
            logger.error(f"Permission denied reading source directory: {self.source_dir}")

        return media_files

    def _process_file(self, source_file: Path) -> bool:
        """
        Process a single media file.

        Returns:
            True if file was copied, False if skipped
        """
        # Extract datetime from file
        dt = self.metadata_extractor.get_datetime(source_file, source_file.suffix)

        if dt is None:
            logger.error(f"Could not extract timestamp from {source_file.name}, skipping")
            return False

        # Generate destination filename
        destination_file = self.file_namer.get_destination_filename(dt, source_file.suffix)

        # Check if destination already exists
        if destination_file.exists():
            logger.info(f"Skipping {source_file.name}: destination already exists ({destination_file.name})")
            return False

        # Copy file
        try:
            shutil.copy2(source_file, destination_file)
            logger.info(f"Copied: {source_file.name} -> {destination_file.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to copy {source_file.name}: {e}")
            return False
