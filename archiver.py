"""
Core archiving logic for renaming and copying media files.
"""
import hashlib
import logging
import shutil
import time
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta
from metadata import MetadataExtractor

logger = logging.getLogger(__name__)


class FileNamer:
    """Handles destination filename generation."""

    def __init__(self, destination_dir: Path):
        self.destination_dir = destination_dir

    def get_destination_filename(self, dt: datetime, original_extension: str, device_type: str, device_tag: Optional[str] = None) -> Path:
        """
        Generate a destination filename.

        Format: <DESTINATION>/YYYY/MM/DD/YYYYMMDD-HHMMSS-<device_type>[-<device_tag>].ext

        Args:
            dt: datetime object
            original_extension: file extension including dot (e.g., '.mp4')
            device_type: device type string (e.g., 'camera', 'drone', 'audio')
            device_tag: optional freeform tag to identify the source device

        Returns:
            Path object for the destination file (base name without collision handling)
        """
        # Create date-based subdirectory structure
        year = dt.strftime('%Y')
        month = dt.strftime('%m')
        day = dt.strftime('%d')
        date_dir = self.destination_dir / year / month / day

        # Create directory if it doesn't exist
        try:
            date_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.error(f"Failed to create directory {date_dir}: {e}")
            raise

        # Format base filename: YYYYMMDD-HHMMSS-<device_type>[-<device_tag>]
        base_name = dt.strftime('%Y%m%d-%H%M%S') + f'-{device_type}'
        if device_tag:
            base_name += f'-{device_tag}'
        base_filename = base_name + original_extension

        return date_dir / base_filename

    def get_next_available_filename(self, base_path: Path) -> Path:
        """
        Find the next available filename by adding collision suffix if needed.

        Args:
            base_path: The base destination path

        Returns:
            Path object for an available filename
        """
        if not base_path.exists():
            return base_path

        # Handle collision with incrementing suffix
        date_dir = base_path.parent
        base_name = base_path.stem
        extension = base_path.suffix

        logger.warning(f"Destination file already exists: {base_path.name}")
        counter = 1
        while counter < 1000:  # Safety limit
            collision_filename = f"{base_name}.{counter}{extension}"
            collision_path = date_dir / collision_filename

            if not collision_path.exists():
                logger.info(f"Using collision-avoided filename: {collision_filename}")
                return collision_path

            counter += 1

        # Should not reach here
        raise RuntimeError(f"Could not find available filename for {base_path.name}")


