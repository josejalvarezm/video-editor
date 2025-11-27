"""
Video Processor Module
Handles video conversion to 1080p HD using FFmpeg
"""

import subprocess
import os
from pathlib import Path


def _get_subprocess_args():
    """Get platform-specific subprocess arguments for running without console"""
    kwargs = {
        'capture_output': True,
        'text': True,
        'timeout': 10,
        'stdin': subprocess.DEVNULL,  # Critical for windowless apps
    }
    if os.name == 'nt':
        # Windows: hide console window completely
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


class VideoProcessor:
    def __init__(self):
        self.ffmpeg_path = self._find_ffmpeg()
        self.gpu_encoder = self._detect_gpu_encoder()
        self.gpu_name = self._detect_gpu_name()
    
    def _find_ffmpeg(self):
        """Find FFmpeg executable - check PATH and common installation locations"""
        # Get user directories explicitly (more reliable than expandvars in frozen apps)
        user_home = os.path.expanduser("~")
        local_appdata = os.environ.get("LOCALAPPDATA", os.path.join(user_home, "AppData", "Local"))
        
        # Build list of paths to check (WinGet Links first - most reliable for WinGet installs)
        common_paths = [
            os.path.join(local_appdata, "Microsoft", "WinGet", "Links", "ffmpeg.exe"),  # WinGet symlink
            r"C:\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
            r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
            os.path.join(user_home, "scoop", "shims", "ffmpeg.exe"),
            r"C:\ProgramData\chocolatey\bin\ffmpeg.exe",
        ]
        
        # Dynamically search WinGet package locations (handles any FFmpeg version)
        winget_base = os.path.join(local_appdata, "Microsoft", "WinGet", "Packages")
        if os.path.exists(winget_base):
            try:
                for folder in os.listdir(winget_base):
                    if "ffmpeg" in folder.lower():
                        package_path = os.path.join(winget_base, folder)
                        for root, dirs, files in os.walk(package_path):
                            if "ffmpeg.exe" in files:
                                common_paths.append(os.path.join(root, "ffmpeg.exe"))
            except Exception:
                pass
        
        # Add "ffmpeg" (PATH lookup) at the end as fallback
        common_paths.append("ffmpeg")
        
        # Try each path - first check if file exists (for absolute paths)
        subprocess_args = _get_subprocess_args()
        for ffmpeg_path in common_paths:
            try:
                # Skip absolute paths that don't exist
                if ffmpeg_path != "ffmpeg" and not os.path.isfile(ffmpeg_path):
                    continue
                
                result = subprocess.run([ffmpeg_path, "-version"], **subprocess_args)
                if result.returncode == 0:
                    return ffmpeg_path
            except Exception:
                continue
        
        # Return default and let check_ffmpeg handle the error
        return "ffmpeg"
        
    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            subprocess_args = _get_subprocess_args()
            result = subprocess.run([self.ffmpeg_path, "-version"], **subprocess_args)
            return result.returncode == 0
        except Exception:
            return False
    
    def _detect_gpu_encoder(self):
        """Detect available GPU encoder (NVIDIA, AMD, Intel)"""
        try:
            subprocess_args = _get_subprocess_args()
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-encoders"],
                **subprocess_args
            )
            encoders = result.stdout.lower()
            
            # Check for NVIDIA NVENC (best quality/speed)
            if "h264_nvenc" in encoders or "hevc_nvenc" in encoders:
                return "nvenc"
            
            # Check for AMD AMF
            elif "h264_amf" in encoders:
                return "amf"
            
            # Check for Intel QuickSync
            elif "h264_qsv" in encoders:
                return "qsv"
            
            # Fallback to CPU
            return "cpu"
            
        except Exception:
            return "cpu"
    
    def _detect_gpu_name(self):
        """Detect GPU model name using platform-specific commands"""
        try:
            import platform
            import re
            
            system = platform.system()
            
            if system == "Windows":
                # Try NVIDIA CUDA/GPU detection
                try:
                    result = subprocess.run(
                        ["nvidia-smi", "-L"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0 and result.stdout:
                        # Parse output like "GPU 0: NVIDIA GeForce RTX 4090"
                        match = re.search(r":\s*(.+?)(?:\s*\(|$)", result.stdout.split('\n')[0])
                        if match:
                            return match.group(1).strip()
                except Exception:
                    pass
                
                # Try AMD GPU detection (AMD ADRENALIN)
                try:
                    result = subprocess.run(
                        ["wmic", "path", "win32_videocontroller", "get", "name"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if result.returncode == 0:
                        lines = [line.strip() for line in result.stdout.split('\n') if line.strip()]
                        if len(lines) > 1:
                            # First line is "Name", second line is the GPU
                            gpu_name = lines[1]
                            if gpu_name and gpu_name.lower() != "name":
                                return gpu_name
                except Exception:
                    pass
            
            elif system == "Darwin":  # macOS
                try:
                    result = subprocess.run(
                        ["system_profiler", "SPDisplaysDataType"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if "NVIDIA" in result.stdout:
                        match = re.search(r"NVIDIA\s+(\S+\s+\S+)", result.stdout)
                        if match:
                            return f"NVIDIA {match.group(1)}"
                    elif "AMD" in result.stdout:
                        match = re.search(r"AMD\s+(\S+\s+\S+)", result.stdout)
                        if match:
                            return f"AMD {match.group(1)}"
                except Exception:
                    pass
            
            elif system == "Linux":
                # Try lspci for NVIDIA/AMD detection
                try:
                    result = subprocess.run(
                        ["lspci"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if "NVIDIA" in result.stdout:
                        match = re.search(r"NVIDIA.*?:\s*(.+?)(?:\s*\(|$)", result.stdout)
                        if match:
                            return match.group(1).strip()
                    elif "AMD" in result.stdout:
                        match = re.search(r"AMD.*?:\s*(.+?)(?:\s*\(|$)", result.stdout)
                        if match:
                            return match.group(1).strip()
                except Exception:
                    pass
        
        except Exception:
            pass
        
        return None
    
    
    def has_hevc_encoder(self):
        """Check if H.265/HEVC encoder is available"""
        try:
            result = subprocess.run(
                [self.ffmpeg_path, "-hide_banner", "-encoders"],
                capture_output=True,
                text=True,
                timeout=5
            )
            encoders = result.stdout.lower()
            
            # Check for any HEVC encoder
            return ("hevc_nvenc" in encoders or 
                    "hevc_amf" in encoders or 
                    "hevc_qsv" in encoders or 
                    "libx265" in encoders)
        except Exception:
            return False
    
    def get_video_info(self, input_path):
        """Get video information using ffprobe"""
        try:
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                input_path
            ]
            result = subprocess.run(cmd, **_get_subprocess_args(), timeout=30)
            return result.stdout
        except Exception as e:
            print(f"Error getting video info: {e}")
            return None
    
    def convert_to_hd(self, input_path, output_path, resolution="1080p", trim_start=None, trim_end=None):
        """
        Convert video to HD resolution using FFmpeg
        
        Args:
            input_path: Path to input video file
            output_path: Path to output video file
            resolution: Target resolution ("1080p" or "720p")
            trim_start: Start time for trimming with millisecond precision
                       Formats: HH:MM:SS.mmm (e.g., "00:00:01.500" for 1.5 seconds)
                               or HH:MM:SS (e.g., "00:00:05")
            trim_end: End time for trimming with millisecond precision
                     Same format as trim_start, leave None for full length
        """
        
        # Check if FFmpeg is available
        if not self.check_ffmpeg():
            raise Exception("FFmpeg not found. Please install FFmpeg and add it to PATH.")
        
        # Determine target resolution (height only - width auto-calculated to preserve aspect ratio)
        if resolution == "8K" or resolution == "4320p":
            target_height = 4320
        elif resolution == "4K" or resolution == "2160p":
            target_height = 2160
        elif resolution == "1440p":
            target_height = 1440
        elif resolution == "1080p":
            target_height = 1080
        elif resolution == "720p":
            target_height = 720
        else:
            target_height = 1080  # Default to 1080p
        
        # Build FFmpeg command
        # Using MAXIMUM quality settings for upscaling
        cmd = [self.ffmpeg_path]
        
        # NVIDIA NVENC has 4096 height limit - force CPU for 8K
        use_gpu_encoder = self.gpu_encoder
        if self.gpu_encoder == "nvenc" and target_height > 4096:
            use_gpu_encoder = "cpu"  # Fallback to CPU for 8K
        
        # Add hardware acceleration BEFORE input (if using GPU)
        if use_gpu_encoder == "nvenc":
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        
        # Add trim/cut parameters if specified
        if trim_start:
            cmd.extend(["-ss", trim_start])  # Start time
        
        cmd.extend(["-i", input_path])
        
        if trim_end:
            cmd.extend(["-to", trim_end])  # End time
        
        # Add video processing parameters based on GPU availability
        if use_gpu_encoder == "nvenc":
            # NVIDIA NVENC - Hardware accelerated encoding
            cmd.extend([
                # GPU-accelerated scaling for better performance
                "-vf", f"scale_cuda=-2:{target_height},hwdownload,format=nv12,unsharp=5:5:1.0:5:5:0.0",
                "-c:v", "h264_nvenc",        # NVIDIA hardware encoder
                "-preset", "p7",             # p7 = highest quality preset for NVENC
                "-tune", "hq",               # High quality tuning
                "-rc", "vbr",                # Variable bitrate
                "-cq", "18",                 # Quality: 18 = visually lossless
                "-b:v", "0",                 # Let CQ control bitrate
                "-profile:v", "high",        # High profile
                "-level", "5.2",             # Level 5.2 supports 4K
                "-pix_fmt", "yuv420p",       # Pixel format for compatibility
                "-c:a", "aac",               # AAC audio codec
                "-b:a", "320k",              # High quality audio bitrate
                "-movflags", "+faststart",   # Enable streaming
                "-y",                        # Overwrite output file
                output_path
            ])
        elif use_gpu_encoder == "amf":
            # AMD AMF - Hardware accelerated encoding
            cmd.extend([
                "-vf", f"scale=-2:{target_height}:flags=lanczos:param0=3,unsharp=5:5:1.0:5:5:0.0",
                "-c:v", "h264_amf",          # AMD hardware encoder
                "-quality", "quality",       # Quality mode
                "-rc", "vbr_peak",           # Variable bitrate
                "-qp_i", "18",               # I-frame quality
                "-qp_p", "20",               # P-frame quality
                "-profile:v", "high",
                "-level", "5.2",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "320k",
                "-movflags", "+faststart",
                "-y",
                output_path
            ])
        elif use_gpu_encoder == "qsv":
            # Intel QuickSync - Hardware accelerated encoding
            cmd.extend([
                "-vf", f"scale=-2:{target_height}:flags=lanczos:param0=3,unsharp=5:5:1.0:5:5:0.0",
                "-c:v", "h264_qsv",          # Intel hardware encoder
                "-preset", "veryslow",       # Quality preset
                "-global_quality", "18",     # Quality
                "-profile:v", "high",
                "-level", "5.2",
                "-pix_fmt", "yuv420p",
                "-c:a", "aac",
                "-b:a", "320k",
                "-movflags", "+faststart",
                "-y",
                output_path
            ])
        else:
            # CPU fallback - Software encoding (slower but compatible)
            # Use HEVC (H.265) for 8K, H.264 for lower resolutions
            if target_height >= 4320:
                # 8K: Use HEVC for better compression
                cmd.extend([
                    "-vf", f"scale=-2:{target_height}:flags=lanczos:param0=3,unsharp=5:5:1.0:5:5:0.0",
                    "-c:v", "libx265",           # H.265/HEVC video codec (better for 8K)
                    "-preset", "medium",         # Balanced preset (veryslow takes too long for 8K)
                    "-crf", "18",                # Quality: 18 = high quality for HEVC
                    "-pix_fmt", "yuv420p",       # Pixel format for compatibility
                    "-tag:v", "hvc1",            # Apple compatibility tag
                    "-c:a", "aac",               # AAC audio codec
                    "-b:a", "320k",              # High quality audio bitrate
                    "-movflags", "+faststart",   # Enable streaming
                    "-y",                        # Overwrite output file
                    output_path
                ])
            else:
                # 4K and below: Use H.264
                cmd.extend([
                    "-vf", f"scale=-2:{target_height}:flags=lanczos:param0=3,unsharp=5:5:1.0:5:5:0.0",
                    "-c:v", "libx264",           # H.264 video codec
                    "-preset", "veryslow",       # Maximum quality preset (slowest)
                    "-crf", "15",                # Quality: 15 = near-lossless (lower = better)
                    "-profile:v", "high",        # High profile for best quality
                    "-level", "5.2",             # Level 5.2 supports 4K
                    "-pix_fmt", "yuv420p",       # Pixel format for compatibility
                    "-c:a", "aac",               # AAC audio codec
                    "-b:a", "320k",              # High quality audio bitrate
                    "-movflags", "+faststart",   # Enable streaming
                    "-y",                        # Overwrite output file
                    output_path
                ])
        
        try:
            # Setup for windowless operation
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'stdin': subprocess.DEVNULL,
                'universal_newlines': True,
            }
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                popen_kwargs['startupinfo'] = startupinfo
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            # Run FFmpeg
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            # Wait for completion
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr}")
            
            return True
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("FFmpeg processing timed out")
        except Exception as e:
            raise Exception(f"Failed to convert video: {str(e)}")
    
    def compress_video(self, input_path, output_path, codec="h264", quality="balanced", audio_codec="aac128"):
        """Compress video with specified codec and quality settings
        
        Args:
            input_path: Path to input video file
            output_path: Path to output video file
            codec: 'h264' or 'h265' (HEVC)
            quality: 'high', 'balanced', or 'max' compression
            audio_codec: 'aac128', 'aac96', or 'copy'
        """
        
        # Quality presets for CRF (Constant Rate Factor)
        # Lower CRF = higher quality, larger file
        # Higher CRF = lower quality, smaller file
        quality_presets = {
            "high": {"h264": 18, "h265": 20},      # High quality
            "balanced": {"h264": 23, "h265": 24},  # Balanced
            "max": {"h264": 28, "h265": 28}        # Maximum compression
        }
        
        crf_value = quality_presets[quality][codec]
        
        # Build FFmpeg command
        cmd = [self.ffmpeg_path]
        
        # Add hardware acceleration if available
        if self.gpu_encoder == "nvenc":
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        
        cmd.extend(["-i", input_path])
        
        # Video codec selection
        if codec == "h265":
            if self.gpu_encoder == "nvenc":
                cmd.extend([
                    "-c:v", "hevc_nvenc",
                    "-preset", "p7",  # High quality preset
                    "-rc", "vbr",
                    "-cq", str(crf_value),
                    "-b:v", "0"  # Variable bitrate
                ])
            elif self.gpu_encoder == "amf":
                cmd.extend([
                    "-c:v", "hevc_amf",
                    "-quality", "quality",
                    "-rc", "cqp",
                    "-qp_i", str(crf_value),
                    "-qp_p", str(crf_value)
                ])
            elif self.gpu_encoder == "qsv":
                cmd.extend([
                    "-c:v", "hevc_qsv",
                    "-global_quality", str(crf_value),
                    "-look_ahead", "1"
                ])
            else:
                # CPU encoding with libx265
                cmd.extend([
                    "-c:v", "libx265",
                    "-crf", str(crf_value),
                    "-preset", "medium",
                    "-x265-params", "log-level=error"
                ])
        else:  # h264
            if self.gpu_encoder == "nvenc":
                cmd.extend([
                    "-c:v", "h264_nvenc",
                    "-preset", "p7",
                    "-rc", "vbr",
                    "-cq", str(crf_value),
                    "-b:v", "0"
                ])
            elif self.gpu_encoder == "amf":
                cmd.extend([
                    "-c:v", "h264_amf",
                    "-quality", "quality",
                    "-rc", "cqp",
                    "-qp_i", str(crf_value),
                    "-qp_p", str(crf_value)
                ])
            elif self.gpu_encoder == "qsv":
                cmd.extend([
                    "-c:v", "h264_qsv",
                    "-global_quality", str(crf_value),
                    "-look_ahead", "1"
                ])
            else:
                # CPU encoding with libx264
                cmd.extend([
                    "-c:v", "libx264",
                    "-crf", str(crf_value),
                    "-preset", "medium"
                ])
        
        # Audio codec selection
        if audio_codec == "copy":
            cmd.extend(["-c:a", "copy"])
        elif audio_codec == "aac128":
            cmd.extend(["-c:a", "aac", "-b:a", "128k"])
        elif audio_codec == "aac96":
            cmd.extend(["-c:a", "aac", "-b:a", "96k"])
        
        # Output file
        cmd.extend(["-y", output_path])
        
        try:
            # Setup for windowless operation
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'stdin': subprocess.DEVNULL,
                'universal_newlines': True,
            }
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                popen_kwargs['startupinfo'] = startupinfo
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            # Run FFmpeg
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr}")
            
            return True
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("FFmpeg compression timed out")
        except Exception as e:
            raise Exception(f"Failed to compress video: {str(e)}")
    
    def trim_video_lossless(self, input_path, output_path, trim_start=None, trim_end=None):
        """Trim video without re-encoding (lossless, fast, no quality loss)
        
        Args:
            input_path: Path to input video file
            output_path: Path to output video file
            trim_start: Start time in HH:MM:SS.mmm format
            trim_end: End time in HH:MM:SS.mmm format (optional)
        """
        
        # Build FFmpeg command for stream copy (no re-encoding)
        cmd = [self.ffmpeg_path]
        
        # Add start time if specified
        if trim_start:
            cmd.extend(["-ss", trim_start])
        
        cmd.extend(["-i", input_path])
        
        # Add end time if specified
        if trim_end:
            cmd.extend(["-to", trim_end])
        
        # Stream copy mode - no re-encoding (lossless and fast)
        cmd.extend([
            "-c", "copy",           # Copy all streams without re-encoding
            "-avoid_negative_ts", "make_zero",  # Fix timestamp issues
            "-y",                   # Overwrite output file
            output_path
        ])
        
        try:
            # Setup for windowless operation
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'stdin': subprocess.DEVNULL,
                'universal_newlines': True,
            }
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                popen_kwargs['startupinfo'] = startupinfo
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            # Run FFmpeg
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            stdout, stderr = process.communicate()
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr}")
            
            return True
            
        except subprocess.TimeoutExpired:
            process.kill()
            raise Exception("FFmpeg trimming timed out")
        except Exception as e:
            raise Exception(f"Failed to trim video: {str(e)}")
    
    def check_video_compatibility(self, video_paths):
        """Check if videos are compatible for lossless joining
        
        Returns: (bool, str) - (is_compatible, message)
        """
        if len(video_paths) < 2:
            return False, "Need at least 2 videos"
        
        try:
            # Get info for first video as reference
            ref_info = self.get_video_info(video_paths[0])
            if not ref_info:
                return False, "Could not read first video info"
            
            ref_video = next((s for s in ref_info.get('streams', []) if s['codec_type'] == 'video'), None)
            if not ref_video:
                return False, "No video stream in first file"
            
            ref_codec = ref_video.get('codec_name')
            ref_width = ref_video.get('width')
            ref_height = ref_video.get('height')
            ref_fps = eval(ref_video.get('r_frame_rate', '0/1'))  # e.g., "30/1" -> 30.0
            
            # Check all other videos
            for video_path in video_paths[1:]:
                info = self.get_video_info(video_path)
                if not info:
                    return False, f"Could not read info from {os.path.basename(video_path)}"
                
                video_stream = next((s for s in info.get('streams', []) if s['codec_type'] == 'video'), None)
                if not video_stream:
                    return False, f"No video stream in {os.path.basename(video_path)}"
                
                codec = video_stream.get('codec_name')
                width = video_stream.get('width')
                height = video_stream.get('height')
                fps = eval(video_stream.get('r_frame_rate', '0/1'))
                
                # Check codec
                if codec != ref_codec:
                    return False, f"Codec mismatch: {ref_codec} vs {codec}. All videos must use the same codec."
                
                # Check resolution
                if width != ref_width or height != ref_height:
                    return False, f"Resolution mismatch: {ref_width}x{ref_height} vs {width}x{height}. All videos must have the same resolution."
                
                # Check FPS (allow small tolerance)
                if abs(fps - ref_fps) > 0.1:
                    return False, f"FPS mismatch: {ref_fps} vs {fps}. All videos must have the same frame rate."
            
            return True, f"All {len(video_paths)} videos compatible ({ref_codec}, {ref_width}x{ref_height}, {ref_fps:.2f}fps)"
            
        except Exception as e:
            return False, f"Error checking compatibility: {str(e)}"
    
    def join_videos_concat(self, video_paths, output_path):
        """Join videos using concat demuxer (lossless, fast)
        
        Args:
            video_paths: List of video file paths in order to join
            output_path: Path to output video file
        """
        import tempfile
        
        try:
            # Create temporary file list for FFmpeg concat demuxer
            with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt', encoding='utf-8') as f:
                filelist_path = f.name
                for video_path in video_paths:
                    # Use absolute paths and escape for FFmpeg
                    abs_path = os.path.abspath(video_path).replace('\\', '/')
                    f.write(f"file '{abs_path}'\n")
            
            # Build FFmpeg command using concat demuxer
            cmd = [
                self.ffmpeg_path,
                "-f", "concat",
                "-safe", "0",
                "-i", filelist_path,
                "-c", "copy",  # Stream copy (no re-encoding, lossless)
                "-y",  # Overwrite output file
                output_path
            ]
            
            # Setup for windowless operation
            popen_kwargs = {
                'stdout': subprocess.PIPE,
                'stderr': subprocess.PIPE,
                'stdin': subprocess.DEVNULL,
                'universal_newlines': True,
            }
            if os.name == 'nt':
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = subprocess.SW_HIDE
                popen_kwargs['startupinfo'] = startupinfo
                popen_kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
            
            # Run FFmpeg
            process = subprocess.Popen(cmd, **popen_kwargs)
            
            stdout, stderr = process.communicate()
            
            # Clean up temp file
            try:
                os.unlink(filelist_path)
            except:
                pass
            
            if process.returncode != 0:
                raise Exception(f"FFmpeg error: {stderr}")
            
            return True
            
        except Exception as e:
            # Try to clean up temp file
            try:
                if 'filelist_path' in locals():
                    os.unlink(filelist_path)
            except:
                pass
            raise Exception(f"Failed to join videos: {str(e)}")
    
    def get_supported_formats(self):
        """Return list of supported video formats"""
        return [".mp4", ".avi", ".mov", ".mkv", ".flv", ".wmv", ".webm", ".m4v"]
    
    def extract_thumbnail(self, input_path, output_path, timestamp="00:00:01", width=None, height=None):
        """
        Extract a thumbnail from video at specified timestamp
        
        Args:
            input_path: Path to input video file
            output_path: Path to output thumbnail image (jpg/png)
            timestamp: Time to extract frame from (default: 1 second)
            width: Thumbnail width in pixels (None to maintain aspect ratio)
            height: Thumbnail height in pixels (None to maintain aspect ratio)
        
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            cmd = [
                self.ffmpeg_path,
                "-ss", timestamp,           # Seek to timestamp
                "-i", input_path,           # Input video
                "-vframes", "1",            # Extract 1 frame
            ]
            
            # Only add size parameter if specified
            if width is not None and height is not None:
                cmd.extend(["-s", f"{width}x{height}"])  # Resize to thumbnail size
            elif width is not None:
                cmd.extend(["-vf", f"scale={width}:-1"])  # Scale width, maintain aspect ratio
            elif height is not None:
                cmd.extend(["-vf", f"scale=-1:{height}"])  # Scale height, maintain aspect ratio
            # If both None, extract at original resolution
            
            cmd.extend([
                "-q:v", "2",                # High quality (1-31, lower is better)
                "-y",                       # Overwrite output file
                output_path
            ])
            
            result = subprocess.run(cmd, **_get_subprocess_args(), timeout=10)
            
            return result.returncode == 0
            
        except Exception as e:
            print(f"Error extracting thumbnail: {e}")
            return False
    
    def get_detailed_video_info(self, input_path):
        """
        Get detailed video information including duration, resolution, codec, fps
        
        Args:
            input_path: Path to input video file
        
        Returns:
            dict: Video information or None if failed
                {
                    'duration': '00:05:23',
                    'duration_seconds': 323.5,
                    'resolution': '1920x1080',
                    'width': 1920,
                    'height': 1080,
                    'codec': 'h264',
                    'fps': '30.00',
                    'bitrate': '5000 kb/s',
                    'size': '150.5 MB'
                }
        """
        try:
            import json
            
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-print_format", "json",
                "-show_streams",
                "-show_format",
                input_path
            ]
            
            result = subprocess.run(cmd, **_get_subprocess_args(), timeout=30)
            
            if result.returncode != 0:
                return None
            
            data = json.loads(result.stdout)
            
            # Find video stream
            video_stream = None
            for stream in data.get('streams', []):
                if stream.get('codec_type') == 'video':
                    video_stream = stream
                    break
            
            if not video_stream:
                return None
            
            # Extract information
            info = {}
            
            # Duration
            duration_sec = float(data.get('format', {}).get('duration', 0))
            hours = int(duration_sec // 3600)
            minutes = int((duration_sec % 3600) // 60)
            seconds = int(duration_sec % 60)
            info['duration'] = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            info['duration_seconds'] = duration_sec
            
            # Resolution
            width = video_stream.get('width', 0)
            height = video_stream.get('height', 0)
            info['width'] = width
            info['height'] = height
            info['resolution'] = f"{width}x{height}"
            
            # Codec
            info['codec'] = video_stream.get('codec_name', 'unknown')
            
            # FPS (frame rate)
            fps_str = video_stream.get('r_frame_rate', '0/1')
            if '/' in fps_str:
                num, den = fps_str.split('/')
                fps = float(num) / float(den) if float(den) != 0 else 0
            else:
                fps = float(fps_str)
            info['fps'] = f"{fps:.2f}"
            
            # Bitrate
            bitrate = int(data.get('format', {}).get('bit_rate', 0))
            info['bitrate'] = f"{bitrate // 1000} kb/s" if bitrate > 0 else "unknown"
            
            # File size
            size_bytes = int(data.get('format', {}).get('size', 0))
            if size_bytes > 1024 * 1024 * 1024:
                info['size'] = f"{size_bytes / (1024**3):.1f} GB"
            elif size_bytes > 1024 * 1024:
                info['size'] = f"{size_bytes / (1024**2):.1f} MB"
            elif size_bytes > 1024:
                info['size'] = f"{size_bytes / 1024:.1f} KB"
            else:
                info['size'] = f"{size_bytes} B"
            
            return info
            
        except Exception as e:
            print(f"Error getting detailed video info: {e}")
            return None


# Test functionality
if __name__ == "__main__":
    processor = VideoProcessor()
    
    if processor.check_ffmpeg():
        print("✓ FFmpeg is available")
    else:
        print("✗ FFmpeg not found. Please install FFmpeg.")
