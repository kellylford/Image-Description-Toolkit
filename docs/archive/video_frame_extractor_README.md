# Video Frame Extractor

A Python tool for extracting frames from video files with configurable options including intelligent scene change detection.

## Features

- **Two Extraction Modes:**
  - **Time Interval**: Extract frames at regular intervals (e.g., every 5 seconds)
  - **Scene Change Detection**: Intelligently extract frames when significant visual changes occur
- **Recursive Directory Processing**: Process entire folder structures automatically
- **Configurable Settings**: All options controlled via JSON configuration file
- **Multiple Video Formats**: Supports MP4, AVI, MKV, MOV, WMV, FLV, WebM, M4V
- **Flexible Output Options**: Simple flat structure or preserve directory hierarchy
- **Image Quality Control**: Adjustable JPEG compression (1-100)
- **Frame Resizing**: Optional resize frames to save space
- **Progress Logging**: Detailed progress reporting and timing information
- **Smart Skip Logic**: Skip processing if output already exists (configurable)
- **Command Line Overrides**: Override config settings via command line arguments

### Installation

#### Prerequisites
- Python 3.7 or higher
- OpenCV and NumPy libraries

#### Quick Setup
1. Clone or download this repository
2. Install required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

#### Manual Installation
```bash
pip install opencv-python numpy
```

### Usage

#### Basic Usage
Extract frames from a single video:
```bash
python video_frame_extractor.py video.mp4
```

Process all videos in a directory recursively:
```bash
python video_frame_extractor.py "/path/to/videos"
```

#### Command Line Options

**Time Interval Override:**
```bash
# Extract every 2 seconds (overrides config)
python video_frame_extractor.py --time 2.0 "/path/to/videos"
```

**Scene Change Override:**
```bash
# Use scene detection with 25% threshold (overrides config)
python video_frame_extractor.py --scene 25.0 "/path/to/videos"
```

**Custom Config File:**
```bash
python video_frame_extractor.py "/path/to/videos" -c my_config.json
```

### Configuration

The tool uses a JSON configuration file for all extraction settings. By default, it looks for `video_frame_extractor_config.json` in the scripts directory, which contains sensible defaults. You can also specify a custom config file path.

#### Getting Started with Configuration

**Use the default config (recommended):**
```bash
python video_frame_extractor.py video.mp4
```

**Create a custom config file:**
```bash
# Create a default config file in current directory for customization
python video_frame_extractor.py --create-config

# Then use your custom config
python video_frame_extractor.py video.mp4 -c video_frame_extractor_config.json
```

#### Configuration Options

| Setting | Description | Default | Example |
|---------|-------------|---------|---------|
| `extraction_mode` | Extraction method | `"time_interval"` | `"scene_change"` |
| `time_interval_seconds` | Seconds between extractions | `5.0` | `10.0` |
| `scene_change_threshold` | Sensitivity for scene detection (%) | `30.0` | `25.0` |
| `min_scene_duration_seconds` | Minimum time between scene extractions | `1.0` | `2.0` |
| `output_directory` | Where to save extracted frames | `"extracted_frames"` | `"thumbnails"` |
| `preserve_directory_structure` | Keep original folder layout | `true` | `false` |
| `image_quality` | JPEG quality (1-100) | `95` | `80` |
| `resize_width` | Resize frame width (pixels) | `null` | `1920` |
| `resize_height` | Resize frame height (pixels) | `null` | `1080` |
| `frame_prefix` | Filename prefix for extracted frames | `"frame"` | `"thumb"` |
| `start_time_seconds` | Start extraction at time | `0` | `30` |
| `end_time_seconds` | Stop extraction at time | `null` | `300` |
| `max_frames_per_video` | Limit frames per video | `null` | `50` |
| `skip_existing` | Skip if output directory has files | `true` | `false` |
| `log_progress` | Show detailed progress | `true` | `false` |

### Sample Configuration

```json
{
    "extraction_mode": "scene_change",
    "scene_change_threshold": 25.0,
    "min_scene_duration_seconds": 2.0,
    "output_directory": "thumbnails",
    "preserve_directory_structure": true,
    "image_quality": 90,
    "resize_width": 1280,
    "resize_height": 720,
    "frame_prefix": "scene",
    "max_frames_per_video": 20,
    "skip_existing": true,
    "log_progress": true
}
```

