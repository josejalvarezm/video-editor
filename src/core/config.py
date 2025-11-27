"""
Configuration Management
Centralized settings with validation and environment support
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import json
import os


@dataclass
class VideoSettings:
    """Video processing default settings"""
    default_resolution: str = "1080p"
    default_codec: str = "h265"
    default_quality: str = "high"
    default_audio_codec: str = "aac"
    default_audio_bitrate: str = "96k"
    gpu_acceleration: bool = True
    
    
@dataclass
class UISettings:
    """User interface settings"""
    window_width: int = 1100
    window_height: int = 900
    theme: str = "clam"
    show_thumbnails: bool = False
    thumbnail_width: int = 80
    thumbnail_height: int = 45
    preview_width: int = 280
    preview_height: int = 158
    
    
@dataclass
class PathSettings:
    """File path configuration"""
    ffmpeg_path: str = "ffmpeg"
    ffprobe_path: str = "ffprobe"
    temp_dir: Optional[Path] = None
    default_output_dir: Optional[Path] = None
    
    def __post_init__(self):
        if self.temp_dir is None:
            import tempfile
            self.temp_dir = Path(tempfile.gettempdir()) / "video_editor_pro"
            self.temp_dir.mkdir(exist_ok=True)


@dataclass
class AppConfig:
    """Main application configuration"""
    video: VideoSettings = field(default_factory=VideoSettings)
    ui: UISettings = field(default_factory=UISettings)
    paths: PathSettings = field(default_factory=PathSettings)
    log_level: str = "INFO"
    log_file: Optional[Path] = None
    
    @classmethod
    def load_from_file(cls, config_path: Path) -> 'AppConfig':
        """Load configuration from JSON file"""
        if not config_path.exists():
            return cls()
            
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            return cls(
                video=VideoSettings(**data.get('video', {})),
                ui=UISettings(**data.get('ui', {})),
                paths=PathSettings(**data.get('paths', {})),
                log_level=data.get('log_level', 'INFO'),
                log_file=Path(data['log_file']) if data.get('log_file') else None
            )
        except Exception as e:
            print(f"Warning: Failed to load config from {config_path}: {e}")
            return cls()
    
    def save_to_file(self, config_path: Path) -> None:
        """Save configuration to JSON file"""
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'video': {
                'default_resolution': self.video.default_resolution,
                'default_codec': self.video.default_codec,
                'default_quality': self.video.default_quality,
                'default_audio_codec': self.video.default_audio_codec,
                'default_audio_bitrate': self.video.default_audio_bitrate,
                'gpu_acceleration': self.video.gpu_acceleration,
            },
            'ui': {
                'window_width': self.ui.window_width,
                'window_height': self.ui.window_height,
                'theme': self.ui.theme,
                'show_thumbnails': self.ui.show_thumbnails,
                'thumbnail_width': self.ui.thumbnail_width,
                'thumbnail_height': self.ui.thumbnail_height,
                'preview_width': self.ui.preview_width,
                'preview_height': self.ui.preview_height,
            },
            'paths': {
                'ffmpeg_path': self.paths.ffmpeg_path,
                'ffprobe_path': self.paths.ffprobe_path,
                'temp_dir': str(self.paths.temp_dir) if self.paths.temp_dir else None,
                'default_output_dir': str(self.paths.default_output_dir) if self.paths.default_output_dir else None,
            },
            'log_level': self.log_level,
            'log_file': str(self.log_file) if self.log_file else None,
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
    
    @classmethod
    def get_default_config_path(cls) -> Path:
        """Get platform-specific config file path"""
        if os.name == 'nt':  # Windows
            base = Path(os.environ.get('APPDATA', Path.home()))
        else:  # Linux/Mac
            base = Path.home() / '.config'
        
        return base / 'VideoEditorPro' / 'config.json'


# Global configuration instance
_config: Optional[AppConfig] = None


def get_config() -> AppConfig:
    """Get global configuration instance (singleton pattern)"""
    global _config
    if _config is None:
        config_path = AppConfig.get_default_config_path()
        _config = AppConfig.load_from_file(config_path)
    return _config


def set_config(config: AppConfig) -> None:
    """Set global configuration instance"""
    global _config
    _config = config
