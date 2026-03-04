"""
Scan a source path to find media directories for archiving.
"""
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

MEDIA_EXTENSIONS = {
    '.mp4', '.mov', '.m4a', '.wav', '.aac', '.jpg', '.jpeg',
    '.png', '.raw', '.dng', '.cr2', '.nef', '.arw', '.gpr', '.srt'
}

AUDIO_EXTENSIONS = {'.m4a', '.wav', '.aac', '.mp3'}


class DetectedSource:
    """A detected media source directory."""

    def __init__(self, source_dir: Path, device_hint: str, file_count: int):
        self.source_dir = source_dir
        self.device_hint = device_hint
        self.file_count = file_count

    def __repr__(self):
        return f"DetectedSource(dir={self.source_dir}, hint={self.device_hint}, files={self.file_count})"


class SourceScanner:
    """Scans a given path to find directories containing media files."""

    def scan(self, source_path: Path) -> list[DetectedSource]:
        """
        Scan source_path for media content.

        If source_path directly contains media files, returns it as a single source.
        Otherwise, scans for known subdirectory structures (DCIM, MUSIC, etc.).

        Returns:
            List of DetectedSource objects, one per directory containing media files.
        """
        if not source_path.exists() or not source_path.is_dir():
            return []

        # Check if source directly contains media files (backward compatible)
        direct_count = self._count_media_files(source_path)
        if direct_count > 0:
            hint = self._detect_device_hint(source_path)
            return [DetectedSource(source_path, hint, direct_count)]

        # Scan for known subdirectory structures
        detected = []

        # Check for DCIM directory (cameras, drones, GoPros)
        dcim = source_path / 'DCIM'
        if dcim.exists() and dcim.is_dir():
            detected.extend(self._scan_dcim(dcim))

        # Check for Tascam-style audio directories
        for folder_name in ('MUSIC', 'SOUND', 'RECORD'):
            folder = source_path / folder_name
            if folder.exists() and folder.is_dir():
                count = self._count_media_files(folder)
                if count > 0:
                    detected.append(DetectedSource(folder, 'tascam', count))

        return detected

    def _scan_dcim(self, dcim: Path) -> list[DetectedSource]:
        """Scan a DCIM directory for media subdirectories."""
        sources = []

        # Check for media files directly in DCIM/
        direct_count = self._count_media_files(dcim)
        if direct_count > 0:
            hint = self._detect_device_hint(dcim)
            sources.append(DetectedSource(dcim, hint, direct_count))

        # Scan subdirectories (100GOPRO, 101GOPRO, DJI_001, 100MEDIA, etc.)
        try:
            for subdir in sorted(dcim.iterdir()):
                if not subdir.is_dir() or subdir.name.startswith('.'):
                    continue
                count = self._count_media_files(subdir)
                if count > 0:
                    hint = self._detect_device_hint(subdir)
                    sources.append(DetectedSource(subdir, hint, count))
        except PermissionError:
            logger.debug(f"Permission denied reading {dcim}")

        return sources

    def _count_media_files(self, directory: Path) -> int:
        """Count media files in a directory (non-recursive)."""
        count = 0
        try:
            for f in directory.iterdir():
                if f.is_file() and f.suffix.lower() in MEDIA_EXTENSIONS and not f.name.startswith('._'):
                    count += 1
        except PermissionError:
            pass
        return count

    def _detect_device_hint(self, directory: Path) -> str:
        """Infer device type from directory name and file patterns."""
        dir_name = directory.name.upper()

        if 'GOPRO' in dir_name:
            return 'gopro'
        if 'DJI' in dir_name:
            return 'dji'

        # Check file name patterns
        try:
            for f in directory.iterdir():
                if not f.is_file():
                    continue
                fname = f.name.upper()
                if fname.startswith('GOPR') or fname.startswith('GP'):
                    return 'gopro'
                if fname.startswith('DJI'):
                    return 'dji'
                if f.suffix.lower() in AUDIO_EXTENSIONS:
                    return 'tascam'
        except PermissionError:
            pass

        return 'camera'
