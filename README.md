# Video Editor Pro

A professional desktop application for batch video processing with GPU acceleration. Built with Python and Tkinter, following **SOLID principles** and clean architecture patterns.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-green.svg)
![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)
![GPU](https://img.shields.io/badge/GPU-NVIDIA%20%7C%20AMD%20%7C%20Intel-orange.svg)

## ✨ Features

### Video Processing
- **🎬 Upscale/Convert** - Convert videos to 720p, 1080p, 1440p, or 4K
- **📦 Compress** - Reduce file size with configurable quality (CRF 18-28)
- **✂️ Trim** - Lossless video trimming with precise timestamps
- **🔗 Join** - Concatenate multiple videos into one

### Image Processing
- **🖼️ Format Conversion** - Convert between JPG, PNG, WebP, BMP, TIFF
- **📐 Batch Resize** - Resize to preset or custom dimensions
- **🎨 JXR/HDR Support** - Convert JPEG XR files via Windows WIC codec

### Performance
- **⚡ GPU Acceleration** - Automatic NVIDIA NVENC, AMD AMF, Intel QSV detection
- **🔄 Batch Processing** - Process multiple files with progress tracking
- **🖥️ Modern UI** - Clean, responsive Tkinter interface

## 🏗️ Architecture

This project demonstrates **SOLID principles** and professional Python patterns:

```
src/
├── core/
│   ├── config.py          # Application configuration
│   ├── exceptions.py      # Custom exception hierarchy
│   └── logger.py          # Centralized logging
├── services/
│   ├── interfaces.py      # Abstract interfaces (ISP)
│   ├── container.py       # Dependency injection container (DIP)
│   ├── video_services.py  # Video processing implementations
│   ├── image_services.py  # Image processing implementations
│   └── adapters.py        # Legacy compatibility adapters
└── app_factory.py         # Application factory pattern
```

### SOLID Implementation

| Principle | Implementation |
|-----------|---------------|
| **S**ingle Responsibility | Each service class has one purpose |
| **O**pen/Closed | Interfaces allow extension without modification |
| **L**iskov Substitution | Adapters ensure interchangeability |
| **I**nterface Segregation | Small, focused interfaces |
| **D**ependency Inversion | Constructor injection via factory |

## 🚀 Installation

### Prerequisites

- Python 3.10 or higher
- FFmpeg (for video processing)
- ImageMagick (for image processing)

### Quick Start

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/video-editor.git
   cd video-editor
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install FFmpeg** (Windows)
   ```bash
   winget install FFmpeg
   ```

5. **Install ImageMagick** (Windows)
   ```bash
   winget install ImageMagick.ImageMagick
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

## 📖 Usage

### Video Upscaling
1. Click "Add Videos" to select files
2. Choose target resolution (720p - 4K)
3. Select codec (H.264 or H.265)
4. Click "Start Conversion"

### Video Compression
1. Add videos to the Compress tab
2. Adjust CRF slider (lower = higher quality)
3. Choose audio bitrate
4. Click "Compress"

### Video Trimming
1. Select a video file
2. Enter start and end timestamps (HH:MM:SS)
3. Click "Trim Video"

### Image Conversion
1. Add images in the Image Converter tab
2. Select output format (WebP recommended)
3. Adjust quality and resize options
4. Click "Convert"

## 🔧 Configuration

The application auto-detects:
- GPU encoder (NVENC/AMF/QSV/CPU)
- FFmpeg installation path
- ImageMagick installation path

For custom paths, modify `src/core/config.py`.

## 🤝 Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [FFmpeg](https://ffmpeg.org/) - Video processing backbone
- [ImageMagick](https://imagemagick.org/) - Image processing
- [Pillow](https://pillow.readthedocs.io/) - Python imaging library
