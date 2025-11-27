"""
Custom Exceptions
Hierarchical exception system for better error handling
"""

from typing import Optional


class VideoEditorError(Exception):
    """Base exception for all application errors"""
    
    def __init__(self, message: str, details: Optional[str] = None):
        self.message = message
        self.details = details
        super().__init__(self.message)
    
    def __str__(self) -> str:
        if self.details:
            return f"{self.message}\nDetails: {self.details}"
        return self.message


# Configuration Errors
class ConfigurationError(VideoEditorError):
    """Configuration-related errors"""
    pass


# Dependency Errors
class DependencyError(VideoEditorError):
    """Missing or invalid dependencies"""
    pass


class FFmpegNotFoundError(DependencyError):
    """FFmpeg executable not found"""
    
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            "FFmpeg not found in PATH",
            details or "Please install FFmpeg or run setup.bat"
        )


class FFprobeNotFoundError(DependencyError):
    """FFprobe executable not found"""
    
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            "FFprobe not found in PATH",
            details or "FFprobe comes bundled with FFmpeg"
        )


# Video Processing Errors
class VideoProcessingError(VideoEditorError):
    """Base class for video processing errors"""
    pass


class VideoConversionError(VideoProcessingError):
    """Video conversion/upscaling failed"""
    pass


class VideoCompressionError(VideoProcessingError):
    """Video compression failed"""
    pass


class VideoTrimmingError(VideoProcessingError):
    """Video trimming failed"""
    pass


class VideoJoiningError(VideoProcessingError):
    """Video joining/concatenation failed"""
    pass


class VideoIncompatibleError(VideoProcessingError):
    """Videos are not compatible for joining"""
    
    def __init__(self, details: str):
        super().__init__(
            "Videos have different formats and cannot be joined losslessly",
            details
        )


# File Errors
class FileError(VideoEditorError):
    """File operation errors"""
    pass


class FileNotFoundError(FileError):
    """Video file not found"""
    pass


class InvalidFileFormatError(FileError):
    """Invalid video file format"""
    pass


class OutputDirectoryError(FileError):
    """Cannot write to output directory"""
    pass


# Thumbnail Errors
class ThumbnailError(VideoEditorError):
    """Thumbnail extraction errors"""
    pass


# GPU Errors
class GPUError(VideoEditorError):
    """GPU acceleration errors"""
    pass


class EncoderNotFoundError(GPUError):
    """Required video encoder not available"""
    
    def __init__(self, encoder: str, details: Optional[str] = None):
        super().__init__(
            f"Video encoder '{encoder}' not found",
            details or "GPU acceleration may not be available"
        )


# UI Errors
class UIError(VideoEditorError):
    """User interface errors"""
    pass


class InvalidInputError(UIError):
    """User provided invalid input"""
    pass


class OperationCancelledError(VideoEditorError):
    """User cancelled the operation"""
    pass


# =============================================================================
# IMAGE PROCESSING ERRORS
# =============================================================================

class ImageProcessingError(VideoEditorError):
    """Base class for image processing errors"""
    pass


class ImageConversionError(ImageProcessingError):
    """Image conversion failed"""
    pass


class ImageMagickNotFoundError(DependencyError):
    """ImageMagick executable not found"""
    
    def __init__(self, details: Optional[str] = None):
        super().__init__(
            "ImageMagick not found",
            details or "Please install ImageMagick or run the installer"
        )


class UnsupportedImageFormatError(ImageProcessingError):
    """Image format not supported"""
    
    def __init__(self, format_ext: str, details: Optional[str] = None):
        super().__init__(
            f"Unsupported image format: {format_ext}",
            details or "See supported formats in ImageProcessor.INPUT_FORMATS"
        )
