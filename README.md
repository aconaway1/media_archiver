# Media Archiver

A Python CLI tool for archiving and standardizing the naming of media files from various devices (GoPro, DJI drones, Tascam recorders, etc.).

## Features

- **Standardized Naming**: Renames media files to `YYYYMMDD-HHMMSS-<device_type>.ext` format with device identification
- **Smart Timestamp Extraction**: Extracts creation timestamps from file metadata with intelligent fallback to file modification time
- **Collision Handling**: Automatically handles naming conflicts with incrementing suffixes
- **File Type Support**: MP4, MOV, M4A, WAV, and AAC files
- **Safe Operations**: Copies files (preserves originals) rather than moving them
- **Smart Skipping**: Skips files that already exist in the destination with informative messaging

## Installation

1. Clone or navigate to the media_archiver project directory
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

No external tools needed! The archiver uses pure Python libraries for metadata extraction.

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
- **Video files (.mp4, .mov)**: Reads metadata using hachoir (pure Python) or OpenCV
- **Audio files (.m4a, .wav, .aac)**: Reads date/year tags using mutagen library
- **Fallback**: Uses the file's modification timestamp

### 2b. Device Type Detection
The tool identifies the source device using multiple strategies:
- **Filename patterns**: Detects GoPro files (GOPR*, GP*) and DJI files (DJI*)
- **Metadata tags**: Searches video metadata for manufacturer info (DJI, GoPro, HERO)
- **File type**: Audio-only files (M4A, WAV, AAC) default to 'audio'
- **Default**: Unidentified video files default to 'camera'

Device types include: `camera`, `drone`, `audio`, or `unknown`

### 3. Directory Organization
Files are organized by date in the destination directory:
```
<DESTINATION>/
├── 2024/
│   ├── 02/
│   │   ├── 15/
│   │   │   ├── 20240215-143045-camera.mp4
│   │   │   └── 20240215-143045-drone.mov
│   │   └── 16/
│   │       └── 20240216-091530-audio.wav
```

### 4. Filename Generation
Filenames are formatted as `YYYYMMDD-HHMMSS-<device_type>.<extension>`:
- `YYYYMMDD`: Date (e.g., 20240215)
- `HHMMSS`: Time (e.g., 143045)
- `<device_type>`: Device type (e.g., camera, drone, audio)
- Extension: Original file extension (e.g., .mp4)

Example outputs:
- `20240215-143045-camera.mp4` (GoPro video)
- `20240215-143045-drone.mov` (DJI drone footage)
- `20240216-091530-audio.wav` (Tascam audio recording)

### 5. Collision Handling
If a file with the same name already exists in the same date folder:
- First collision: Changes to `YYYYMMDD-HHMMSS-<device_type>.1.ext`
- Second collision: Changes to `YYYYMMDD-HHMMSS-<device_type>.2.ext`
- And so on...

### 6. File Copying
Files are copied to the destination directory while preserving their metadata.

## Output

The tool provides informative logging:

```
INFO: Starting archiver: /source -> /destination
INFO: Found 42 media file(s) to process
INFO: Copied: GOPR1234.MP4 -> 20240222-143025-camera.mp4
INFO: Copied: DJI_0001.MOV -> 20240222-143126-drone.mov
INFO: Copied: audio.wav -> 20240222-143200-audio.wav
INFO: Processing complete: 42 copied, 0 skipped/failed
```

## Requirements

- Python 3.7+
- mutagen library for audio metadata reading
- hachoir library for video metadata parsing (pure Python)
- opencv-python for video format validation
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
4. Try with a single test file first to isolate the issue

## License

MIT License
