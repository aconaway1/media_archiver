"""
Metadata extraction for various media file types.
"""
import logging
import os
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    from mutagen.file import File as MutagenFile
    from mutagen.mp4 import MP4
except ImportError:
    MutagenFile = None
    MP4 = None

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from hachoir.parser import createParser
    from hachoir.metadata import extractMetadata
except ImportError:
    createParser = None
    extractMetadata = None

try:
    from PIL import Image
    from PIL.ExifTags import TAGS
except ImportError:
    Image = None
    TAGS = None

logger = logging.getLogger(__name__)


class MetadataExtractor:
    """Extract timestamps from media files."""

    # Supported file extensions
    AUDIO_EXTENSIONS = {'.m4a', '.wav', '.aac', '.mp3'}
    VIDEO_EXTENSIONS = {'.mp4', '.mov'}
    IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png'}
    RAW_IMAGE_EXTENSIONS = {'.raw', '.dng', '.cr2', '.nef', '.arw', '.gpr'}
    SRT_EXTENSIONS = {'.srt'}

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
        elif ext_lower in MetadataExtractor.IMAGE_EXTENSIONS or ext_lower in MetadataExtractor.RAW_IMAGE_EXTENSIONS:
            dt = MetadataExtractor._extract_image_datetime(file_path)
            if dt:
                logger.debug(f"Extracted datetime from image metadata: {file_path}")
                return dt

        # Fallback to file modification time
        logger.debug(f"Using file modification time as fallback: {file_path}")
        return MetadataExtractor._get_file_datetime(file_path)

    @staticmethod
    def get_device_type(file_path: Path, extension: str) -> str:
        """
        Detect device type from filename and/or metadata.

        Returns one of: 'video', 'drone', 'audio', 'image', 'srt', or 'unknown'

        Args:
            file_path: Path to the media file
            extension: File extension (e.g., '.mp4')

        Returns:
            Device type string
        """
        filename = file_path.name.upper()
        ext_lower = extension.lower()

        # Check for SRT files first
        if ext_lower in MetadataExtractor.SRT_EXTENSIONS:
            return 'srt'

        # Check filename patterns
        if filename.startswith('GOPR') or filename.startswith('GP'):
            return 'video'

        if filename.startswith('DJI'):
            # Could be drone video or image
            if ext_lower in MetadataExtractor.IMAGE_EXTENSIONS or ext_lower in MetadataExtractor.RAW_IMAGE_EXTENSIONS:
                return 'image'
            return 'drone'

        # Image files
        if ext_lower in MetadataExtractor.IMAGE_EXTENSIONS or ext_lower in MetadataExtractor.RAW_IMAGE_EXTENSIONS:
            return 'image'

        # Audio files default to 'audio'
        if ext_lower in MetadataExtractor.AUDIO_EXTENSIONS:
            return 'audio'

        # Try to extract device type from video metadata
        if ext_lower in MetadataExtractor.VIDEO_EXTENSIONS:
            device_type = MetadataExtractor._detect_video_device(file_path)
            if device_type:
                return device_type

        # Default to 'video' for video files without device detection
        if ext_lower in MetadataExtractor.VIDEO_EXTENSIONS:
            return 'video'

        return 'unknown'

    @staticmethod
    def _detect_video_device(file_path: Path) -> Optional[str]:
        """Try to detect video device type from metadata."""
        if createParser and extractMetadata:
            try:
                parser = createParser(str(file_path))
                if parser:
                    metadata = extractMetadata(parser)
                    if metadata:
                        for key, value in metadata.exportPlaintext():
                            value_str = str(value).upper()
                            if 'DJI' in value_str:
                                return 'drone'
                            if 'GOPRO' in value_str or 'HERO' in value_str:
                                return 'video'
            except Exception:
                pass

        return None

    @staticmethod
    def _extract_video_datetime(file_path: Path) -> Optional[datetime]:
        """Extract creation datetime from video file using hachoir or cv2."""
        # Try hachoir first (pure Python)
        if createParser and extractMetadata:
            try:
                parser = createParser(str(file_path))
                if parser:
                    metadata = extractMetadata(parser)
                    if metadata:
                        # Look for creation time in metadata
                        if hasattr(metadata, 'getItems'):
                            for key, value in metadata.exportPlaintext():
                                if 'creation' in key.lower() or 'date' in key.lower():
                                    try:
                                        # Try to parse common date formats
                                        for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d']:
                                            try:
                                                return datetime.strptime(str(value), fmt)
                                            except ValueError:
                                                continue
                                    except Exception:
                                        continue
            except Exception as e:
                logger.debug(f"Hachoir failed to extract metadata from {file_path}: {e}")

        # Try OpenCV as fallback
        if cv2:
            try:
                cap = cv2.VideoCapture(str(file_path))
                if cap.isOpened():
                    # Try to get creation time property
                    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
                    fps = cap.get(cv2.CAP_PROP_FPS)
                    cap.release()

                    # We can't get the actual timestamp from cv2, but we can log that we found the video
                    logger.debug(f"Found video with {frame_count} frames at {fps} fps: {file_path}")
            except Exception as e:
                logger.debug(f"OpenCV failed to read video {file_path}: {e}")

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
    def _extract_image_datetime(file_path: Path) -> Optional[datetime]:
        """Extract creation datetime from image file using EXIF metadata."""
        if Image is None:
            logger.debug("Pillow not installed, cannot extract image EXIF metadata")
            return None

        try:
            image = Image.open(str(file_path))
            exif_data = image._getexif()

            if exif_data:
                # Look for DateTime tags (EXIF tag 306 is DateTime)
                for tag_id, value in exif_data.items():
                    tag_name = TAGS.get(tag_id, tag_id)
                    if tag_name in ['DateTime', 'DateTimeOriginal', 'DateTimeDigitized']:
                        try:
                            # EXIF dates are in format: "YYYY:MM:DD HH:MM:SS"
                            return datetime.strptime(str(value), '%Y:%m:%d %H:%M:%S')
                        except (ValueError, TypeError):
                            continue

        except Exception as e:
            logger.warning(f"Error extracting image metadata from {file_path}: {e}")

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
