"""
Metadata extraction for various media file types.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
import subprocess

try:
    from mutagen.file import File as MutagenFile
    from mutagen.mp4 import MP4
except ImportError:
    MutagenFile = None
    MP4 = None

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract timestamps from media files."""

    # Supported file extensions
    AUDIO_EXTENSIONS = {'.m4a', '.wav', '.aac', '.mp3'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov'}

    @staticmethod
    def get_datetime(file_path: Path, extension: str) -> Optional[datetime]:
        """
        Get creation datetime from a media file.

        Attempts to extract from metadata first, falls back to file modification time.

        Args:
            file_path: Path to the media file
            extension: File extension (e.g., '.mp4')

        Returns:
            datetime object or None if extraction fails
        """
        ext_lower = extension.lower()

        # Try metadata extraction based on file type
        if ext_lower in MetadataExtractor.VIDEO_EXTENSIONS:
            dt = MetadataExtractor._extract_video_datetime(file_path)
            if dt:
                logger.debug(f"Extracted datetime from video metadata: {file_path}")
                return dt
        elif ext_lower in MetadataExtractor.AUDIO_EXTENSIONS:
            dt = MetadataExtractor._extract_audio_datetime(file_path)
            if dt:
                logger.debug(f"Extracted datetime from audio metadata: {file_path}")
                return dt

        # Fallback to file modification time
        logger.debug(f"Using file modification time as fallback: {file_path}")
        return MetadataExtractor._get_file_datetime(file_path)

    @staticmethod
    def _extract_video_datetime(file_path: Path) -> Optional[datetime]:
        """Extract creation datetime from video file using ffmpeg."""
        try:
            # Use ffmpeg to extract metadata
            result = subprocess.run(
                ['ffprobe', '-v', 'error', '-print_format', 'json',
                 '-show_entries', 'format=creation_time', str(file_path)],
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode != 0:
                logger.warning(f"ffprobe failed for {file_path}")
                return None

            import json
            try:
                data = json.loads(result.stdout)
                creation_time = data.get('format', {}).get('creation_time')
                if creation_time:
                    # Parse ISO 8601 format (e.g., "2024-02-22T15:30:45.123Z")
                    # Try with microseconds first, then without
                    for fmt in ['%Y-%m-%dT%H:%M:%S.%fZ', '%Y-%m-%dT%H:%M:%SZ']:
                        try:
                            return datetime.strptime(creation_time.replace('+00:00', 'Z'), fmt)
                        except ValueError:
                            continue
            except (json.JSONDecodeError, KeyError):
                pass

        except FileNotFoundError:
            logger.debug("ffprobe not found, cannot extract video metadata")
        except subprocess.TimeoutExpired:
            logger.warning(f"ffprobe timeout for {file_path}")
        except Exception as e:
            logger.warning(f"Error extracting video metadata from {file_path}: {e}")

        return None

    @staticmethod
    def _extract_audio_datetime(file_path: Path) -> Optional[datetime]:
        """Extract creation datetime from audio file using mutagen."""
        if MutagenFile is None:
            logger.debug("mutagen not installed, cannot extract audio metadata")
            return None

        try:
            # Try to read with specific MP4 class first (for .m4a files)
            if file_path.suffix.lower() == '.m4a' and MP4:
                try:
                    tags = MP4(str(file_path)).tags
                    if tags:
                        # Look for common date tags
                        for tag_name in ['\xa9day', 'date', 'year']:
                            if tag_name in tags:
                                date_val = tags[tag_name]
                                if date_val:
                                    date_str = str(date_val[0])
                                    # Try parsing as YYYY-MM-DD or YYYY
                                    for fmt in ['%Y-%m-%d', '%Y']:
                                        try:
                                            return datetime.strptime(date_str, fmt)
                                        except ValueError:
                                            continue
                except Exception as e:
                    logger.debug(f"Could not read MP4 tags: {e}")

            # Generic mutagen approach
            audio_file = MutagenFile(str(file_path), easy=True)
            if audio_file and audio_file.tags:
                # Look for common date tags
                for tag_name in ['date', 'year', '\xa9day']:
                    if tag_name in audio_file.tags:
                        date_val = audio_file.tags[tag_name]
                        if date_val:
                            date_str = str(date_val[0])
                            for fmt in ['%Y-%m-%d', '%Y']:
                                try:
                                    return datetime.strptime(date_str, fmt)
                                except ValueError:
                                    continue

        except Exception as e:
            logger.warning(f"Error extracting audio metadata from {file_path}: {e}")

        return None

    @staticmethod
    def _get_file_datetime(file_path: Path) -> Optional[datetime]:
        """Get file modification time as fallback."""
        try:
            mod_time = os.path.getmtime(file_path)
            return datetime.fromtimestamp(mod_time)
        except (OSError, ValueError) as e:
            logger.error(f"Error getting file modification time for {file_path}: {e}")
            return None