class Archiver:
    """Main archiver that orchestrates file discovery, renaming, and copying."""

    SUPPORTED_EXTENSIONS = {'.mp4', '.mov', '.m4a', '.wav', '.aac', '.jpg', '.jpeg', '.png', '.raw', '.dng', '.cr2', '.nef', '.arw', '.gpr', '.srt'}

    def __init__(self, source_dir: Path, destination_dir: Path, skip_raw: bool = False, overwrite: bool = False, ignore_srt: bool = False, device_tag: Optional[str] = None, recent_days: Optional[int] = None):
        self.source_dir = Path(source_dir)
        self.destination_dir = Path(destination_dir)
        self.skip_raw = skip_raw
        self.overwrite = overwrite
        self.ignore_srt = ignore_srt
        self.device_tag = device_tag
        self.recent_days = recent_days
        self.file_namer = FileNamer(self.destination_dir)
        self.metadata_extractor = MetadataExtractor()

    def run(self):
        """Run the archiving process."""
        logger.info(f"Starting archiver: {self.source_dir} -> {self.destination_dir}")

        start_time = time.time()
        media_files = self._discover_media_files()
        discover_time = time.time() - start_time
        logger.debug(f"File discovery took {discover_time:.2f}s")

        if not media_files:
            logger.info("No media files found in source directory")
            return

        logger.info(f"Found {len(media_files)} media file(s) to process")

        processed = 0
        skipped = 0

        for idx, source_file in enumerate(sorted(media_files), 1):
            try:
                logger.debug(f"[{idx}/{len(media_files)}] Processing: {source_file.name}")
                if self._process_file(source_file):
                    processed += 1
                else:
                    skipped += 1
            except Exception as e:
                logger.error(f"Error processing {source_file.name}: {e}")
                skipped += 1

        logger.info(f"Processing complete: {processed} copied, {skipped} skipped/failed")

    @staticmethod
    def _calculate_sha256(file_path: Path) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                sha256_hash.update(chunk)
        return sha256_hash.hexdigest()

    def _discover_media_files(self) -> list[Path]:
        """Discover all supported media files in source directory."""
        media_files = []
        raw_extensions = {'.raw', '.dng', '.cr2', '.nef', '.arw', '.gpr'}
        skipped_old = 0

        # Compute age cutoff if --recent was specified (0 means all files)
        if self.recent_days is not None and self.recent_days > 0:
            # Use calendar-day cutoff: midnight N-1 days ago
            # --recent 1 = since midnight today, --recent 2 = since midnight yesterday
            today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            cutoff_dt = today - timedelta(days=self.recent_days - 1)
            cutoff_time = cutoff_dt.timestamp()
        else:
            cutoff_time = None

        try:
            for file_path in self.source_dir.iterdir():
                if file_path.is_file() and file_path.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                    # Skip macOS metadata files (e.g., ._filename)
                    if file_path.name.startswith('._'):
                        logger.debug(f"Skipping macOS metadata file: {file_path.name}")
                        continue
                    # Skip raw files if requested
                    if self.skip_raw and file_path.suffix.lower() in raw_extensions:
                        logger.debug(f"Skipping raw file (--skip-raw enabled): {file_path.name}")
                        continue
                    # Skip SRT files if requested
                    if self.ignore_srt and file_path.suffix.lower() == '.srt':
                        logger.debug(f"Skipping SRT file (--ignore-srt enabled): {file_path.name}")
                        continue
                    # Skip files older than --recent N days
                    if cutoff_time is not None:
                        try:
                            if file_path.stat().st_mtime < cutoff_time:
                                logger.debug(f"Skipping old file (--recent {self.recent_days}): {file_path.name}")
                                skipped_old += 1
                                continue
                        except OSError:
                            pass
                    media_files.append(file_path)
        except PermissionError:
            logger.error(f"Permission denied reading source directory: {self.source_dir}")

        if skipped_old > 0:
            logger.info(f"Skipped {skipped_old} file(s) older than {self.recent_days} day(s)")

        return media_files

    def _process_file(self, source_file: Path) -> bool:
        """
        Process a single media file.

        Returns:
            True if file was copied, False if skipped
        """
        # Extract datetime from file
        meta_start = time.time()
        dt = self.metadata_extractor.get_datetime(source_file, source_file.suffix)
        meta_time = time.time() - meta_start
        logger.debug(f"Metadata extraction took {meta_time:.2f}s: {source_file.name}")

        if dt is None:
            logger.error(f"Could not extract timestamp from {source_file.name}, skipping")
            return False

        # Detect device type
        device_type = self.metadata_extractor.get_device_type(source_file, source_file.suffix)

        # Calculate source checksum once upfront
        # This is used for both duplicate detection and copy verification
        # Avoids reading the source file twice
        hash_start = time.time()
        source_hash = self._calculate_sha256(source_file)
        hash_time = time.time() - hash_start
        logger.debug(f"Source checksum calculation took {hash_time:.2f}s: {source_file.name}")

        # Generate base destination filename (without collision handling)
        base_destination_file = self.file_namer.get_destination_filename(dt, source_file.suffix, device_type, self.device_tag)

        # Check if destination already exists
        if base_destination_file.exists():
            # Compare checksums for duplicate detection
            verify_start = time.time()
            dest_hash = self._calculate_sha256(base_destination_file)
            verify_time = time.time() - verify_start
            logger.debug(f"Destination checksum calculation took {verify_time:.2f}s: {source_file.name}")

            if source_hash == dest_hash:
                logger.info(f"Skipping {source_file.name}: identical file already exists ({base_destination_file.name})")
                return False
            else:
                # Files have different content
                if self.overwrite:
                    logger.warning(f"Destination file exists with different content: {source_file.name} - overwriting")
                    try:
                        base_destination_file.unlink()
                    except Exception as e:
                        logger.error(f"Failed to delete existing file {base_destination_file.name}: {e}")
                        return False
                    # Fall through to copy with the base destination name
                    destination_file = base_destination_file
                else:
                    # Different content without --overwrite: use collision handling
                    destination_file = self.file_namer.get_next_available_filename(base_destination_file)
        else:
            # File doesn't exist yet, use the base destination name
            destination_file = base_destination_file

        # Copy file with retry logic (up to 3 attempts)
        max_retries = 3
        for attempt in range(1, max_retries + 1):
            try:
                copy_start = time.time()
                shutil.copy2(source_file, destination_file)
                copy_time = time.time() - copy_start

                # Verify copy integrity by comparing with cached source hash
                # Only read destination hash, not source again (already calculated above)
                verify_start = time.time()
                dest_hash = self._calculate_sha256(destination_file)
                verify_time = time.time() - verify_start
                logger.debug(f"Copy took {copy_time:.2f}s, verification took {verify_time:.2f}s: {source_file.name}")

                if source_hash != dest_hash:
                    logger.warning(f"Checksum mismatch for {source_file.name} (attempt {attempt}/{max_retries}): retrying...")
                    # Clean up bad copy before retry
                    try:
                        destination_file.unlink()
                    except Exception:
                        pass
                    if attempt < max_retries:
                        time.sleep(1)  # Wait 1 second before retry
                        continue
                    else:
                        logger.error(f"Checksum mismatch for {source_file.name}: copy failed after {max_retries} attempts, deleting corrupted file")
                        try:
                            destination_file.unlink()
                        except Exception:
                            pass
                        return False

                logger.info(f"Copied: {source_file.name} -> {destination_file.name}")
                return True

            except Exception as e:
                logger.warning(f"Failed to copy {source_file.name} (attempt {attempt}/{max_retries}): {e}")
                # Clean up any partial copy before retry
                try:
                    if destination_file.exists():
                        destination_file.unlink()
                except Exception:
                    pass
                if attempt < max_retries:
                    time.sleep(1)  # Wait 1 second before retry
                    continue
                else:
                    logger.error(f"Failed to copy {source_file.name}: all {max_retries} attempts failed")
                    return False

        return False
