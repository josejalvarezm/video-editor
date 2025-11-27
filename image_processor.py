"""
Image Processor Module
Handles image conversion and compression using ImageMagick
"""

import subprocess
import os
from pathlib import Path


def _get_subprocess_args():
    """Get platform-specific subprocess arguments for running without console"""
    kwargs = {
        'capture_output': True,
        'text': True,
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


class ImageProcessor:
    # Supported input formats
    INPUT_FORMATS = ['.jxr', '.hdp', '.wdp', '.jpg', '.jpeg', '.png', '.bmp', '.tiff', '.tif', '.webp', '.gif', '.heic', '.heif']
    
    # Supported output formats
    OUTPUT_FORMATS = {
        'JPG': '.jpg',
        'PNG': '.png', 
        'WebP': '.webp',
        'BMP': '.bmp',
        'TIFF': '.tiff'
    }
    
    # Resize presets (width in pixels, None = original)
    RESIZE_PRESETS = {
        'Original': None,
        '1920px (Full HD)': 1920,
        '1280px (HD)': 1280,
        '800px (Web)': 800,
        '640px (Thumbnail)': 640,
        'Custom': 'custom'
    }

    def __init__(self):
        self.magick_path = None
        self._find_imagemagick()

    def _find_imagemagick(self):
        """Find ImageMagick installation"""
        # Common ImageMagick locations
        search_paths = [
            # Standard Windows installations
            r"C:\Program Files\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
            r"C:\Program Files\ImageMagick-7.1.1-Q16\magick.exe",
            r"C:\Program Files (x86)\ImageMagick-7.1.1-Q16-HDRI\magick.exe",
            # Generic version patterns
            r"C:\Program Files\ImageMagick*\magick.exe",
        ]
        
        # Check PATH first
        try:
            result = subprocess.run(['magick', '-version'], **_get_subprocess_args())
            if result.returncode == 0:
                self.magick_path = 'magick'
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
        
        # Check common installation paths
        for path in search_paths:
            if '*' in path:
                # Glob pattern
                import glob
                matches = glob.glob(path)
                for match in matches:
                    if os.path.isfile(match):
                        try:
                            result = subprocess.run([match, '-version'], **_get_subprocess_args())
                            if result.returncode == 0:
                                self.magick_path = match
                                return True
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            pass
            elif os.path.isfile(path):
                try:
                    result = subprocess.run([path, '-version'], **_get_subprocess_args())
                    if result.returncode == 0:
                        self.magick_path = path
                        return True
                except (FileNotFoundError, subprocess.TimeoutExpired):
                    pass
        
        # Check Program Files directories for any ImageMagick
        program_dirs = [
            os.environ.get('ProgramFiles', r'C:\Program Files'),
            os.environ.get('ProgramFiles(x86)', r'C:\Program Files (x86)'),
            os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs'),
        ]
        
        for prog_dir in program_dirs:
            if not prog_dir or not os.path.isdir(prog_dir):
                continue
            for folder in os.listdir(prog_dir):
                if folder.lower().startswith('imagemagick'):
                    magick_exe = os.path.join(prog_dir, folder, 'magick.exe')
                    if os.path.isfile(magick_exe):
                        try:
                            result = subprocess.run([magick_exe, '-version'], **_get_subprocess_args())
                            if result.returncode == 0:
                                self.magick_path = magick_exe
                                return True
                        except (FileNotFoundError, subprocess.TimeoutExpired):
                            pass
        
        return False

    def is_available(self):
        """Check if ImageMagick is available"""
        return self.magick_path is not None

    def get_version(self):
        """Get ImageMagick version string"""
        if not self.magick_path:
            return None
        try:
            result = subprocess.run([self.magick_path, '-version'], **_get_subprocess_args())
            if result.returncode == 0:
                # Extract version from first line
                first_line = result.stdout.split('\n')[0]
                return first_line
            return None
        except Exception:
            return None

    def get_image_info(self, input_path):
        """Get image information (dimensions, format, size)"""
        if not self.magick_path:
            return None
        
        try:
            cmd = [
                self.magick_path, 'identify',
                '-format', '%w|%h|%m|%B',
                input_path
            ]
            result = subprocess.run(cmd, **_get_subprocess_args(), timeout=30)
            
            if result.returncode == 0:
                parts = result.stdout.strip().split('|')
                if len(parts) >= 4:
                    return {
                        'width': int(parts[0]),
                        'height': int(parts[1]),
                        'format': parts[2],
                        'size_bytes': int(parts[3])
                    }
            return None
        except Exception as e:
            print(f"Error getting image info: {e}")
            return None

    def convert_image(self, input_path, output_path, quality=85, resize_width=None):
        """
        Convert image to specified format with optional quality and resize
        
        Args:
            input_path: Path to input image
            output_path: Path to output image (extension determines format)
            quality: Quality percentage (1-100) for lossy formats
            resize_width: Target width in pixels (maintains aspect ratio), None for original
            
        Returns:
            tuple: (success: bool, message: str)
        """
        if not self.magick_path:
            return False, "ImageMagick not found"
        
        try:
            input_ext = Path(input_path).suffix.lower()
            
            # Check if input is JXR - requires special handling
            if input_ext in ['.jxr', '.hdp', '.wdp']:
                return self._convert_jxr(input_path, output_path, quality, resize_width)
            
            # Use 'magick' directly (not 'magick convert' which is deprecated in v7)
            cmd = [self.magick_path, input_path]
            
            # Add resize if specified
            if resize_width:
                cmd.extend(['-resize', f'{resize_width}x>'])  # Only shrink, don't enlarge
            
            # Add quality for lossy formats
            output_ext = Path(output_path).suffix.lower()
            if output_ext in ['.jpg', '.jpeg', '.webp']:
                cmd.extend(['-quality', str(quality)])
            
            # Strip metadata to reduce size
            cmd.append('-strip')
            
            # Output path
            cmd.append(output_path)
            
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
            
            # Run ImageMagick
            process = subprocess.Popen(cmd, **popen_kwargs)
            stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
            
            if process.returncode == 0:
                return True, "Conversion successful"
            else:
                return False, f"ImageMagick error: {stderr}"
                
        except subprocess.TimeoutExpired:
            process.kill()
            return False, "Conversion timed out"
        except Exception as e:
            return False, f"Failed to convert image: {str(e)}"
    
    def _convert_jxr(self, input_path, output_path, quality=85, resize_width=None):
        """
        Convert JXR/HDP/WDP files using Windows built-in codecs via PowerShell
        Since ImageMagick doesn't have native JXR support, we use .NET/WIC
        
        Returns:
            tuple: (success: bool, message: str)
        """
        try:
            import tempfile
            
            # First, convert JXR to PNG using PowerShell and Windows Imaging Component
            temp_png = tempfile.mktemp(suffix='.png')
            
            # PowerShell script to decode JXR using Windows.Graphics.Imaging (WIC)
            ps_script = f'''
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName PresentationCore

try {{
    $inputPath = "{input_path.replace(chr(92), chr(92)+chr(92))}"
    $outputPath = "{temp_png.replace(chr(92), chr(92)+chr(92))}"
    
    # Use WPF's BitmapDecoder which supports JPEG XR
    $stream = [System.IO.File]::OpenRead($inputPath)
    $decoder = [System.Windows.Media.Imaging.BitmapDecoder]::Create(
        $stream,
        [System.Windows.Media.Imaging.BitmapCreateOptions]::PreservePixelFormat,
        [System.Windows.Media.Imaging.BitmapCacheOption]::Default
    )
    
    $frame = $decoder.Frames[0]
    
    # Encode to PNG
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
            
            # Run PowerShell to decode JXR
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
            
            process = subprocess.Popen(
                ['powershell', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', ps_script],
                **popen_kwargs
            )
            stdout, stderr = process.communicate(timeout=120)
            
            if 'SUCCESS' not in stdout:
                # Clean up temp file if exists
                try:
                    os.remove(temp_png)
                except:
                    pass
                error_msg = stdout.strip() if stdout else stderr.strip()
                return False, f"JXR decode failed: {error_msg}"
            
            # Now convert the temp PNG to final format using ImageMagick
            cmd = [self.magick_path, temp_png]
            
            if resize_width:
                cmd.extend(['-resize', f'{resize_width}x>'])
            
            output_ext = Path(output_path).suffix.lower()
            if output_ext in ['.jpg', '.jpeg', '.webp']:
                cmd.extend(['-quality', str(quality)])
            
            cmd.append('-strip')
            cmd.append(output_path)
            
            process = subprocess.Popen(cmd, **popen_kwargs)
            stdout, stderr = process.communicate(timeout=300)
            
            # Clean up temp file
            try:
                os.remove(temp_png)
            except:
                pass
            
            if process.returncode == 0:
                return True, "Conversion successful (via Windows codec)"
            else:
                return False, f"ImageMagick error: {stderr}"
                
        except Exception as e:
            return False, f"JXR conversion failed: {str(e)}"

    def batch_convert(self, input_files, output_format, output_dir=None, quality=85, 
                      resize_width=None, delete_originals=False, progress_callback=None):
        """
        Convert multiple images
        
        Args:
            input_files: List of input file paths
            output_format: Output format key (e.g., 'JPG', 'PNG', 'WebP')
            output_dir: Output directory (None = same as input)
            quality: Quality percentage for lossy formats
            resize_width: Target width in pixels (None = original)
            delete_originals: Whether to delete original files after successful conversion
            progress_callback: Optional callback(current, total, filename) for progress
            
        Returns:
            dict: Results with 'success', 'failed', 'messages'
        """
        results = {
            'success': [],
            'failed': [],
            'messages': []
        }
        
        output_ext = self.OUTPUT_FORMATS.get(output_format, '.jpg')
        total = len(input_files)
        
        for idx, input_path in enumerate(input_files):
            if progress_callback:
                progress_callback(idx + 1, total, os.path.basename(input_path))
            
            # Determine output path
            input_file = Path(input_path)
            if output_dir:
                output_path = Path(output_dir) / (input_file.stem + output_ext)
            else:
                output_path = input_file.parent / (input_file.stem + output_ext)
            
            # Handle name collision if input and output are same
            if str(output_path) == str(input_path):
                output_path = input_file.parent / (input_file.stem + '_converted' + output_ext)
            
            # Convert
            success, message = self.convert_image(
                str(input_path), 
                str(output_path), 
                quality=quality,
                resize_width=resize_width
            )
            
            if success:
                results['success'].append(str(output_path))
                results['messages'].append(f"✓ {input_file.name} → {output_path.name}")
                
                # Delete original if requested
                if delete_originals:
                    try:
                        os.remove(input_path)
                        results['messages'].append(f"  Deleted: {input_file.name}")
                    except Exception as e:
                        results['messages'].append(f"  Warning: Could not delete {input_file.name}: {e}")
            else:
                results['failed'].append(str(input_path))
                results['messages'].append(f"✗ {input_file.name}: {message}")
        
        return results

    @classmethod
    def get_supported_extensions(cls):
        """Get file dialog filter string for supported input formats"""
        extensions = ' '.join(f'*{ext}' for ext in cls.INPUT_FORMATS)
        return f"Image files ({extensions})"
