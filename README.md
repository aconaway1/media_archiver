# Media Archiver

> Built with [Claude Code](https://claude.ai/claude-code)

A Python CLI tool for archiving and standardizing the naming of media files from various devices (GoPro, DJI drones, Tascam recorders, etc.).

## Features

- **Standardized Naming**: Renames media files to `YYYYMMDD-HHMMSS-<device_type>.ext` format with device identification
- **Smart Timestamp Extraction**: Extracts creation timestamps from file metadata with intelligent fallback to file modification time
- **Collision Handling**: Automatically handles naming conflicts with incrementing suffixes
- **File Type Support**: Video (MP4, MOV), Audio (M4A, WAV, AAC), Images (JPG, PNG, RAW formats), and SRT files
- **Safe Operations**: Copies files (preserves originals) rather than moving them
- **Smart Skipping**: Skips files that already exist in the destination with informative messaging
- **YAML Config File**: Set persistent defaults for destination, flags, and device tags in `config.yml`
- **Smart Source Scanning**: Point at a volume/SD card root and the tool auto-detects media directories (DCIM/100GOPRO, DCIM/DJI_001, MUSIC/, etc.)
- **Device Tagging**: Use `--device-tag` to identify source devices (e.g., `gopro-a`, `drone-mavic3`) in filenames
- **Recent File Filtering**: By default, only archives files from today. Use `--recent N` to include the last N days, or `--recent 0` for all files
- **Optional Raw Image Skipping**: Use `--skip-raw` flag to exclude raw image files if needed
- **Optional SRT Skipping**: Use `--ignore-srt` flag to exclude DJI SRT subtitle/telemetry files if needed

## Installation

1. Clone or navigate to the media_archiver project directory
2. Create a virtual environment and install dependencies:

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

No external tools needed! The archiver uses pure Python libraries for metadata extraction.

## Configuration

You can set persistent defaults in a `config.yml` file in the project directory. Copy the example to get started:

```bash
cp config.yml.example config.yml
```

Edit `config.yml` with your preferred defaults:

```yaml
# Source and destination directories
source: /Volumes/Untitled
destination: ~/Library/CloudStorage/Dropbox/Video

# File filtering
skip_raw: false
ignore_srt: false

# Device identification tag (appended to filenames)
device_tag: mavic3

# Only archive files from the last N days (0 = all files)
recent: 1

# Overwrite destination files with different content
overwrite: false

# Enable debug logging
verbose: false
```

CLI flags always override config file values. The config file is gitignored so your local paths stay private.

## Usage

```bash
python main.py --source <source_directory> --destination <destination_directory> [options]
```

If `--source` and `--destination` are set in `config.yml`, you can run with no arguments:

```bash
python main.py
```

### Options

| Flag | Description |
|------|-------------|
| `--source` | Source directory containing media files (required, via CLI or config) |
| `--destination` | Destination directory for archived files (required, via CLI or config) |
| `--recent N` | Only archive files from the last N days (default: 1, today only). Use `--recent 0` for all files |
| `--device-tag TAG` | Freeform tag appended to filenames to identify the source device |
| `--skip-raw` | Skip raw image files (.raw, .dng, .cr2, .nef, .arw, .gpr) |
| `--overwrite` | Overwrite destination files if content differs (use with caution) |
| `--ignore-srt` | Skip DJI SRT subtitle/telemetry files |
| `-y`, `--yes` | Skip confirmation prompt when multiple source directories are detected |
| `--verbose` | Enable debug logging with timing diagnostics |
| `--filename-pattern` | Custom filename pattern using tokens (see below) |
| `--directory-pattern` | Custom directory structure pattern using tokens (see below) |

### Examples

Archive today's files from an SD card (default behavior):

```bash
python main.py --source /Volumes/GoPro --destination ~/Videos/Archive
```

Archive the last 3 days of footage with a device tag:

```bash
python main.py --source /Volumes/GoPro --destination ~/Videos/Archive --recent 3 --device-tag gopro-a
```

Archive all files (override the default recent filter):

```bash
python main.py --source /Volumes/GoPro --destination ~/Videos/Archive --recent 0
```

Archive DJI files without SRT telemetry, tagged by drone:

```bash
python main.py --source /Volumes/DJI_001/DCIM --destination ~/Videos/DJI --ignore-srt --device-tag mavic3
```

Point at an SD card root and let the tool find media directories:

```bash
python main.py --source /Volumes/Untitled --destination ~/Videos/Archive
```

The tool will scan for known structures and ask for confirmation:

```
Detected media sources:
--------------------------------------------------
  [gopro] /Volumes/Untitled/DCIM/100GOPRO (42 files)
  [gopro] /Volumes/Untitled/DCIM/101GOPRO (18 files)

Total: 2 source directories

Process these sources? [y/N]
```

With config.yml set up, archive with zero arguments:

```bash
python main.py
```

Archive files and skip raw images:

```bash
python main.py --source ./raw_media --destination ./archived_media --skip-raw
```

Use a custom filename pattern:

```bash
python main.py --source /Volumes/GoPro --destination ~/Videos/Archive \
  --filename-pattern "{original}-{year}{month}{day}{-device_tag}"
```

### Custom Filename & Directory Patterns

You can customize how output files are named and organized using pattern tokens.

**Default patterns:**
```yaml
filename_pattern: "{year}{month}{day}-{hour}{minute}{second}-{device_type}{-device_tag}"
directory_pattern: "{year}/{month}/{day}"
```

**Available tokens:**

| Token | Example | Description |
|-------|---------|-------------|
| `{year}` | `2024` | 4-digit year |
| `{month}` | `02` | Zero-padded month |
| `{day}` | `15` | Zero-padded day |
| `{hour}` | `14` | Zero-padded hour (24h) |
| `{minute}` | `30` | Zero-padded minute |
| `{second}` | `45` | Zero-padded second |
| `{device_type}` | `video` | Detected device type (video, drone, audio, image, srt) |
| `{device_tag}` | `mavic3` | From `--device-tag` (empty string if unset) |
| `{-device_tag}` | `-mavic3` | Dash-prefixed tag (empty string if unset) |
| `{original}` | `GOPR0001` | Original filename without extension |

**Examples:**
```yaml
# Keep original filename with date prefix
filename_pattern: "{year}{month}{day}-{original}"

# Organize by device type instead of date
directory_pattern: "{device_type}/{year}-{month}"

# Simple date-only filenames
filename_pattern: "{year}-{month}-{day}_{hour}{minute}{second}"
```

## How It Works

### 1. Source Scanning
When given a source path, the tool first checks if media files exist directly in that directory (backward compatible). If not, it scans for known device directory structures:
- **DCIM/** subdirectories: 100GOPRO, 101GOPRO, DJI_001, 100MEDIA, etc.
- **Audio folders**: MUSIC/, SOUND/, RECORD/ (Tascam-style recorders)

Each detected subdirectory is treated as a separate source. If multiple sources are found, you'll be prompted to confirm before processing.

### 2. File Discovery
The tool scans each source directory for supported media files (.mp4, .mov, .m4a, .wav, .aac, .jpg, .jpeg, .png, .raw, .dng, .cr2, .nef, .arw, .gpr, .srt).

### 3. Timestamp Extraction
For each file, the tool attempts to extract the creation timestamp in this order:
- **Video files (.mp4, .mov)**: Reads metadata using hachoir (pure Python) or OpenCV
- **Audio files (.m4a, .wav, .aac)**: Reads date/year tags using mutagen library
- **Image files (.jpg, .jpeg, .png, RAW)**: Reads EXIF DateTime, DateTimeOriginal, or DateTimeDigitized tags
- **Fallback**: Uses the file's modification timestamp

### 3b. Device Type Detection
The tool identifies the source device using multiple strategies:
- **Filename patterns**: Detects GoPro files (GOPR*, GP*) and DJI files (DJI*)
- **Metadata tags**: Searches video metadata for manufacturer info (DJI, GoPro, HERO)
- **File type**: Audio-only files (M4A, WAV, AAC) default to 'audio'; image files default to 'image'; SRT files default to 'srt'
- **Default**: Unidentified video files default to 'video'

Device types include: `video`, `drone`, `audio`, `image`, `srt`, or `unknown`

### 4. Directory Organization
Files are organized by date in the destination directory:
```
<DESTINATION>/
├── 2024/
│   ├── 02/
│   │   ├── 15/
│   │   │   ├── 20240215-143045-video-gopro-a.mp4
│   │   │   ├── 20240215-143045-drone-mavic3.mov
│   │   │   ├── 20240215-143215-image.jpg
│   │   │   └── 20240215-143245-image.png
│   │   └── 16/
│   │       └── 20240216-091530-audio.wav
```

### 5. Filename Generation
Filenames are formatted as `YYYYMMDD-HHMMSS-<device_type>[-<device_tag>].<extension>`:
- `YYYYMMDD`: Date (e.g., 20240215)
- `HHMMSS`: Time (e.g., 143045)
- `<device_type>`: Device type (e.g., video, drone, audio, image)
- `<device_tag>`: Optional device identifier from `--device-tag`
- Extension: Original file extension (e.g., .mp4)

Example outputs:
- `20240215-143045-video.mp4` (GoPro video, no tag)
- `20240215-143045-video-gopro-a.mp4` (GoPro video with `--device-tag gopro-a`)
- `20240215-143045-drone-mavic3.mov` (DJI drone with `--device-tag mavic3`)
- `20240215-143215-image.jpg` (Photo from camera or drone)
- `20240216-091530-audio.wav` (Tascam audio recording)

### 6. Collision Handling
If a file with the same name already exists in the same date folder:
- First collision: Changes to `YYYYMMDD-HHMMSS-<device_type>.1.ext`
- Second collision: Changes to `YYYYMMDD-HHMMSS-<device_type>.2.ext`
- And so on...

### 7. File Copying
Files are copied to the destination directory while preserving their metadata.

### 8. Duplicate File Detection
When a destination file with the same name already exists:
- The tool calculates SHA256 checksums of both files
- If checksums match: File is skipped (already archived)
- If checksums differ: File is skipped with a warning (use `--overwrite` flag to replace it)
- The `--overwrite` flag allows replacing files with different content (use with caution)

## Output

The tool provides informative logging:

```
INFO: Starting archiver: /source -> /destination
INFO: Skipped 128 file(s) older than 1 day(s)
INFO: Found 5 media file(s) to process
INFO: Copied: GOPR1234.MP4 -> 20240222-143025-video-gopro-a.mp4
INFO: Copied: DJI_0001.MOV -> 20240222-143126-drone-mavic3.mov
INFO: Copied: audio.wav -> 20240222-143200-audio.wav
INFO: Processing complete: 5 copied, 0 skipped/failed
```

## Requirements

- Python 3.7+
- mutagen library for audio metadata reading
- hachoir library for video metadata parsing (pure Python)
- opencv-python for video format validation
- Pillow library for image EXIF metadata reading
- pyyaml for config file support
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

**Video Files:**
- MP4 (.mp4) - GoPro, DJI, and general video
- MOV (.mov) - GoPro and general video

**Audio Files:**
- WAV (.wav) - Tascam recorders and general audio
- M4A (.m4a) - Tascam recorders and general audio
- AAC (.aac) - General audio

**Image Files:**
- JPEG (.jpg, .jpeg) - Photos from any device
- PNG (.png) - General images
- RAW Formats (.raw, .dng, .cr2, .nef, .arw, .gpr) - Professional camera RAW files (can be skipped with `--skip-raw` flag)

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
1. Files may be older than 1 day — try `--recent 0` to include all files
2. Files have supported extensions (.mp4, .mov, .m4a, .wav, .aac, .jpg, .jpeg, .png, .raw, .dng, etc.)
3. Destination directory exists and is writable
4. Source directory contains readable files
5. Raw files aren't being skipped due to `--skip-raw` flag
6. Try with a single test file first to isolate the issue

### Parser warnings (hachoir, OpenCV)
You may see warnings like:
- `[warn] Skip parser 'MP4File': Unknown MOV file type`
- `[<NdsFile>] Error when getting size of 'header': delete it`

These are **not our code deleting anything**. They come from third-party parsing libraries (hachoir and OpenCV) that attempt to extract metadata from video files. The "delete it" message refers to internal cleanup of temporary parse structures, not actual file deletion.

These warnings typically occur when:
- Parsing DJI or proprietary video formats that differ from standard MP4/MOV specs
- The file format has unexpected structure or tags
- The library encounters something it doesn't recognize in the metadata

**This is normal and safe** - the archiver continues to work, and files are archived successfully. When metadata extraction fails, the archiver falls back to using the file's modification time for the archive timestamp.

### DJI files with incorrect timestamps
Some DJI drone files may not have extractable creation metadata in the format the archiver expects. In these cases, the archiver will use the file's modification time from the SD card, which is typically the time the file was written (usually very close to when it was actually recorded).

To ensure accurate timestamps:
- If your DJI files were recorded on a drone with correct system time, the modification time should be accurate
- If timestamps are significantly off, check that your drone's clock was set correctly when recording
- You can verify file timestamps using: `ls -lh <file>` (macOS/Linux)

## License

MIT License

## Development

This project is developed with [Claude Code](https://claude.ai/claude-code), Anthropic's CLI tool for AI-assisted software development.
