"""
Dependency Injection Container
Manages service lifecycle and dependencies following Dependency Inversion Principle
"""

from typing import Dict, Type, Any, Callable, Optional, TypeVar
from pathlib import Path

from .interfaces import (
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
from .video_services import (
    VideoConverter,
    VideoCompressor,
    VideoTrimmer,
    VideoJoiner,
    VideoInfoExtractor,
    ThumbnailExtractor,
    EncoderDetector
)
from .image_services import (
    ImageConverter,
    ImageInfoExtractor,
    ImageMagickDetector
)
from ..core.config import AppConfig, get_config
from ..core.logger import get_logger


T = TypeVar('T')
logger = get_logger(__name__)


class ServiceContainer:
    """
    Dependency injection container for managing service instances
    Implements singleton pattern for service lifetime management
    """
    
    def __init__(self, config: Optional[AppConfig] = None):
        self.config = config or get_config()
        self._services: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._register_default_services()
    
    def _register_default_services(self) -> None:
        """Register default service factories"""
        ffmpeg_path = self.config.paths.ffmpeg_path
        ffprobe_path = self.config.paths.ffprobe_path
        
        # Register encoder detector (base dependency)
        self.register_singleton(
            IEncoderDetector,
            lambda: EncoderDetector(ffmpeg_path, ffprobe_path)
        )
        
        # Register info extractor
        self.register_singleton(
            IVideoInfoExtractor,
            lambda: VideoInfoExtractor(ffmpeg_path, ffprobe_path)
        )
        
        # Register thumbnail extractor
        self.register_singleton(
            IThumbnailExtractor,
            lambda: ThumbnailExtractor(ffmpeg_path, ffprobe_path)
        )
        
        # Register video converter with encoder detector dependency
        self.register_singleton(
            IVideoConverter,
            lambda: VideoConverter(
                ffmpeg_path,
                ffprobe_path,
                self.resolve(IEncoderDetector)
            )
        )
        
        # Register video compressor with encoder detector dependency
        self.register_singleton(
            IVideoCompressor,
            lambda: VideoCompressor(
                ffmpeg_path,
                ffprobe_path,
                self.resolve(IEncoderDetector)
            )
        )
        
        # Register video trimmer
        self.register_singleton(
            IVideoTrimmer,
            lambda: VideoTrimmer(ffmpeg_path, ffprobe_path)
        )
        
        # Register video joiner with info extractor dependency
        self.register_singleton(
            IVideoJoiner,
            lambda: VideoJoiner(
                ffmpeg_path,
                ffprobe_path,
                self.resolve(IVideoInfoExtractor)
            )
        )
        
        # =================================================================
        # IMAGE SERVICES
        # =================================================================
        
        # Register ImageMagick detector
        self.register_singleton(
            IImageMagickDetector,
            lambda: ImageMagickDetector()
        )
        
        # Register image info extractor with detector dependency
        self.register_singleton(
            IImageInfoExtractor,
            lambda: ImageInfoExtractor(self.resolve(IImageMagickDetector))
        )
        
        # Register image converter with detector dependency
        self.register_singleton(
            IImageConverter,
            lambda: ImageConverter(self.resolve(IImageMagickDetector))
        )
        
        logger.debug("Default services registered")
    
    def register_singleton(
        self,
        interface: Type[T],
        factory: Callable[[], T]
    ) -> None:
        """
        Register a service with singleton lifetime
        
        Args:
            interface: Interface type to register
            factory: Factory function to create instance
        """
        self._factories[interface] = factory
        logger.debug(f"Registered singleton: {interface.__name__}")
    
    def register_transient(
        self,
        interface: Type[T],
        factory: Callable[[], T]
    ) -> None:
        """
        Register a service with transient lifetime (new instance each time)
        
        Args:
            interface: Interface type to register
            factory: Factory function to create instance
        """
        # For transient, we don't cache the instance
        self._factories[interface] = factory
        logger.debug(f"Registered transient: {interface.__name__}")
    
    def register_instance(
        self,
        interface: Type[T],
        instance: T
    ) -> None:
        """
        Register an existing instance
        
        Args:
            interface: Interface type to register
            instance: Pre-created instance
        """
        self._services[interface] = instance
        logger.debug(f"Registered instance: {interface.__name__}")
    
    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve service instance by interface type
        
        Args:
            interface: Interface type to resolve
            
        Returns:
            Service instance
            
        Raises:
            KeyError: If service not registered
        """
        # Return cached instance if exists
        if interface in self._services:
            return self._services[interface]
        
        # Create new instance using factory
        if interface in self._factories:
            logger.debug(f"Creating instance: {interface.__name__}")
            instance = self._factories[interface]()
            self._services[interface] = instance
            return instance
        
        raise KeyError(f"Service not registered: {interface.__name__}")
    
    def resolve_all(self) -> Dict[Type, Any]:
        """
        Resolve all registered services
        
        Returns:
            Dictionary of interface types to instances
        """
        return {
            interface: self.resolve(interface)
            for interface in self._factories.keys()
        }
    
    def clear(self) -> None:
        """Clear all cached service instances"""
        self._services.clear()
        logger.debug("Service cache cleared")


# Global container instance
_container: Optional[ServiceContainer] = None


def get_container(config: Optional[AppConfig] = None) -> ServiceContainer:
    """
    Get global service container instance (singleton pattern)
    
    Args:
        config: Optional configuration (only used on first call)
        
    Returns:
        ServiceContainer instance
    """
    global _container
    if _container is None:
        _container = ServiceContainer(config)
        logger.info("Service container initialized")
    return _container


def reset_container() -> None:
    """Reset global container (useful for testing)"""
    global _container
    _container = None
    logger.debug("Service container reset")
