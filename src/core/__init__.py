"""
Core Module
Provides configuration, logging, and custom exceptions
"""

from .config import AppConfig, get_config
from .logger import get_logger
from .exceptions import (
    VideoEditorError,
    ConfigurationError,
    DependencyError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    VideoProcessingError,
    VideoConversionError,
    VideoCompressionError,
    VideoTrimmingError,
    VideoJoiningError,
    VideoIncompatibleError,
    FileError,
    ThumbnailError,
    GPUError,
    EncoderNotFoundError,
    UIError,
    InvalidInputError,
    OperationCancelledError,
    ImageProcessingError,
    ImageConversionError,
    ImageMagickNotFoundError,
    UnsupportedImageFormatError
)

__all__ = [
    # Config
    'AppConfig',
    'get_config',
    
    # Logging
    'get_logger',
    
    # Base exceptions
    'VideoEditorError',
    'ConfigurationError',
    'DependencyError',
    
    # Video exceptions
    'FFmpegNotFoundError',
    'FFprobeNotFoundError',
    'VideoProcessingError',
    'VideoConversionError',
    'VideoCompressionError',
    'VideoTrimmingError',
    'VideoJoiningError',
    'VideoIncompatibleError',
    
    # Image exceptions
    'ImageProcessingError',
    'ImageConversionError',
    'ImageMagickNotFoundError',
    'UnsupportedImageFormatError',
    
    # Other exceptions
    'FileError',
    'ThumbnailError',
    'GPUError',
    'EncoderNotFoundError',
    'UIError',
    'InvalidInputError',
    'OperationCancelledError',
]
