"""
ImageMagick-based Image Services
Concrete implementations of image processing interfaces
"""

import subprocess
import os
import glob
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Callable

from ..core.exceptions import (
    ImageProcessingError,
    ImageConversionError,
    ImageMagickNotFoundError,
    UnsupportedImageFormatError
)
from ..core.logger import get_logger
from .interfaces import (
    IImageConverter,
    IImageInfoExtractor,
    IImageMagickDetector,
    ImageInfo,
    ImageConversionResult
)


logger = get_logger(__name__)


def _get_subprocess_args() -> dict:
    """Get platform-specific subprocess arguments for running without console"""
    kwargs = {
        'capture_output': True,
        'text': True,
        'stdin': subprocess.DEVNULL,
    }
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


def _get_popen_kwargs() -> dict:
    """Get platform-specific Popen arguments for long-running processes"""
    kwargs = {
        'stdout': subprocess.PIPE,
        'stderr': subprocess.PIPE,
        'stdin': subprocess.DEVNULL,
        'universal_newlines': True,
    }
    if os.name == 'nt':
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
        startupinfo.wShowWindow = subprocess.SW_HIDE
        kwargs['startupinfo'] = startupinfo
        kwargs['creationflags'] = subprocess.CREATE_NO_WINDOW
    return kwargs


class ImageMagickDetector(IImageMagickDetector):
    """ImageMagick detection and validation service"""
    
    # Common installation paths for Windows
    SEARCH_PATHS = [
        r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
        r"C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe",
        r"C:\Program Files (x86)\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
        r"C:\Program Files\ImageMagick*\magick.exe",
    ]
    
    def __init__(self):
        self._magick_path: Optional[str] = None
        self._version: Optional[str] = None
        self._detect_imagemagick()
    
    def _detect_imagemagick(self) -> None:
        """Find ImageMagick installation"""
        # Check PATH first
        try:
            result = subprocess.run(['magick', '-version'], **_get_subprocess_args())
            if result.returncode == 0:
                self._magick_path = 'magick'
                self._version = result.stdout.split('\n')[0] if result.stdout else None
                logger.info(f"Found ImageMagick in PATH: {self._version}")
                return
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check common installation paths
        for path in self.SEARCH_PATHS:
            if '*' in path:
                matches = glob.glob(path)
                for match in matches:
                    if self._try_magick_path(match):
                        return
            elif os.path.isfile(path):
                if self._try_magick_path(path):
                    return
        
        # Check Program Files directories
        program_dirs = [
            os.environ.get('ProgramFiles', r'C:\Program Files'),
            os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
        ]
        
        for prog_dir in program_dirs:
            if not prog_dir or not os.path.isdir(prog_dir):
                continue
            try:
                for folder in os.listdir(prog_dir):
                    if folder.lower().startswith('imagemagick'):
                        magick_exe = os.path.join(prog_dir, folder, 'magick.exe')
                        if os.path.isfile(magick_exe):
                            if self._try_magick_path(magick_exe):
                                return
            except PermissionError:
                continue
        
        logger.warning("ImageMagick not found")
    
    def _try_magick_path(self, path: str) -> bool:
        """Try a potential ImageMagick path"""
        try:
            result = subprocess.run([path, '-version'], **_get_subprocess_args())
            if result.returncode == 0:
                self._magick_path = path
                self._version = result.stdout.split('\n')[0] if result.stdout else None
                logger.info(f"Found ImageMagick at: {path}")
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        return False
    
    def is_available(self) -> bool:
        """Check if ImageMagick is available"""
        return self._magick_path is not None
    
    def get_version(self) -> Optional[str]:
        """Get ImageMagick version string"""
        return self._version
    
    def get_executable_path(self) -> Optional[str]:
        """Get path to ImageMagick executable"""
        return self._magick_path


