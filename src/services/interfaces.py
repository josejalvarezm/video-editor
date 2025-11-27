"""
Video and Image Processing Interfaces
Defines contracts for media operations following Interface Segregation Principle
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List, Callable
from dataclasses import dataclass


@dataclass
class VideoInfo:
    """Video metadata information"""
    duration: str
    duration_seconds: float
    resolution: str
    width: int
    height: int
    codec: str
    fps: float
    bitrate: Optional[str] = None
    size: Optional[str] = None


class IVideoConverter(ABC):
    """Interface for video conversion and upscaling operations"""
    
    @abstractmethod
    def convert_to_resolution(
        self, 
        input_path: Path, 
        output_path: Path, 
        resolution: str,
        **kwargs
    ) -> None:
        """
        Convert video to specified resolution
        
        Args:
            input_path: Source video file
            output_path: Destination video file
            resolution: Target resolution (e.g., "1080p", "4k")
            **kwargs: Additional conversion parameters
            
        Raises:
            VideoConversionError: If conversion fails
        """
        pass


class IVideoCompressor(ABC):
    """Interface for video compression operations"""
    
    @abstractmethod
    def compress(
        self,
        input_path: Path,
        output_path: Path,
        codec: str,
        quality: str,
        audio_codec: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Compress video with specified codec and quality
        
        Args:
            input_path: Source video file
            output_path: Destination video file
            codec: Video codec (h264, h265)
            quality: Quality preset (high, balanced, max)
            audio_codec: Audio codec (aac, copy)
            **kwargs: Additional compression parameters
            
        Raises:
            VideoCompressionError: If compression fails
        """
        pass


class IVideoTrimmer(ABC):
    """Interface for video trimming operations"""
    
    @abstractmethod
    def trim(
        self,
        input_path: Path,
        output_path: Path,
        start_time: str,
        end_time: str,
        lossless: bool = True
    ) -> None:
        """
        Trim video to specified time range
        
        Args:
            input_path: Source video file
            output_path: Destination video file
            start_time: Start timestamp (HH:MM:SS.mmm)
            end_time: End timestamp (HH:MM:SS.mmm)
            lossless: Use stream copy for lossless trim
            
        Raises:
            VideoTrimmingError: If trimming fails
        """
        pass


class IVideoJoiner(ABC):
    """Interface for video joining/concatenation operations"""
    
    @abstractmethod
    def join(
        self,
        input_paths: List[Path],
        output_path: Path,
        lossless: bool = True
    ) -> None:
        """
        Join multiple videos into single file
        
        Args:
            input_paths: List of source video files
            output_path: Destination video file
            lossless: Use concat demuxer for lossless join
            
        Raises:
            VideoJoiningError: If joining fails
            VideoIncompatibleError: If videos have incompatible formats
        """
        pass
    
    @abstractmethod
    def check_compatibility(
        self,
        video_paths: List[Path]
    ) -> Tuple[bool, str]:
        """
        Check if videos can be joined losslessly
        
        Args:
            video_paths: List of video files to check
            
        Returns:
            Tuple of (is_compatible, message)
        """
        pass


class IVideoInfoExtractor(ABC):
    """Interface for video metadata extraction"""
    
    @abstractmethod
    def get_info(self, video_path: Path) -> VideoInfo:
        """
        Extract video metadata
        
        Args:
            video_path: Video file path
            
        Returns:
            VideoInfo object with metadata
            
        Raises:
            VideoProcessingError: If extraction fails
        """
        pass
    
    @abstractmethod
    def get_raw_info(self, video_path: Path) -> str:
        """
        Get raw ffprobe JSON output
        
        Args:
            video_path: Video file path
            
        Returns:
            JSON string with video information
        """
        pass


class IThumbnailExtractor(ABC):
    """Interface for video thumbnail extraction"""
    
    @abstractmethod
    def extract_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: str = "00:00:01",
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> None:
        """
        Extract thumbnail frame from video
        
        Args:
            video_path: Source video file
            output_path: Destination image file
            timestamp: Time position to extract (HH:MM:SS)
            width: Target width (maintains aspect if height is None)
            height: Target height (maintains aspect if width is None)
            
        Raises:
            ThumbnailError: If extraction fails
        """
        pass


