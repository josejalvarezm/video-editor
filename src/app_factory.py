"""
Application Factory
Creates and configures the main application with dependency injection
"""

from typing import Protocol, Optional
import tkinter as tk

from src.services.container import get_container, ServiceContainer
from src.services.interfaces import (
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
from src.services.adapters import (
    LegacyVideoProcessorAdapter,
    LegacyImageProcessorAdapter
)
from src.core.logger import get_logger


logger = get_logger(__name__)


class VideoServices:
    """Aggregates all video-related services"""
    
    def __init__(self, container: ServiceContainer):
        self.converter: IVideoConverter = container.resolve(IVideoConverter)
        self.compressor: IVideoCompressor = container.resolve(IVideoCompressor)
        self.trimmer: IVideoTrimmer = container.resolve(IVideoTrimmer)
        self.joiner: IVideoJoiner = container.resolve(IVideoJoiner)
        self.info_extractor: IVideoInfoExtractor = container.resolve(IVideoInfoExtractor)
        self.thumbnail_extractor: IThumbnailExtractor = container.resolve(IThumbnailExtractor)
        self.encoder_detector: IEncoderDetector = container.resolve(IEncoderDetector)


class ImageServices:
    """Aggregates all image-related services"""
    
    def __init__(self, container: ServiceContainer):
        self.converter: IImageConverter = container.resolve(IImageConverter)
        self.info_extractor: IImageInfoExtractor = container.resolve(IImageInfoExtractor)
        self.magick_detector: IImageMagickDetector = container.resolve(IImageMagickDetector)


class ApplicationFactory:
    """
    Factory for creating the main application with all dependencies resolved.
    Implements the Factory Pattern for clean dependency injection.
    """
    
    def __init__(self):
        self._container: Optional[ServiceContainer] = None
        self._video_services: Optional[VideoServices] = None
        self._image_services: Optional[ImageServices] = None
        self._video_processor_adapter: Optional[LegacyVideoProcessorAdapter] = None
        self._image_processor_adapter: Optional[LegacyImageProcessorAdapter] = None
    
    def initialize(self) -> None:
        """Initialize the DI container and resolve all services"""
        logger.info("Initializing application factory...")
        
        try:
            self._container = get_container()
            self._video_services = VideoServices(self._container)
            self._image_services = ImageServices(self._container)
            
            # Create legacy adapters for backward compatibility
            self._video_processor_adapter = LegacyVideoProcessorAdapter(
                encoder_detector=self._video_services.encoder_detector,
                converter=self._video_services.converter,
                compressor=self._video_services.compressor,
                trimmer=self._video_services.trimmer,
                joiner=self._video_services.joiner,
                info_extractor=self._video_services.info_extractor,
                thumbnail_extractor=self._video_services.thumbnail_extractor
            )
            
            self._image_processor_adapter = LegacyImageProcessorAdapter(
                magick_detector=self._image_services.magick_detector,
                converter=self._image_services.converter,
                info_extractor=self._image_services.info_extractor
            )
            
            logger.info("All services initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize services: {e}")
            raise
    
    @property
    def container(self) -> ServiceContainer:
        """Get the service container"""
        if self._container is None:
            self.initialize()
        return self._container
    
    @property
    def video_services(self) -> VideoServices:
        """Get aggregated video services"""
        if self._video_services is None:
            self.initialize()
        return self._video_services
    
    @property
    def image_services(self) -> ImageServices:
        """Get aggregated image services"""
        if self._image_services is None:
            self.initialize()
        return self._image_services
    
    @property
    def video_processor(self) -> LegacyVideoProcessorAdapter:
        """Get legacy-compatible video processor"""
        if self._video_processor_adapter is None:
            self.initialize()
        return self._video_processor_adapter
    
    @property
    def image_processor(self) -> LegacyImageProcessorAdapter:
        """Get legacy-compatible image processor"""
        if self._image_processor_adapter is None:
            self.initialize()
        return self._image_processor_adapter
    
    def create_app(self, root: tk.Tk):
        """
        Create the main application with all dependencies injected.
        
        Args:
            root: Tkinter root window
            
        Returns:
            Configured VideoUpscalerApp instance
        """
        from main import VideoUpscalerApp
        
        # Initialize if not already done
        if self._container is None:
            self.initialize()
        
        # Create app with injected legacy-compatible processors
        app = VideoUpscalerApp(
            root,
            video_processor=self._video_processor_adapter,
            image_processor=self._image_processor_adapter
        )
        
        logger.info("Application created successfully")
        return app


# Global factory instance (singleton)
_factory: Optional[ApplicationFactory] = None


def get_factory() -> ApplicationFactory:
    """Get the global application factory instance"""
    global _factory
    if _factory is None:
        _factory = ApplicationFactory()
    return _factory
