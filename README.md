# Media Archiver

A Python CLI tool for archiving and standardizing the naming of media files from various devices (GoPro, DJI drones, Tascam recorders, etc.).

## Features

- **Standardized Naming**: Renames media files to `YYYYMMDD-HHMMSS.sss.ext` format for consistent organization
- **Smart Timestamp Extraction**: Extracts creation timestamps from file metadata with intelligent fallback to file modification time
- **Collision Handling**: Automatically handles naming conflicts with incrementing suffixes
- **File Type Support**: MP4, MOV, M4A, WAV, and AAC files
- **Safe Operations**: Copies files (preserves originals) rather than moving them
- **Smart Skipping**: Skips files that already exist in the destination with informative messaging

## Installation

1. Clone or navigate to the media_archiver project directory
2. Install dependencies:

```bash
pip install -r requirements.txt
```

Make sure you have `ffprobe` installed (part of ffmpeg):

```bash
# macOS
brew install ffmpeg

# Ubuntu/Debian
sudo apt-get install ffmpeg

# Windows
# Download from https://ffmpeg.org/download.html
```

## Usage

```bash
python main.py --source <source_directory> --destination <destination_directory>
```

### Examples

Archive files from an SD card:

```bash
python main.py --source /Volumes/GoPro --destination ~/Videos/Archive
```

Archive files from a local directory:

```bash
python main.py --source ./raw_media --destination ./archived_media
```

## How It Works

### 1. File Discovery
The tool scans the source directory for supported media files (.mp4, .mov, .m4a, .wav, .aac).

### 2. Timestamp Extraction
For each file, the tool attempts to extract the creation timestamp in this order:
- **Video files (.mp4, .mov)**: Reads `creation_time` metadata tag using ffprobe
- **Audio files (.m4a, .wav, .aac)**: Reads date/year tags using mutagen library
- **Fallback**: Uses the file's modification timestamp

### 3. Filename Generation
Timestamps are formatted as `YYYYMMDD-HHMMSS.sss.<extension>`:
- `YYYYMMDD`: Date (e.g., 20240222)
- `HHMMSS`: Time (e.g., 153045)
- `.sss`: Milliseconds (e.g., 123)
- Extension: Original file extension (e.g., .mp4)

Example output: `20240222-153045.123.mp4`

### 4. Collision Handling
If a file with the same name already exists in the destination:
- First collision: Changes to `YYYYMMDD-HHMMSS.ss1.ext`
- Second collision: Changes to `YYYYMMDD-HHMMSS.ss2.ext`
- And so on...

### 5. File Copying
Files are copied to the destination directory while preserving their metadata.

## Output

The tool provides informative logging:

```
INFO: Starting archiver: /source -> /destination
INFO: Found 42 media file(s) to process
INFO: Copied: GOPR1234.MP4 -> 20240222-143025.456.mp4
WARNING: File skipped (already exists): GOPR1235.MP4 -> 20240222-143126.789.mp4
INFO: Processing complete: 40 copied, 2 skipped/failed
```

## Requirements

- Python 3.7+
- ffmpeg/ffprobe for video metadata extraction
- mutagen library for audio metadata reading
- Read and write permissions to source and destination directories

## Error Handling

The tool gracefully handles:
- Missing or invalid source/destination directories
- Corrupted media files (falls back to file timestamps)
- Permission errors
- Files that can't be read or written
- Invalid metadata formats

Processing continues even if individual files fail, with detailed error logging.

## Supported Formats

| Device | Format | Extension |
|--------|--------|-----------|
| GoPro | MP4 | .mp4 |
| GoPro | MOV | .mov |
| DJI Drones | MP4 | .mp4 |
| Tascam Recorders | WAV | .wav |
| Tascam Recorders | MP4 | .m4a |
| General Audio | AAC | .aac |
| General Audio | MP3 | .mp3* |

*Note: MP3 support may require additional setup

## Troubleshooting

### "ffprobe not found"
Install ffmpeg:
- macOS: `brew install ffmpeg`
- Linux: `sudo apt-get install ffmpeg`

### Cannot extract timestamp
The tool will use the file's modification time as a fallback. Check file timestamps:
```bash
# macOS/Linux
ls -lh <file>

# Or use the tool's verbose output
```

### Permission denied errors
Ensure you have read permissions on the source directory and write permissions on the destination directory.

### Files not being copied
Check that:
1. Files have supported extensions (.mp4, .mov, .m4a, .wav, .aac)
2. Destination directory exists and is writable
3. Source directory contains readable files

## License

MIT License