class IEncoderDetector(ABC):
    """Interface for hardware encoder detection"""
    
    @abstractmethod
    def detect_gpu_encoder(self) -> str:
        """
        Detect available GPU encoder
        
        Returns:
            Encoder type: 'nvenc', 'amf', 'qsv', or 'cpu'
        """
        pass
    
    @abstractmethod
    def has_hevc_encoder(self) -> bool:
        """
        Check if H.265/HEVC encoder is available
        
        Returns:
            True if HEVC encoder available
        """
        pass
    
    @abstractmethod
    def check_ffmpeg_available(self) -> bool:
        """
        Check if FFmpeg is available in PATH
        
        Returns:
            True if FFmpeg is accessible
        """
        pass


# =============================================================================
# IMAGE PROCESSING INTERFACES
# =============================================================================

@dataclass
class ImageInfo:
    """Image metadata container"""
    width: int
    height: int
    format: str
    size_bytes: int
    
    @property
    def size_formatted(self) -> str:
        """Human-readable file size"""
        if self.size_bytes >= 1_000_000:
            return f"{self.size_bytes / 1_000_000:.2f} MB"
        elif self.size_bytes >= 1_000:
            return f"{self.size_bytes / 1_000:.2f} KB"
        return f"{self.size_bytes} B"
    
    @property
    def resolution(self) -> str:
        """Resolution as WxH string"""
        return f"{self.width}x{self.height}"


@dataclass
class ImageConversionResult:
    """Result of image conversion operation"""
    success: bool
    message: str
    input_path: Optional[Path] = None
    output_path: Optional[Path] = None


class IImageInfoExtractor(ABC):
    """Interface for image metadata extraction"""
    
    @abstractmethod
    def get_info(self, image_path: Path) -> ImageInfo:
        """
        Extract image metadata
        
        Args:
            image_path: Image file path
            
        Returns:
            ImageInfo object with metadata
            
        Raises:
            ImageProcessingError: If extraction fails
        """
        pass
    
    @abstractmethod
    def is_supported(self, file_path: Path) -> bool:
        """
        Check if file format is supported
        
        Args:
            file_path: File path to check
            
        Returns:
            True if format is supported
        """
        pass


class IImageConverter(ABC):
    """Interface for image format conversion operations"""
    
    @property
    @abstractmethod
    def supported_input_formats(self) -> List[str]:
        """List of supported input file extensions"""
        pass
    
    @property
    @abstractmethod
    def supported_output_formats(self) -> Dict[str, str]:
        """Dict of output format name to extension"""
        pass
    
    @abstractmethod
    def convert(
        self,
        input_path: Path,
        output_path: Path,
        quality: int = 85,
        resize_width: Optional[int] = None
    ) -> ImageConversionResult:
        """
        Convert image to specified format
        
        Args:
            input_path: Source image file
            output_path: Destination image file
            quality: Quality percentage (1-100) for lossy formats
            resize_width: Target width in pixels (maintains aspect ratio)
            
        Returns:
            ImageConversionResult with success status and message
        """
        pass
    
    @abstractmethod
    def batch_convert(
        self,
        input_files: List[Path],
        output_format: str,
        output_dir: Optional[Path] = None,
        quality: int = 85,
        resize_width: Optional[int] = None,
        delete_originals: bool = False,
        progress_callback: Optional[Callable[[int, int, str], None]] = None
    ) -> Dict[str, List]:
        """
        Convert multiple images
        
        Args:
            input_files: List of input file paths
            output_format: Output format key (e.g., 'JPG', 'PNG', 'WebP')
            output_dir: Output directory (None = same as input)
            quality: Quality percentage for lossy formats
            resize_width: Target width in pixels (None = original)
            delete_originals: Whether to delete original files after conversion
            progress_callback: Optional callback(current, total, filename)
            
        Returns:
            Dict with 'success', 'failed', 'messages' lists
        """
        pass


class IImageMagickDetector(ABC):
    """Interface for ImageMagick detection"""
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        Check if ImageMagick is available
        
        Returns:
            True if ImageMagick is installed and accessible
        """
        pass
    
    @abstractmethod
    def get_version(self) -> Optional[str]:
        """
        Get ImageMagick version string
        
        Returns:
            Version string or None if not available
        """
        pass
    
    @abstractmethod
    def get_executable_path(self) -> Optional[str]:
        """
        Get path to ImageMagick executable
        
        Returns:
            Path to magick.exe or None if not found
        """
        pass