class ImageInfoExtractor(IImageInfoExtractor):
    """Image metadata extraction service"""
    
    SUPPORTED_FORMATS = [
        '.jxr', '.hdp', '.wdp', '.jpg', '.jpeg', '.png', 
        '.bmp', '.tiff', '.tif', '.webp', '.gif', '.heic', '.heif'
    ]
    
    def __init__(self, magick_detector: IImageMagickDetector):
        self._detector = magick_detector
    
    def get_info(self, image_path: Path) -> ImageInfo:
        """Extract image metadata"""
        if not self._detector.is_available():
            raise ImageMagickNotFoundError()
        
        magick_path = self._detector.get_executable_path()
        logger.debug(f"Extracting info from: {image_path}")
        
        try:
            cmd = [
                magick_path, 'identify',
                '-format', '%w|%h|%m|%B',
                str(image_path)
            ]
            result = subprocess.run(cmd, **_get_subprocess_args(), timeout=30)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                if len(parts) >= 4:
                    return ImageInfo(
                        width=int(parts[0]),
                        height=int(parts[1]),
                        format=parts[2],
                        size_bytes=int(parts[3])
                    )
            
            raise ImageProcessingError(
                f"Failed to extract image info from {image_path.name}",
                result.stderr
            )
            
        except subprocess.TimeoutExpired:
            raise ImageProcessingError(
                "Image info extraction timed out",
                f"File: {image_path}"
            )
        except Exception as e:
            logger.error(f"Error getting image info: {e}")
            raise ImageProcessingError(
                f"Failed to extract image info from {image_path.name}",
                str(e)
            )
    
    def is_supported(self, file_path: Path) -> bool:
        """Check if file format is supported"""
        return file_path.suffix.lower() in self.SUPPORTED_FORMATS