## Extraction Modes

### Time Interval Mode
Extracts frames at regular time intervals. Perfect for:
- Creating consistent thumbnails
- Time-lapse creation
- Regular sampling of video content

**Example**: Extract a frame every 10 seconds
```json
{
    "extraction_mode": "time_interval",
    "time_interval_seconds": 10.0
}
```

### Scene Change Detection Mode
Intelligently detects when video content changes significantly. Perfect for:
- Capturing key moments
- Identifying scene transitions
- Content analysis and summarization

**How it works**: Compares consecutive frames and extracts when a threshold percentage of pixels change significantly.

**Example**: Extract frames when 25% of the image changes, with minimum 2 seconds between extractions
```json
{
    "extraction_mode": "scene_change",
    "scene_change_threshold": 25.0,
    "min_scene_duration_seconds": 2.0
}
```

## Output Structure

### With Directory Structure Preserved
```
extracted_frames/
├── Movies/
│   ├── Action/
│   │   └── movie1/
│   │       ├── frame_00.05s.jpg
│   │       ├── frame_00.10s.jpg
│   │       └── ...
│   └── Comedy/
│       └── movie2/
│           ├── frame_00.05s.jpg
│           └── ...
```

### Flattened Structure
```
extracted_frames/
├── movie1/
│   ├── frame_00.05s.jpg
│   ├── frame_00.10s.jpg
│   └── ...
├── movie2/
│   ├── frame_00.05s.jpg
│   └── ...
```

## Examples

### Extract Thumbnails for Video Library
```json
{
    "extraction_mode": "time_interval",
    "time_interval_seconds": 60.0,
    "output_directory": "video_thumbnails",
    "resize_width": 320,
    "resize_height": 180,
    "image_quality": 85,
    "max_frames_per_video": 5
}
```

### Scene Analysis for Content Review
```json
{
    "extraction_mode": "scene_change",
    "scene_change_threshold": 20.0,
    "min_scene_duration_seconds": 3.0,
    "output_directory": "scene_analysis",
    "preserve_directory_structure": true,
    "frame_prefix": "scene"
}
```

### High-Quality Stills Every 30 Seconds
```json
{
    "extraction_mode": "time_interval",
    "time_interval_seconds": 30.0,
    "image_quality": 100,
    "output_directory": "high_quality_stills"
}
```

### Command Line Examples

```bash
# Extract frames every 2 seconds from a single video
python video_frame_extractor.py movie.mp4 --time 2

# Use scene detection with 15% threshold on entire directory
python video_frame_extractor.py /path/to/videos --scene 15

# Extract frames every 30 seconds with custom config
python video_frame_extractor.py videos/ -c thumbnails.json --time 30

# Use sensitive scene detection (10% threshold)
python video_frame_extractor.py documentary.mkv --scene 10

# Quick thumbnail extraction (every 60 seconds)
python video_frame_extractor.py /path/to/movies --time 60
```

## Troubleshooting

### Frame Extractor Issues

**Error: "Import cv2 could not be resolved"**
- Install OpenCV: `pip install opencv-python`

**Error: "Could not open video"**
- Check video file format is supported
- Verify file path is correct
- Ensure video file is not corrupted

**No frames extracted**
- Check video duration vs. `time_interval_seconds`
- Verify `start_time_seconds` and `end_time_seconds` settings
- For scene change mode, try lowering `scene_change_threshold`

**Out of memory errors**
- Reduce `resize_width` and `resize_height`
- Lower `image_quality`
- Process videos individually instead of batch processing

### Performance Tips

- Use scene change mode for videos with distinct scenes
- Use time interval mode for consistent sampling
- Resize frames to reduce output file sizes
- Adjust `image_quality` based on your needs (80-95 is usually sufficient)
- Use `max_frames_per_video` to limit output for very long videos

## Supported Video Formats

- MP4 (.mp4)
- AVI (.avi)
- MKV (.mkv)
- MOV (.mov)
- WMV (.wmv)
- FLV (.flv)
- WebM (.webm)
- M4V (.m4v)

## Requirements

- Python 3.7+
- OpenCV Python (opencv-python>=4.8.0)
- NumPy (numpy>=1.24.0)

## License

This project is open source. Feel free to modify and distribute according to your needs.

## Contributing

Contributions are welcome! Feel free to submit issues, feature requests, or pull requests.
