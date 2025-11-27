"""
Service Adapters
Provides backward-compatible adapters for legacy code migration
"""

from typing import Optional, List, Dict, Callable, Tuple
from pathlib import Path

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
    IImageMagickDetector,
    VideoInfo,
    ImageInfo,
    ImageConversionResult
)
from src.core.logger import get_logger


logger = get_logger(__name__)


class LegacyVideoProcessorAdapter:
    """
    Adapter that wraps legacy VideoProcessor to work with SOLID interfaces.
    Implements the Adapter Pattern to bridge old and new code.
    
    This allows gradual migration - main.py can use this adapter which
    internally uses the SOLID services, maintaining the same API.
    """
    
    def __init__(
        self,
        encoder_detector: IEncoderDetector,
        converter: IVideoConverter,
        compressor: IVideoCompressor,
        trimmer: IVideoTrimmer,
        joiner: IVideoJoiner,
        info_extractor: IVideoInfoExtractor,
        thumbnail_extractor: IThumbnailExtractor
    ):
        self._encoder_detector = encoder_detector
        self._converter = converter
        self._compressor = compressor
        self._trimmer = trimmer
        self._joiner = joiner
        self._info_extractor = info_extractor
        self._thumbnail_extractor = thumbnail_extractor
        
        # Expose properties matching old VideoProcessor
        self.gpu_encoder = self._encoder_detector.detect_gpu_encoder()
        self.gpu_name = self._get_gpu_name()
        self.ffmpeg_path = "ffmpeg"  # Container handles path resolution
    
    def _get_gpu_name(self) -> str:
        """Get GPU name - simplified for adapter"""
        encoder = self.gpu_encoder
        if encoder == "nvenc":
            return "NVIDIA GPU"
        elif encoder == "amf":
            return "AMD GPU"
        elif encoder == "qsv":
            return "Intel GPU"
        return "CPU"
    
    def check_ffmpeg(self) -> bool:
        """Check if FFmpeg is available"""
        return self._encoder_detector.check_ffmpeg_available()
    
    def has_hevc_encoder(self) -> bool:
        """Check for HEVC encoder support"""
        return self._encoder_detector.has_hevc_encoder()
    
    def get_detailed_video_info(self, video_path: str) -> Optional[Dict]:
        """Get video info matching legacy format"""
        try:
            info = self._info_extractor.get_info(Path(video_path))
            return {
                'duration': info.duration,
                'duration_seconds': info.duration_seconds,
                'resolution': info.resolution,
                'width': info.width,
                'height': info.height,
                'codec': info.codec,
                'fps': info.fps,
                'bitrate': info.bitrate,
                'size': info.size
            }
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            return None
    
    def extract_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: str = "00:00:01",
        width: int = 120,
        height: int = 68
    ) -> bool:
        """Extract video thumbnail"""
        try:
            self._thumbnail_extractor.extract_thumbnail(
                Path(video_path),
                Path(output_path),
                timestamp=timestamp,
                width=width,
                height=height
            )
            return True
        except Exception as e:
            logger.error(f"Thumbnail extraction failed: {e}")
            return False
    
    def convert_to_hd(
        self,
        input_path: str,
        output_path: str,
        target_resolution: str = "1080p",
        codec: str = "h264",
        preset: str = "slow",
        crf: int = 18,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Convert video to HD resolution"""
        try:
            self._converter.convert_to_resolution(
                Path(input_path),
                Path(output_path),
                resolution=target_resolution,
                codec=codec,
                preset=preset,
                crf=crf,
                progress_callback=progress_callback
            )
            return True
        except Exception as e:
            logger.error(f"Video conversion failed: {e}")
            return False
    
    def compress_video(
        self,
        input_path: str,
        output_path: str,
        crf: int = 23,
        preset: str = "slow",
        audio_bitrate: str = "128k",
        codec: str = "h264",
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Compress video file"""
        try:
            self._compressor.compress(
                Path(input_path),
                Path(output_path),
                crf=crf,
                preset=preset,
                audio_bitrate=audio_bitrate,
                codec=codec,
                progress_callback=progress_callback
            )
            return True
        except Exception as e:
            logger.error(f"Video compression failed: {e}")
            return False
    
    def trim_video_lossless(
        self,
        input_path: str,
        output_path: str,
        start_time: str,
        end_time: str,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Trim video without re-encoding"""
        try:
            self._trimmer.trim(
                Path(input_path),
                Path(output_path),
                start_time=start_time,
                end_time=end_time,
                lossless=True
            )
            return True
        except Exception as e:
            logger.error(f"Video trimming failed: {e}")
            return False
    
    def check_video_compatibility(
        self,
        video_paths: List[str]
    ) -> Tuple[bool, str]:
        """Check if videos can be joined losslessly"""
        try:
            return self._joiner.check_compatibility(
                [Path(p) for p in video_paths]
            )
        except Exception as e:
            return False, str(e)
    
    def join_videos_concat(
        self,
        video_paths: List[str],
        output_path: str,
        lossless: bool = True,
        progress_callback: Optional[Callable] = None
    ) -> bool:
        """Join multiple videos into one"""
        try:
            self._joiner.join(
                [Path(p) for p in video_paths],
                Path(output_path),
                lossless=lossless
            )
            return True
        except Exception as e:
            logger.error(f"Video joining failed: {e}")
            return False


class LegacyImageProcessorAdapter:
    """
    Adapter that wraps SOLID image services to match legacy ImageProcessor API.
    """
    
    # Expose class attributes for compatibility
    INPUT_FORMATS = [
        '.jxr', '.hdp', '.wdp', '.jpg', '.jpeg', '.png',
        '.bmp', '.tiff', '.tif', '.webp', '.gif', '.heic', '.heif'
    ]
    
    OUTPUT_FORMATS = {
        'JPG': '.jpg',
        'PNG': '.png',
        'WebP': '.webp',
        'BMP': '.bmp',
        'TIFF': '.tiff'
    }
    
    RESIZE_PRESETS = {
        'Original': None,
        '1920px (Full HD)': 1920,
        '1280px (HD)': 1280,
        '800px (Web)': 800,
        '640px (Thumbnail)': 640,
        'Custom': 'custom'
    }
    
    def __init__(
        self,
        magick_detector: IImageMagickDetector,
        converter: IImageConverter,
        info_extractor: IImageInfoExtractor
    ):
        self._detector = magick_detector
        self._converter = converter
        self._info_extractor = info_extractor
        self.magick_path = self._detector.get_executable_path()
    
    def is_available(self) -> bool:
        """Check if ImageMagick is available"""
        return self._detector.is_available()
    
    def get_version(self) -> Optional[str]:
        """Get ImageMagick version string"""
        return self._detector.get_version()
    
    def get_image_info(self, input_path: str) -> Optional[Dict]:
        """Get image information"""
        try:
            info = self._info_extractor.get_info(Path(input_path))
            return {
                'width': info.width,
                'height': info.height,
                'format': info.format,
                'size_bytes': info.size_bytes
            }
        except Exception:
            return None
    
    def convert_image(
        self,
        input_path: str,
        output_path: str,
        quality: int = 85,
        resize_width: Optional[int] = None
    ) -> Tuple[bool, str]:
        """Convert image to specified format"""
        result = self._converter.convert(
            Path(input_path),
            Path(output_path),
            quality=quality,
            resize_width=resize_width
        )
        return result.success, result.message
    
    def batch_convert(
        self,
        input_files: List[str],
        output_format: str,
        output_dir: Optional[str] = None,
        quality: int = 85,
        resize_width: Optional[int] = None,
        delete_originals: bool = False,
        progress_callback: Optional[Callable] = None
    ) -> Dict[str, List]:
        """Convert multiple images"""
        return self._converter.batch_convert(
            [Path(f) for f in input_files],
            output_format=output_format,
            output_dir=Path(output_dir) if output_dir else None,
            quality=quality,
            resize_width=resize_width,
            delete_originals=delete_originals,
            progress_callback=progress_callback
        )
    
    @classmethod
    def get_supported_extensions(cls) -> str:
        """Get file dialog filter string"""
        extensions = ' '.join(f'*{ext}' for ext in cls.INPUT_FORMATS)
        return f"Image files ({extensions})"
