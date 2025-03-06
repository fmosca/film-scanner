# Film Negative Scanner

A Python application for scanning film negatives using an Olympus camera. This tool connects to your Olympus camera via WiFi, displays a live view on your computer, and allows you to capture, review, and save RAW or JPEG images.

## Features

- Live view from your Olympus camera on your computer
- Capture images with a keypress
- Review images before saving
- Invert colors (useful for film negatives)
- Focus peaking support
- Zoom control
- Download RAW (.orf) files when available

## Prerequisites

- Python 3.7 or newer
- An Olympus camera with WiFi capability (tested with EM5 Mark III)
- Computer connected to the camera's WiFi network

## Setup

### 1. Connect Your Camera

1. Enable WiFi on your camera and set it to "private" mode
2. On your computer, connect to the camera's WiFi network
3. Verify connectivity by opening `http://192.168.0.10/DCIM` in a web browser

### 2. Create a Virtual Environment

```bash
# Create a directory for the project
mkdir film_scanner
cd film_scanner

# Clone the repository (if applicable)
# git clone https://github.com/yourusername/film_scanner.git
# cd film_scanner

# Create a virtual environment
python -m venv .venv/film-scanner

# Activate the virtual environment
# On Windows:
.venv\film-scanner\Scripts\activate
# On macOS/Linux:
source .venv/film-scanner/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Install the Application

Either install in development mode:

```bash
pip install -e .
```

Or install normally:

```bash
pip install .
```

## Running the Application

After installation, you can run the application using:

```bash
# Using the entry point (if installed)
film-scanner

# Or directly with Python
python film_scanner/main.py
```

## Usage

Once the application is running, you'll see the live view from your camera. Use the following keyboard shortcuts:

- **S**: Take a photo in live view mode / Accept and download in preview mode
- **F**: Toggle focus peaking
- **Z**: Cycle through zoom levels (1x, 3x, 5x, 7x, 10x)
- **I**: Invert image colors (helpful for negative film)
- **R**: Reject preview and return to live view
- **?** or **H**: Show help
- **ESC**: Quit the application

## File Storage

By default, images are saved to `~/Pictures/FilmScans`. RAW files (.orf) are prioritized over JPEG files when both are available.

## Troubleshooting

- **No live view**: Make sure your computer is connected to the camera's WiFi network
- **Camera not responding**: Check if the camera is in the correct mode (it should be in WiFi connection mode)
- **Connection issues**: Try restarting both the camera and the application

## Development

The application is organized into several modules:

- `camera_manager.py`: Handles all camera interactions
- `image_processor.py`: Processes images (scaling, inversion)
- `preview_manager.py`: Manages the preview display
- `film_scanner_app.py`: Coordinates UI and components
- `main.py`: Entry point for the application

## License

[MIT License](LICENSE)
