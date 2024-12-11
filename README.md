# Video Search Application

This application allows you to search through video content using transcribed audio. It supports both English and Chinese languages.

## Features

- Video transcription using OpenAI's Whisper
- Word extraction and indexing
- Search functionality with timestamp matching
- Video playback at specific timestamps
- Support for both English and Chinese text

## Installation

1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Install VLC media player (required for video playback)

## Usage

1. Run the application:
```bash
python main.py
```

2. Click "Open Folder" to select a directory containing video files
3. Click "Build Index" to process videos and create the search index
4. Use the search box to find specific content in the videos
5. Click on search results to play the corresponding video segments

## Notes

- Supported video formats: MP4, AVI, MOV
- The application creates an index file (`video_index.json`) in the video directory
- Use "Rebuild Index" to reprocess all videos in the directory