class ImageConverter(IImageConverter):
    """Image format conversion service"""
    
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
    
    def __init__(self, magick_detector: IImageMagickDetector):
        self._detector = magick_detector
    
    @property
    def supported_input_formats(self) -> List[str]:
        """List of supported input file extensions"""
        return self.INPUT_FORMATS.copy()
    
    @property
    def supported_output_formats(self) -> Dict[str, str]:
        """Dict of output format name to extension"""
        return self.OUTPUT_FORMATS.copy()
    
    def convert(
        self,
        input_path: Path,
        output_path: Path,
        quality: int = 85,
        resize_width: Optional[int] = None
    ) -> ImageConversionResult:
        """Convert image to specified format"""
        if not self._detector.is_available():
            return ImageConversionResult(
                success=False,
                message="ImageMagick not found",
                input_path=input_path
            )
        
        magick_path = self._detector.get_executable_path()
        input_ext = input_path.suffix.lower()
        
        logger.debug(f"Converting {input_path} to {output_path}")
        
        try:
            # JXR requires special handling
            if input_ext in ['.jxr', '.hdp', '.wdp']:
                return self._convert_jxr(input_path, output_path, quality, resize_width)
            
            # Standard ImageMagick conversion
            cmd = [magick_path, str(input_path)]
            
            if resize_width:
                cmd.extend(['-resize', f'{resize_width}x>'])
            
            output_ext = output_path.suffix.lower()
            if output_ext in ['.jpg', '.jpeg', '.webp']:
                cmd.extend(['-quality', str(quality)])
            
            cmd.append('-strip')
            cmd.append(str(output_path))
            
            process = subprocess.Popen(cmd, **_get_popen_kwargs())
            stdout, stderr = process.communicate(timeout=300)
            
            if process.returncode == 0:
                logger.info(f"Conversion successful: {output_path.name}")
                return ImageConversionResult(
                    success=True,
                    message="Conversion successful",
                    input_path=input_path,
                    output_path=output_path
                )
            else:
                logger.error(f"ImageMagick error: {stderr}")
                return ImageConversionResult(
                    success=False,
                    message=f"ImageMagick error: {stderr}",
                    input_path=input_path
                )
                
        except subprocess.TimeoutExpired:
            process.kill()
            return ImageConversionResult(
                success=False,
                message="Conversion timed out",
                input_path=input_path
            )
        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            return ImageConversionResult(
                success=False,
                message=f"Failed to convert image: {str(e)}",
                input_path=input_path
            )
    
    def _convert_jxr(
        self,
        input_path: Path,
        output_path: Path,
        quality: int = 85,
        resize_width: Optional[int] = None
    ) -> ImageConversionResult:
        """Convert JXR files using Windows WIC codec"""
        magick_path = self._detector.get_executable_path()
        
        try:
            temp_png = tempfile.mktemp(suffix='.png')
            
            # PowerShell script for WIC-based JXR decoding
            ps_script = f'''
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName PresentationCore

try {{
    $inputPath = "{str(input_path).replace(chr(92), chr(92)+chr(92))}"
    $outputPath = "{temp_png.replace(chr(92), chr(92)+chr(92))}"
    
    $stream = [System.IO.File]::OpenRead($inputPath)
    $decoder = [System.Windows.Media.Imaging.BitmapDecoder]::Create(
        $stream,
        [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat,
        [System.Windows.Media.Imaging.BitmapCacheOption]::Default
    )
    
    $frame = $decoder.Frames[0]
    
    $encoder = New-Object System.Windows.Media.Imaging.PngBitmapEncoder
    $encoder.Frames.Add([System.Windows.Media.Imaging.BitmapFrame]::Create($frame))
    
    $outStream = [System.IO.File]::Create($outputPath)
    $encoder.Save($outStream)
    $outStream.Close()
    $stream.Close()
    
    Write-Output "SUCCESS"
}} catch {{
    Write-Output "ERROR: $($_.Exception.Message)"
}}
'''
            
            process = subprocess.Popen(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                **_get_popen_kwargs()
            )
            stdout, stderr = process.communicate(timeout=120)
            
            if 'SUCCESS' not in stdout:
                try:
                    os.remove(temp_png)
                except:
                    pass
                error_msg = stdout.strip() if stdout else stderr.strip()
                return ImageConversionResult(
                    success=False,
                    message=f"JXR decode failed: {error_msg}",
                    input_path=input_path
                )
            
            # Convert temp PNG to final format
            cmd = [magick_path, temp_png]
            
            if resize_width:
                cmd.extend(['-resize', f'{resize_width}x>'])
            
            output_ext = output_path.suffix.lower()
            if output_ext in ['.jpg', '.jpeg', '.webp']:
                cmd.extend(['-quality', str(quality)])
            
            cmd.append('-strip')
            cmd.append(str(output_path))
            
            process = subprocess.Popen(cmd, **_get_popen_kwargs())
            stdout, stderr = process.communicate(timeout=300)
            
            try:
                os.remove(temp_png)
            except:
                pass
            
            if process.returncode == 0:
                logger.info(f"JXR conversion successful: {output_path.name}")
                return ImageConversionResult(
                    success=True,
                    message="Conversion successful (via Windows codec)",
                    input_path=input_path,
                    output_path=output_path
                )
            else:
                return ImageConversionResult(
                    success=False,
                    message=f"ImageMagick error: {stderr}",
                    input_path=input_path
                )
                
        except Exception as e:
            logger.error(f"JXR conversion failed: {e}")
            return ImageConversionResult(
                success=False,
                message=f"JXR conversion failed: {str(e)}",
                input_path=input_path
            )
    
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
        """Convert multiple images"""
        results = {
            'success': [],
            'failed': [],
            'messages': []
        }
        
        output_ext = self.OUTPUT_FORMATS.get(output_format, '.jpg')
        total = len(input_files)
        
        for idx, input_path in enumerate(input_files):
            input_path = Path(input_path)
            
            if progress_callback:
                progress_callback(idx + 1, total, input_path.name)
            
            # Determine output path
            if output_dir:
                out_path = Path(output_dir) / (input_path.stem + output_ext)
            else:
                out_path = input_path.parent / (input_path.stem + output_ext)
            
            # Handle name collision
            if str(out_path) == str(input_path):
                out_path = input_path.parent / (input_path.stem + '_converted' + output_ext)
            
            result = self.convert(
                input_path,
                out_path,
                quality=quality,
                resize_width=resize_width
            )
            
            if result.success:
                results['success'].append(str(out_path))
                results['messages'].append(f"✓ {input_path.name} → {out_path.name}")
                
                if delete_originals:
                    try:
                        os.remove(input_path)
                        results['messages'].append(f"  Deleted: {input_path.name}")
                    except Exception as e:
                        results['messages'].append(f"  Warning: Could not delete {input_path.name}: {e}")
            else:
                results['failed'].append(str(input_path))
                results['messages'].append(f"✗ {input_path.name}: {result.message}")
        
        return results
    
    @classmethod
    def get_file_filter(cls) -> str:
        """Get file dialog filter string for supported input formats"""
        extensions = ' '.join(f'*{ext}' for ext in cls.INPUT_FORMATS)
        return f"Image files ({extensions})"
