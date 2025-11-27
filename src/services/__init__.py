"""
Media Processing Services
Provides SOLID-compliant interfaces and implementations for video/image processing
"""

from .interfaces import (
    VideoInfo,
    ImageInfo,
    ImageConversionResult,
    IVideoConverter,
    IVideoCompressor,
    IVideoTrimmer,
    IVideoJoiner,
    IVideoInfoExtractor,
    IThumbnailExtractor,
    IEncoderDetector,
    IImageConverter,
    IImageInfoExtractor,
    IImageMagickDetector
)

from .container import (
    ServiceContainer,
    get_container,
    reset_container
)

from .adapters import (
    LegacyVideoProcessorAdapter,
    LegacyImageProcessorAdapter
)

__all__ = [
    # Data classes
    'VideoInfo',
    'ImageInfo',
    'ImageConversionResult',
    
    # Video interfaces
    'IVideoConverter',
    'IVideoCompressor',
    'IVideoTrimmer',
    'IVideoJoiner',
    'IVideoInfoExtractor',
    'IThumbnailExtractor',
    'IEncoderDetector',
    
    # Image interfaces
    'IImageConverter',
    'IImageInfoExtractor',
    'IImageMagickDetector',
    
    # Container
    'ServiceContainer',
    'get_container',
    'reset_container',
    
    # Adapters
    'LegacyVideoProcessorAdapter',
    'LegacyImageProcessorAdapter',
]
