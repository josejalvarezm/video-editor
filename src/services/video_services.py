"""
FFmpeg-based Video Services
Concrete implementations of video processing interfaces
"""

import subprocess
import json
import tempfile
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

from ..core.exceptions import (
    VideoConversionError,
    VideoCompressionError,
    VideoTrimmingError,
    VideoJoiningError,
    VideoIncompatibleError,
    ThumbnailError,
    FFmpegNotFoundError,
    FFprobeNotFoundError,
    VideoProcessingError
)
from ..core.logger import get_logger
from .interfaces import (
    IVideoConverter,
    IVideoCompressor,
    IVideoTrimmer,
    IVideoJoiner,
    IVideoInfoExtractor,
    IThumbnailExtractor,
    IEncoderDetector,
    VideoInfo
)


logger = get_logger(__name__)


class FFmpegBase:
    """Base class for FFmpeg operations with common functionality"""
    
    def __init__(self, ffmpeg_path: str = "ffmpeg", ffprobe_path: str = "ffprobe"):
        self.ffmpeg_path = ffmpeg_path
        self.ffprobe_path = ffprobe_path
        self._validate_dependencies()
    
    def _validate_dependencies(self) -> None:
        """Validate FFmpeg and FFprobe are available"""
        try:
            subprocess.run(
                [self.ffmpeg_path, "-version"],
                capture_output=True,
                timeout=5,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"FFmpeg validation failed: {e}")
            raise FFmpegNotFoundError(str(e))
        
        try:
            subprocess.run(
                [self.ffprobe_path, "-version"],
                capture_output=True,
                timeout=5,
                check=True
            )
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
            logger.error(f"FFprobe validation failed: {e}")
            raise FFprobeNotFoundError(str(e))
    
    def _run_ffmpeg(self, args: List[str], timeout: int = 300) -> subprocess.CompletedProcess:
        """
        Run FFmpeg command with error handling
        
        Args:
            args: FFmpeg arguments
            timeout: Command timeout in seconds
            
        Returns:
            CompletedProcess instance
            
        Raises:
            VideoProcessingError: If command fails
        """
        cmd = [self.ffmpeg_path] + args
        logger.debug(f"Running FFmpeg: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                logger.error(f"FFmpeg failed: {result.stderr}")
                raise VideoProcessingError(
                    "FFmpeg command failed",
                    result.stderr
                )
            
            return result
            
        except subprocess.TimeoutExpired as e:
            logger.error(f"FFmpeg timeout: {e}")
            raise VideoProcessingError(
                f"Operation timed out after {timeout} seconds",
                str(e)
            )
        except Exception as e:
            logger.error(f"FFmpeg error: {e}")
            raise VideoProcessingError(
                "Unexpected error during video processing",
                str(e)
            )


class EncoderDetector(FFmpegBase, IEncoderDetector):
    """Hardware encoder detection service"""
    
    def detect_gpu_encoder(self) -> str:
        """Detect available GPU encoder"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            encoders = result.stdout.lower()
            
            if "h264_nvenc" in encoders or "hevc_nvenc" in encoders:
                logger.info("Detected NVIDIA NVENC encoder")
                return "nvenc"
            elif "h264_amf" in encoders:
                logger.info("Detected AMD AMF encoder")
                return "amf"
            elif "h264_qsv" in encoders:
                logger.info("Detected Intel QuickSync encoder")
                return "qsv"
            else:
                logger.info("No GPU encoder detected, using CPU")
                return "cpu"
                
        except Exception as e:
            logger.warning(f"Encoder detection failed: {e}")
            return "cpu"
    
    def has_hevc_encoder(self) -> bool:
        """Check if H.265/HEVC encoder is available"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            encoders = result.stdout.lower()
            
            has_hevc = any(enc in encoders for enc in [
                "hevc_nvenc", "hevc_amf", "hevc_qsv", "libx265"
            ])
            
            logger.debug(f"HEVC encoder available: {has_hevc}")
            return has_hevc
            
        except Exception as e:
            logger.warning(f"HEVC check failed: {e}")
            return False
    
    def check_ffmpeg_available(self) -> bool:
        """Check if FFmpeg is available"""
        try:
            self._validate_dependencies()
            return True
        except (FFmpegNotFoundError, FFprobeNotFoundError):
            return False


class VideoInfoExtractor(FFmpegBase, IVideoInfoExtractor):
    """Video metadata extraction service"""
    
    def get_raw_info(self, video_path: Path) -> str:
        """Get raw ffprobe JSON output"""
        logger.debug(f"Extracting info from: {video_path}")
        
        try:
            result = subprocess.run(
                [
                    self.ffprobe_path,
                    "-v", "quiet",
                    "-print_format", "json",
                    "-show_streams",
                    "-show_format",
                    str(video_path)
                ],
                capture_output=True,
                text=True,
                timeout=30,
                check=True
            )
            return result.stdout
            
        except Exception as e:
            logger.error(f"Failed to get video info: {e}")
            raise VideoProcessingError(
                f"Failed to extract video information from {video_path.name}",
                str(e)
            )
    
    def get_info(self, video_path: Path) -> VideoInfo:
        """Extract structured video metadata"""
        raw_info = self.get_raw_info(video_path)
        
        try:
            data = json.loads(raw_info)
            video_stream = next(
                (s for s in data.get('streams', []) if s.get('codec_type') == 'video'),
                None
            )
            
            if not video_stream:
                raise VideoProcessingError(f"No video stream found in {video_path.name}")
            
            format_data = data.get('format', {})
            
            # Parse duration
            duration_seconds = float(format_data.get('duration', 0))
            hours = int(duration_seconds // 3600)
            minutes = int((duration_seconds % 3600) // 60)
            seconds = int(duration_seconds % 60)
            duration_formatted = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            
            # Parse FPS from r_frame_rate
            fps_str = video_stream.get('r_frame_rate', '0/1')
            try:
                num, den = map(int, fps_str.split('/'))
                fps = round(num / den, 2) if den != 0 else 0.0
            except:
                fps = 0.0
            
            # Format file size
            size_bytes = int(format_data.get('size', 0))
            if size_bytes >= 1_000_000_000:
                size = f"{size_bytes / 1_000_000_000:.2f} GB"
            elif size_bytes >= 1_000_000:
                size = f"{size_bytes / 1_000_000:.2f} MB"
            elif size_bytes >= 1_000:
                size = f"{size_bytes / 1_000:.2f} KB"
            else:
                size = f"{size_bytes} B"
            
            # Format bitrate
            bitrate_bps = int(format_data.get('bit_rate', 0))
            bitrate = f"{bitrate_bps // 1000} kb/s" if bitrate_bps > 0 else "N/A"
            
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            
            return VideoInfo(
                duration=duration_formatted,
                duration_seconds=duration_seconds,
                resolution=f"{width}x{height}",
                width=width,
                height=height,
                codec=video_stream.get('codec_name', 'unknown'),
                fps=fps,
                bitrate=bitrate,
                size=size
            )
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse video info JSON: {e}")
            raise VideoProcessingError(
                "Failed to parse video information",
                str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error parsing video info: {e}")
            raise VideoProcessingError(
                "Failed to extract video metadata",
                str(e)
            )


class ThumbnailExtractor(FFmpegBase, IThumbnailExtractor):
    """Video thumbnail extraction service"""
    
    def extract_thumbnail(
        self,
        video_path: Path,
        output_path: Path,
        timestamp: str = "00:00:01",
        width: Optional[int] = None,
        height: Optional[int] = None
    ) -> None:
        """Extract thumbnail frame from video"""
        logger.debug(f"Extracting thumbnail from {video_path} at {timestamp}")
        
        args = [
            "-ss", timestamp,
            "-i", str(video_path),
            "-frames:v", "1",
            "-q:v", "2",
        ]
        
        # Add scaling if specified
        if width and height:
            args.extend(["-s", f"{width}x{height}"])
        elif width:
            args.extend(["-vf", f"scale={width}:-1"])
        elif height:
            args.extend(["-vf", f"scale=-1:{height}"])
        
        args.extend(["-y", str(output_path)])
        
        try:
            self._run_ffmpeg(args, timeout=30)
            logger.debug(f"Thumbnail saved to {output_path}")
            
        except VideoProcessingError as e:
            logger.error(f"Thumbnail extraction failed: {e}")
            raise ThumbnailError(
                f"Failed to extract thumbnail from {video_path.name}",
                e.details
            )


class VideoConverter(FFmpegBase, IVideoConverter):
    """Video conversion and upscaling service"""
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        encoder_detector: Optional[IEncoderDetector] = None
    ):
        super().__init__(ffmpeg_path, ffprobe_path)
        self.encoder_detector = encoder_detector or EncoderDetector(ffmpeg_path, ffprobe_path)
        self.gpu_encoder = self.encoder_detector.detect_gpu_encoder()
    
    def convert_to_resolution(
        self,
        input_path: Path,
        output_path: Path,
        resolution: str,
        **kwargs
    ) -> None:
        """Convert video to specified resolution"""
        logger.info(f"Converting {input_path.name} to {resolution}")
        
        # Parse resolution
        resolution_map = {
            "720p": (1280, 720),
            "1080p": (1920, 1080),
            "1440p": (2560, 1440),
            "4k": (3840, 2160),
        }
        
        if resolution not in resolution_map:
            raise VideoConversionError(
                f"Invalid resolution: {resolution}",
                f"Supported resolutions: {', '.join(resolution_map.keys())}"
            )
        
        width, height = resolution_map[resolution]
        
        # Build FFmpeg command
        args = []
        
        # GPU acceleration
        if self.gpu_encoder == "nvenc":
            args.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        
        args.extend([
            "-i", str(input_path),
            "-vf", f"scale={width}:{height}:flags=lanczos",
            "-c:v", self._get_encoder(),
            "-preset", "slow",
            "-crf", "18",
            "-c:a", "copy",
            "-y", str(output_path)
        ])
        
        try:
            self._run_ffmpeg(args)
            logger.info(f"Conversion complete: {output_path.name}")
            
        except VideoProcessingError as e:
            logger.error(f"Conversion failed: {e}")
            raise VideoConversionError(
                f"Failed to convert {input_path.name} to {resolution}",
                e.details
            )
    
    def _get_encoder(self) -> str:
        """Get appropriate video encoder"""
        if self.gpu_encoder == "nvenc":
            return "h264_nvenc"
        elif self.gpu_encoder == "amf":
            return "h264_amf"
        elif self.gpu_encoder == "qsv":
            return "h264_qsv"
        else:
            return "libx264"


class VideoCompressor(FFmpegBase, IVideoCompressor):
    """Video compression service"""
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        encoder_detector: Optional[IEncoderDetector] = None
    ):
        super().__init__(ffmpeg_path, ffprobe_path)
        self.encoder_detector = encoder_detector or EncoderDetector(ffmpeg_path, ffprobe_path)
        self.gpu_encoder = self.encoder_detector.detect_gpu_encoder()
    
    def compress(
        self,
        input_path: Path,
        output_path: Path,
        codec: str,
        quality: str,
        audio_codec: Optional[str] = None,
        **kwargs
    ) -> None:
        """Compress video with specified codec and quality"""
        logger.info(f"Compressing {input_path.name} with {codec} at {quality} quality")
        
        # Quality to CRF mapping
        quality_map = {
            "high": ("18", "20"),
            "balanced": ("23", "24"),
            "max": ("28", "28"),
        }
        
        if quality not in quality_map:
            raise VideoCompressionError(
                f"Invalid quality: {quality}",
                f"Supported qualities: {', '.join(quality_map.keys())}"
            )
        
        crf_h264, crf_h265 = quality_map[quality]
        
        # Select encoder
        if codec == "h265":
            if not self.encoder_detector.has_hevc_encoder():
                raise VideoCompressionError(
                    "H.265/HEVC encoder not available",
                    "Install FFmpeg with HEVC support or use H.264"
                )
            encoder = self._get_hevc_encoder()
            crf = crf_h265
        else:
            encoder = self._get_h264_encoder()
            crf = crf_h264
        
        # Build command
        args = []
        
        if self.gpu_encoder == "nvenc":
            args.extend(["-hwaccel", "cuda"])
        
        args.extend([
            "-i", str(input_path),
            "-c:v", encoder,
            "-crf", crf,
            "-preset", "slow",
        ])
        
        # Audio handling
        if audio_codec == "copy":
            args.extend(["-c:a", "copy"])
        elif audio_codec:
            bitrate = kwargs.get("audio_bitrate", "96k")
            args.extend(["-c:a", "aac", "-b:a", bitrate])
        
        args.extend(["-y", str(output_path)])
        
        try:
            self._run_ffmpeg(args)
            logger.info(f"Compression complete: {output_path.name}")
            
        except VideoProcessingError as e:
            logger.error(f"Compression failed: {e}")
            raise VideoCompressionError(
                f"Failed to compress {input_path.name}",
                e.details
            )
    
    def _get_h264_encoder(self) -> str:
        """Get H.264 encoder"""
        if self.gpu_encoder == "nvenc":
            return "h264_nvenc"
        elif self.gpu_encoder == "amf":
            return "h264_amf"
        elif self.gpu_encoder == "qsv":
            return "h264_qsv"
        else:
            return "libx264"
    
    def _get_hevc_encoder(self) -> str:
        """Get H.265/HEVC encoder"""
        if self.gpu_encoder == "nvenc":
            return "hevc_nvenc"
        elif self.gpu_encoder == "amf":
            return "hevc_amf"
        elif self.gpu_encoder == "qsv":
            return "hevc_qsv"
        else:
            return "libx265"


class VideoTrimmer(FFmpegBase, IVideoTrimmer):
    """Video trimming service"""
    
    def trim(
        self,
        input_path: Path,
        output_path: Path,
        start_time: str,
        end_time: str,
        lossless: bool = True
    ) -> None:
        """Trim video to specified time range"""
        logger.info(f"Trimming {input_path.name} from {start_time} to {end_time}")
        
        args = [
            "-ss", start_time,
            "-to", end_time,
            "-i", str(input_path),
        ]
        
        if lossless:
            args.extend(["-c", "copy"])
        else:
            args.extend(["-c:v", "libx264", "-c:a", "aac"])
        
        args.extend(["-y", str(output_path)])
        
        try:
            self._run_ffmpeg(args)
            logger.info(f"Trimming complete: {output_path.name}")
            
        except VideoProcessingError as e:
            logger.error(f"Trimming failed: {e}")
            raise VideoTrimmingError(
                f"Failed to trim {input_path.name}",
                e.details
            )


class VideoJoiner(FFmpegBase, IVideoJoiner):
    """Video joining/concatenation service"""
    
    def __init__(
        self,
        ffmpeg_path: str = "ffmpeg",
        ffprobe_path: str = "ffprobe",
        info_extractor: Optional[IVideoInfoExtractor] = None
    ):
        super().__init__(ffmpeg_path, ffprobe_path)
        self.info_extractor = info_extractor or VideoInfoExtractor(ffmpeg_path, ffprobe_path)
    
    def check_compatibility(self, video_paths: List[Path]) -> Tuple[bool, str]:
        """Check if videos can be joined losslessly"""
        if len(video_paths) < 2:
            return False, "Need at least 2 videos to join"
        
        try:
            # Get info for all videos
            infos = [self.info_extractor.get_info(path) for path in video_paths]
            
            # Check codec
            codecs = {info.codec for info in infos}
            if len(codecs) > 1:
                return False, f"Mixed codecs: {', '.join(codecs)}"
            
            # Check resolution
            resolutions = {info.resolution for info in infos}
            if len(resolutions) > 1:
                return False, f"Mixed resolutions: {', '.join(resolutions)}"
            
            # Check FPS
            fps_values = {info.fps for info in infos}
            if len(fps_values) > 1:
                return False, f"Mixed frame rates: {', '.join(map(str, fps_values))}"
            
            return True, "All videos compatible"
            
        except Exception as e:
            logger.error(f"Compatibility check failed: {e}")
            return False, f"Error checking compatibility: {str(e)}"
    
    def join(
        self,
        input_paths: List[Path],
        output_path: Path,
        lossless: bool = True
    ) -> None:
        """Join multiple videos into single file"""
        logger.info(f"Joining {len(input_paths)} videos")
        
        # Check compatibility if lossless
        if lossless:
            compatible, message = self.check_compatibility(input_paths)
            if not compatible:
                raise VideoIncompatibleError(message)
        
        # Create temporary file list for concat
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='.txt',
            delete=False,
            encoding='utf-8'
        ) as f:
            for path in input_paths:
                f.write(f"file '{path.absolute()}'\n")
            filelist_path = f.name
        
        try:
            args = [
                "-f", "concat",
                "-safe", "0",
                "-i", filelist_path,
            ]
            
            if lossless:
                args.extend(["-c", "copy"])
            else:
                args.extend(["-c:v", "libx264", "-c:a", "aac"])
            
            args.extend(["-y", str(output_path)])
            
            self._run_ffmpeg(args)
            logger.info(f"Joining complete: {output_path.name}")
            
        except VideoProcessingError as e:
            logger.error(f"Joining failed: {e}")
            raise VideoJoiningError(
                f"Failed to join {len(input_paths)} videos",
                e.details
            )
        finally:
            # Clean up temp file
            try:
                Path(filelist_path).unlink()
            except:
                pass
