"""
Video Upscaler Pro - Main GUI Application
Desktop app for batch video processing, compression, and trimming
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import os
import sys
from pathlib import Path
import threading
from typing import Optional, Protocol, runtime_checkable
from PIL import Image, ImageTk
import tempfile


# =============================================================================
# Protocols for Dependency Injection (following Interface Segregation Principle)
# =============================================================================

@runtime_checkable
class VideoProcessorProtocol(Protocol):
    """Protocol defining required video processor interface"""
    gpu_encoder: str
    gpu_name: str
    
    def check_ffmpeg(self) -> bool: ...
    def has_hevc_encoder(self) -> bool: ...
    def get_detailed_video_info(self, video_path: str) -> Optional[dict]: ...
    def extract_thumbnail(self, video_path: str, output_path: str, 
                         timestamp: str, width: int, height: int) -> bool: ...
    def convert_to_hd(self, input_path: str, output_path: str, **kwargs) -> bool: ...
    def compress_video(self, input_path: str, output_path: str, **kwargs) -> bool: ...
    def trim_video_lossless(self, input_path: str, output_path: str,
                           start_time: str, end_time: str, **kwargs) -> bool: ...
    def check_video_compatibility(self, video_paths: list) -> tuple: ...
    def join_videos_concat(self, video_paths: list, output_path: str, **kwargs) -> bool: ...


@runtime_checkable
class ImageProcessorProtocol(Protocol):
    """Protocol defining required image processor interface"""
    INPUT_FORMATS: list
    OUTPUT_FORMATS: dict
    RESIZE_PRESETS: dict
    
    def is_available(self) -> bool: ...
    def batch_convert(self, input_files: list, output_format: str, **kwargs) -> dict: ...


class VideoUpscalerApp:
    """
    Main application class following Single Responsibility Principle.
    Coordinates UI components and delegates processing to injected services.
    """
    
    def __init__(
        self,
        root: tk.Tk,
        video_processor: Optional[VideoProcessorProtocol] = None,
        image_processor: Optional[ImageProcessorProtocol] = None
    ):
        """
        Initialize the application with optional dependency injection.
        
        Args:
            root: Tkinter root window
            video_processor: Video processing service (optional, created if None)
            image_processor: Image processing service (optional, created if None)
        """
        self.root = root
        self.root.title("Video Editor Pro - GPU Accelerated")
        self.root.geometry("1100x1300")
        self.root.resizable(True, True)
        # Set minimum window size to prevent buttons from being hidden
        self.root.minsize(1100, 1300)
        
        # Center window on screen
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = 1100
        window_height = 1300
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Apply modern ttk theme
        self.style = ttk.Style()
        # Try to use modern themes (clam, alt, default, classic)
        available_themes = self.style.theme_names()
        if 'clam' in available_themes:
            self.style.theme_use('clam')
        elif 'alt' in available_themes:
            self.style.theme_use('alt')
        
        # Configure custom styles
        self.configure_styles()
        
        # Configure root background
        self.root.configure(bg='#f0f0f0')
        
        # Initialize processors (Dependency Injection with fallback)
        if video_processor is not None:
            self.video_processor = video_processor
        else:
            # Fallback to legacy processor for backward compatibility
            from video_processor import VideoProcessor
            self.video_processor = VideoProcessor()
        
        if image_processor is not None:
            self.image_processor = image_processor
        else:
            # Fallback to legacy processor for backward compatibility
            from image_processor import ImageProcessor
            self.image_processor = ImageProcessor()
        
        # Video list storage
        self.video_files = []
        self.selected_videos = {}
        
        # Thumbnail storage
        self.thumbnails = {}  # video_path -> PhotoImage
        self.temp_dir = tempfile.mkdtemp()  # Temporary directory for thumbnails
        
        # Selected video for preview
        self.current_preview_video = None
        
        # Thumbnail enable/disable flag
        self.thumbnails_enabled = tk.BooleanVar(value=False)  # Disabled by default
        
        # Setup UI
        self.setup_ui()
    
    def configure_styles(self):
        """Configure custom ttk styles for modern look"""
        # Notebook (tabs) styling
        self.style.configure('TNotebook', background='#f0f0f0', borderwidth=0)
        self.style.configure('TNotebook.Tab', padding=[20, 10], font=('Segoe UI', 10))
        
        # Button styling
        self.style.configure('Primary.TButton', font=('Segoe UI', 10, 'bold'), padding=10)
        self.style.configure('Success.TButton', font=('Segoe UI', 10), padding=8)
        self.style.configure('Danger.TButton', font=('Segoe UI', 10), padding=8)
        
        # LabelFrame styling
        self.style.configure('TLabelframe', background='#f0f0f0', borderwidth=2, relief='groove')
        self.style.configure('TLabelframe.Label', font=('Segoe UI', 10, 'bold'), foreground='#333333')
        
        # Frame styling
        self.style.configure('TFrame', background='#f0f0f0')
        
        # Label styling
        self.style.configure('TLabel', background='#f0f0f0', font=('Segoe UI', 9))
        self.style.configure('Title.TLabel', font=('Segoe UI', 20, 'bold'), foreground='#2c3e50')
        self.style.configure('Subtitle.TLabel', font=('Segoe UI', 10), foreground='#555555')
        self.style.configure('Success.TLabel', foreground='#27ae60', font=('Segoe UI', 10, 'bold'))
        self.style.configure('Warning.TLabel', foreground='#e67e22', font=('Segoe UI', 10, 'bold'))
        
        # Progressbar styling
        self.style.configure('TProgressbar', thickness=25, troughcolor='#e0e0e0', background='#3498db')
        
        # Radiobutton styling
        self.style.configure('TRadiobutton', background='#f0f0f0', font=('Segoe UI', 9))
        
        # Checkbutton styling
        self.style.configure('TCheckbutton', background='#f0f0f0', font=('Segoe UI', 9))
        
    def setup_ui(self):
        """Create the main user interface"""
        
        # Header Frame with gradient-like effect
        header_frame = ttk.Frame(self.root, style='TFrame')
        header_frame.pack(fill="x", padx=15, pady=(15, 10))
        
        # Title Label
        title_label = ttk.Label(
            header_frame, 
            text="🎬 Video Editor Pro", 
            style='Title.TLabel'
        )
        title_label.pack()
        
        # GPU Status Label
        gpu_encoder = self.video_processor.gpu_encoder
        gpu_name = self.video_processor.gpu_name
        
        encoder_info = {
            "nvenc": "🚀 NVIDIA GPU Acceleration (NVENC)",
            "amf": "🚀 AMD GPU Acceleration (AMF)",
            "qsv": "🚀 Intel GPU Acceleration (QuickSync)",
            "cpu": "⚙️ CPU Encoding Mode"
        }
        
        # Build GPU status text with detected GPU name
        if gpu_name:
            gpu_status_text = f"✓ Detected: {gpu_name} - {encoder_info.get(gpu_encoder, 'CPU Encoding')}"
        else:
            gpu_status_text = encoder_info.get(gpu_encoder, "⚙️ CPU Encoding")
        
        gpu_status_label = ttk.Label(
            header_frame,
            text=gpu_status_text,
            style='Success.TLabel' if gpu_encoder != "cpu" else 'Warning.TLabel'
        )
        gpu_status_label.pack(pady=(5, 0))
        
        # Separator
        separator = ttk.Separator(self.root, orient='horizontal')
        separator.pack(fill='x', padx=15, pady=10)
        
        # Create Notebook (Tabbed Interface)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=(0, 10), side="top")
        
        # Create tabs with ttk.Frame
        self.upscale_tab = ttk.Frame(self.notebook, style='TFrame')
        self.compress_tab = ttk.Frame(self.notebook, style='TFrame')
        self.trim_tab = ttk.Frame(self.notebook, style='TFrame')
        self.join_tab = ttk.Frame(self.notebook, style='TFrame')
        self.image_tab = ttk.Frame(self.notebook, style='TFrame')
        
        self.notebook.add(self.upscale_tab, text="  ⬆️ Upscale  ")
        self.notebook.add(self.compress_tab, text="  📦 Compress  ")
        self.notebook.add(self.trim_tab, text="  ✂️ Trim  ")
        self.notebook.add(self.join_tab, text="  🔗 Join  ")
        self.notebook.add(self.image_tab, text="  🖼️ Image  ")
        
        # Setup each tab
        self.setup_upscale_tab()
        self.setup_compress_tab()
        self.setup_trim_tab()
        self.setup_join_tab()
        self.setup_image_tab()
        
    def setup_upscale_tab(self):
        """Setup the upscale/convert tab"""
        
        # File Selection Frame
        file_frame = ttk.LabelFrame(self.upscale_tab, text="📁 Video Selection", padding=15)
        file_frame.pack(fill="both", expand=False, padx=15, pady=10)
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill="x")
        
        self.btn_add_files = ttk.Button(
            btn_frame, 
            text="➕ Add Videos", 
            command=self.add_videos,
            style='Success.TButton'
        )
        self.btn_add_files.pack(side="left", padx=(0, 10))
        
        self.btn_clear = ttk.Button(
            btn_frame, 
            text="🗑️ Clear All", 
            command=self.clear_videos,
            style='Danger.TButton'
        )
        self.btn_clear.pack(side="left")
        
        # Thumbnail toggle checkbox
        ttk.Checkbutton(
            btn_frame,
            text="🖼️ Show Thumbnails",
            variable=self.thumbnails_enabled,
            command=self.refresh_video_list
        ).pack(side="left", padx=(20, 0))
        
        # Main content area with video list and preview panel
        content_frame = ttk.Frame(self.upscale_tab)
        content_frame.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Video List Frame with Checkboxes (Left side - 65% width)
        list_frame = ttk.LabelFrame(content_frame, text="📋 Selected Videos", padding=10)
        list_frame.pack(side="left", fill="both", expand=True, padx=(0, 10))
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Canvas for checkboxes
        self.canvas = tk.Canvas(list_frame, yscrollcommand=scrollbar.set, bg='white', 
                                highlightthickness=0, borderwidth=0)
        self.canvas.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.canvas.yview)
        
        # Frame inside canvas
        self.video_list_frame = ttk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.video_list_frame, anchor="nw")
        
        # Preview Panel (Right side - 35% width)
        self.preview_frame = ttk.LabelFrame(content_frame, text="🎬 Preview", padding=15)
        self.preview_frame.pack(side="right", fill="both", padx=0)
        self.preview_frame.config(width=300)
        
        # Preview image container (fixed size)
        preview_img_container = tk.Frame(self.preview_frame, width=280, height=158, bg='#e0e0e0', 
                                         relief='solid', borderwidth=1)
        preview_img_container.pack(pady=(0, 15))
        preview_img_container.pack_propagate(False)  # Maintain size
        
        # Preview image label
        self.preview_image_label = tk.Label(preview_img_container, text="No video selected", 
                                            bg='#e0e0e0', fg='#666666', font=('Segoe UI', 10))
        self.preview_image_label.pack(expand=True)
        
        # Video info labels
        info_container = ttk.Frame(self.preview_frame)
        info_container.pack(fill="x")
        
        self.preview_filename_label = ttk.Label(info_container, text="", font=('Segoe UI', 9, 'bold'),
                                                wraplength=280, justify="left")
        self.preview_filename_label.pack(anchor="w", pady=(0, 8))
        
        ttk.Separator(info_container, orient='horizontal').pack(fill='x', pady=5)
        
        self.preview_resolution_label = ttk.Label(info_container, text="Resolution: -", 
                                                  font=('Segoe UI', 9))
        self.preview_resolution_label.pack(anchor="w", pady=2)
        
        self.preview_fps_label = ttk.Label(info_container, text="Frame Rate: -", 
                                           font=('Segoe UI', 9))
        self.preview_fps_label.pack(anchor="w", pady=2)
        
        self.preview_duration_label = ttk.Label(info_container, text="Duration: -", 
                                                font=('Segoe UI', 9))
        self.preview_duration_label.pack(anchor="w", pady=2)
        
        self.preview_codec_label = ttk.Label(info_container, text="Codec: -", 
                                             font=('Segoe UI', 9))
        self.preview_codec_label.pack(anchor="w", pady=2)
        
        self.preview_bitrate_label = ttk.Label(info_container, text="Bitrate: -", 
                                               font=('Segoe UI', 9))
        self.preview_bitrate_label.pack(anchor="w", pady=2)
        
        self.preview_size_label = ttk.Label(info_container, text="Size: -", 
                                            font=('Segoe UI', 9))
        self.preview_size_label.pack(anchor="w", pady=2)
        
        # Processing Options Frame
        options_frame = ttk.LabelFrame(self.upscale_tab, text="⚙️ Processing Options", padding=15)
        options_frame.pack(fill="x", padx=15, pady=10)
        
        # Resolution option
        res_frame = ttk.Frame(options_frame)
        res_frame.pack(fill="x", pady=8)
        ttk.Label(res_frame, text="Target Resolution:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 15))
        self.resolution_var = tk.StringVar(value="1440p")
        ttk.Radiobutton(res_frame, text="8K (7680x4320)", variable=self.resolution_var, value="8K").pack(side="left", padx=8)
        ttk.Radiobutton(res_frame, text="4K (3840x2160)", variable=self.resolution_var, value="4K").pack(side="left", padx=8)
        ttk.Radiobutton(res_frame, text="1440p (2560x1440)", variable=self.resolution_var, value="1440p").pack(side="left", padx=8)
        ttk.Radiobutton(res_frame, text="1080p (1920x1080)", variable=self.resolution_var, value="1080p").pack(side="left", padx=8)
        ttk.Radiobutton(res_frame, text="720p (1280x720)", variable=self.resolution_var, value="720p").pack(side="left", padx=8)
        
        # Video Editing Frame (Trim/Cut)
        edit_frame = ttk.LabelFrame(self.upscale_tab, text="✂️ Video Editing (Optional)", padding=15)
        edit_frame.pack(fill="x", padx=15, pady=10)
        
        # Enable trim checkbox
        self.enable_trim = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            edit_frame,
            text="Enable Trim/Cut",
            variable=self.enable_trim,
            command=self.toggle_trim_options
        ).pack(anchor="w", pady=(0, 10))
        
        # Trim options frame
        self.trim_frame = ttk.Frame(edit_frame)
        
        # Start time
        start_frame = ttk.Frame(self.trim_frame)
        start_frame.pack(fill="x", pady=5)
        ttk.Label(start_frame, text="Start Time:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.trim_start_var = tk.StringVar(value="00:00:00.500")
        ttk.Entry(start_frame, textvariable=self.trim_start_var, width=18, font=('Consolas', 9)).pack(side="left", padx=5)
        ttk.Label(start_frame, text="(HH:MM:SS.mmm, e.g., 00:00:01.500 = 1.5 sec)", foreground="gray").pack(side="left")
        
        # End time
        end_frame = ttk.Frame(self.trim_frame)
        end_frame.pack(fill="x", pady=5)
        ttk.Label(end_frame, text="End Time:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.trim_end_var = tk.StringVar(value="")
        ttk.Entry(end_frame, textvariable=self.trim_end_var, width=18, font=('Consolas', 9)).pack(side="left", padx=5)
        ttk.Label(end_frame, text="(HH:MM:SS.mmm or leave empty for full length)", foreground="gray").pack(side="left")
        
        # Show trim frame by default since trim is enabled
        self.trim_frame.pack(fill="x", pady=5)
        
        # Output folder selection
        ttk.Separator(options_frame, orient='horizontal').pack(fill='x', pady=15)
        output_frame = ttk.Frame(options_frame)
        output_frame.pack(fill="x", pady=5)
        ttk.Label(output_frame, text="Output Folder:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.output_path_var = tk.StringVar(value=str(Path.home() / "Videos" / "Upscaled"))
        ttk.Entry(output_frame, textvariable=self.output_path_var, width=55, font=('Segoe UI', 9)).pack(side="left", padx=5)
        ttk.Button(output_frame, text="📂 Browse", command=self.select_output_folder).pack(side="left", padx=5)
        
        # Progress Frame
        progress_frame = ttk.LabelFrame(self.upscale_tab, text="📊 Progress", padding=15)
        progress_frame.pack(fill="x", padx=15, pady=10)
        
        self.progress_label = ttk.Label(progress_frame, text="Ready to process videos", font=('Segoe UI', 9))
        self.progress_label.pack(fill="x", pady=(0, 8))
        
        self.progress_bar = ttk.Progressbar(progress_frame, mode="determinate", length=100)
        self.progress_bar.pack(fill="x")
        
        # Spacer frame to push button to bottom
        spacer = ttk.Frame(self.upscale_tab)
        spacer.pack(fill="both", expand=True)
        
        # Process Button Frame (fixed at bottom with minimum height)
        button_frame = ttk.Frame(self.upscale_tab, height=80)
        button_frame.pack(fill="x", padx=15, pady=15)
        button_frame.pack_propagate(False)
        
        self.btn_process = ttk.Button(
            button_frame,
            text="⬆️ Upscale Selected Videos (Maximum Quality)",
            command=self.start_processing,
            style='Primary.TButton'
        )
        self.btn_process.pack(pady=8, ipady=8, fill="x", expand=True)
    
    def setup_compress_tab(self):
        """Setup the compression tab"""
        
        # File Selection Frame
        file_frame_c = ttk.LabelFrame(self.compress_tab, text="📁 Video Selection", padding=15)
        file_frame_c.pack(fill="both", expand=False, padx=15, pady=10)
        
        btn_frame_c = ttk.Frame(file_frame_c)
        btn_frame_c.pack(fill="x")
        
        ttk.Button(
            btn_frame_c,
            text="➕ Add Videos",
            command=self.add_videos_compress,
            style='Success.TButton'
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            btn_frame_c,
            text="🗑️ Clear All",
            command=self.clear_videos_compress,
            style='Danger.TButton'
        ).pack(side="left")
        
        # Video List Frame
        list_frame_c = ttk.LabelFrame(self.compress_tab, text="📋 Selected Videos", padding=10)
        list_frame_c.pack(fill="both", expand=True, padx=15, pady=10)
        
        scrollbar_c = ttk.Scrollbar(list_frame_c)
        scrollbar_c.pack(side="right", fill="y")
        
        self.canvas_compress = tk.Canvas(list_frame_c, yscrollcommand=scrollbar_c.set, bg='white',
                                         highlightthickness=0, borderwidth=0)
        self.canvas_compress.pack(side="left", fill="both", expand=True)
        scrollbar_c.config(command=self.canvas_compress.yview)
        
        self.video_list_frame_compress = ttk.Frame(self.canvas_compress)
        self.canvas_compress.create_window((0, 0), window=self.video_list_frame_compress, anchor="nw")
        
        # Compression Options Frame
        comp_options = ttk.LabelFrame(self.compress_tab, text="⚙️ Compression Settings", padding=15)
        comp_options.pack(fill="x", padx=15, pady=10)
        
        # Codec selection
        codec_frame = ttk.Frame(comp_options)
        codec_frame.pack(fill="x", pady=8)
        ttk.Label(codec_frame, text="Video Codec:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 15))
        
        # Set default to h265 if available, otherwise h264
        default_codec = "h265" if self.video_processor.has_hevc_encoder() else "h264"
        self.codec_var = tk.StringVar(value=default_codec)
        
        ttk.Radiobutton(codec_frame, text="H.264 (AVC) - Best Compatibility", variable=self.codec_var, value="h264").pack(side="left", padx=8)
        
        # Check if H.265 is available
        if self.video_processor.has_hevc_encoder():
            ttk.Radiobutton(codec_frame, text="H.265 (HEVC) - Better Compression", variable=self.codec_var, value="h265").pack(side="left", padx=8)
        else:
            ttk.Label(codec_frame, text="(H.265 not available)", foreground="gray").pack(side="left", padx=8)
        
        # Compression quality
        quality_frame = ttk.Frame(comp_options)
        quality_frame.pack(fill="x", pady=8)
        ttk.Label(quality_frame, text="Compression Level:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 15))
        self.compress_quality = tk.StringVar(value="balanced")
        ttk.Radiobutton(quality_frame, text="High Quality (larger file)", variable=self.compress_quality, value="high").pack(side="left", padx=8)
        ttk.Radiobutton(quality_frame, text="Balanced", variable=self.compress_quality, value="balanced").pack(side="left", padx=8)
        ttk.Radiobutton(quality_frame, text="Maximum Compression (smaller file)", variable=self.compress_quality, value="max").pack(side="left", padx=8)
        
        # Audio transcoding
        audio_frame = ttk.Frame(comp_options)
        audio_frame.pack(fill="x", pady=8)
        ttk.Label(audio_frame, text="Audio Codec:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 15))
        self.audio_codec_var = tk.StringVar(value="aac96")
        ttk.Radiobutton(audio_frame, text="AAC 128kbps", variable=self.audio_codec_var, value="aac128").pack(side="left", padx=8)
        ttk.Radiobutton(audio_frame, text="AAC 96kbps", variable=self.audio_codec_var, value="aac96").pack(side="left", padx=8)
        ttk.Radiobutton(audio_frame, text="Copy (no transcode)", variable=self.audio_codec_var, value="copy").pack(side="left", padx=8)
        
        # Output folder
        ttk.Separator(comp_options, orient='horizontal').pack(fill='x', pady=15)
        output_frame_c = ttk.Frame(comp_options)
        output_frame_c.pack(fill="x", pady=5)
        ttk.Label(output_frame_c, text="Output Folder:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.output_path_compress = tk.StringVar(value=str(Path.home() / "Videos" / "Compressed"))
        ttk.Entry(output_frame_c, textvariable=self.output_path_compress, width=55, font=('Segoe UI', 9)).pack(side="left", padx=5)
        ttk.Button(output_frame_c, text="📂 Browse", command=self.select_output_folder_compress).pack(side="left", padx=5)
        
        # Progress Frame
        progress_frame_c = ttk.LabelFrame(self.compress_tab, text="📊 Progress", padding=15)
        progress_frame_c.pack(fill="x", padx=15, pady=10)
        
        self.progress_label_compress = ttk.Label(progress_frame_c, text="Ready to compress videos", font=('Segoe UI', 9))
        self.progress_label_compress.pack(fill="x", pady=(0, 8))
        
        self.progress_bar_compress = ttk.Progressbar(progress_frame_c, mode="determinate", length=100)
        self.progress_bar_compress.pack(fill="x")
        
        # Spacer frame to push button to bottom
        spacer_c = ttk.Frame(self.compress_tab)
        spacer_c.pack(fill="both", expand=True)
        
        # Compress Button Frame (fixed at bottom with minimum height)
        button_frame_c = ttk.Frame(self.compress_tab, height=80)
        button_frame_c.pack(fill="x", padx=15, pady=15)
        button_frame_c.pack_propagate(False)
        
        ttk.Button(
            button_frame_c,
            text="📦 Compress Selected Videos",
            command=self.start_compression,
            style='Primary.TButton'
        ).pack(pady=8, ipady=8, fill="x")
        
        # Initialize compress tab variables
        self.video_files_compress = []
        self.selected_videos_compress = {}
    
    def setup_trim_tab(self):
        """Setup the trim/cut tab (lossless)"""
        
        # File Selection Frame
        file_frame_t = ttk.LabelFrame(self.trim_tab, text="📁 Video Selection", padding=15)
        file_frame_t.pack(fill="both", expand=False, padx=15, pady=10)
        
        btn_frame_t = ttk.Frame(file_frame_t)
        btn_frame_t.pack(fill="x")
        
        ttk.Button(
            btn_frame_t,
            text="➕ Add Videos",
            command=self.add_videos_trim,
            style='Success.TButton'
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            btn_frame_t,
            text="🗑️ Clear All",
            command=self.clear_videos_trim,
            style='Danger.TButton'
        ).pack(side="left")
        
        # Video List Frame
        list_frame_t = ttk.LabelFrame(self.trim_tab, text="📋 Selected Videos", padding=10)
        list_frame_t.pack(fill="both", expand=True, padx=15, pady=10)
        
        scrollbar_t = ttk.Scrollbar(list_frame_t)
        scrollbar_t.pack(side="right", fill="y")
        
        self.canvas_trim = tk.Canvas(list_frame_t, yscrollcommand=scrollbar_t.set, bg='white',
                                     highlightthickness=0, borderwidth=0)
        self.canvas_trim.pack(side="left", fill="both", expand=True)
        scrollbar_t.config(command=self.canvas_trim.yview)
        
        self.video_list_frame_trim = ttk.Frame(self.canvas_trim)
        self.canvas_trim.create_window((0, 0), window=self.video_list_frame_trim, anchor="nw")
        
        # Trim Options Frame
        trim_options = ttk.LabelFrame(self.trim_tab, text="✂️ Trim Settings (Lossless - No Re-encoding)", padding=15)
        trim_options.pack(fill="x", padx=15, pady=10)
        
        # Start time
        start_frame_t = ttk.Frame(trim_options)
        start_frame_t.pack(fill="x", pady=8)
        ttk.Label(start_frame_t, text="Start Time:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.trim_start_var_tab = tk.StringVar(value="00:00:00.000")
        ttk.Entry(start_frame_t, textvariable=self.trim_start_var_tab, width=18, font=('Consolas', 9)).pack(side="left", padx=5)
        ttk.Label(start_frame_t, text="(HH:MM:SS.mmm, e.g., 00:00:05.500 = 5.5 sec)", foreground="gray").pack(side="left")
        
        # End time
        end_frame_t = ttk.Frame(trim_options)
        end_frame_t.pack(fill="x", pady=8)
        ttk.Label(end_frame_t, text="End Time:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.trim_end_var_tab = tk.StringVar(value="")
        ttk.Entry(end_frame_t, textvariable=self.trim_end_var_tab, width=18, font=('Consolas', 9)).pack(side="left", padx=5)
        ttk.Label(end_frame_t, text="(HH:MM:SS.mmm or leave empty for end of video)", foreground="gray").pack(side="left")
        
        # Info label
        ttk.Separator(trim_options, orient='horizontal').pack(fill='x', pady=10)
        info_frame = ttk.Frame(trim_options)
        info_frame.pack(fill="x")
        info_label = ttk.Label(
            info_frame,
            text="⚡ Lossless trimming: Fast processing with no quality loss (stream copy mode)",
            style='Success.TLabel'
        )
        info_label.pack()
        
        # Output folder
        ttk.Separator(trim_options, orient='horizontal').pack(fill='x', pady=15)
        output_frame_t = ttk.Frame(trim_options)
        output_frame_t.pack(fill="x", pady=5)
        ttk.Label(output_frame_t, text="Output Folder:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.output_path_trim = tk.StringVar(value=str(Path.home() / "Videos" / "Trimmed"))
        ttk.Entry(output_frame_t, textvariable=self.output_path_trim, width=55, font=('Segoe UI', 9)).pack(side="left", padx=5)
        ttk.Button(output_frame_t, text="📂 Browse", command=self.select_output_folder_trim).pack(side="left", padx=5)
        
        # Progress Frame
        progress_frame_t = ttk.LabelFrame(self.trim_tab, text="📊 Progress", padding=15)
        progress_frame_t.pack(fill="x", padx=15, pady=10)
        
        self.progress_label_trim = ttk.Label(progress_frame_t, text="Ready to trim videos", font=('Segoe UI', 9))
        self.progress_label_trim.pack(fill="x", pady=(0, 8))
        
        self.progress_bar_trim = ttk.Progressbar(progress_frame_t, mode="determinate", length=100)
        self.progress_bar_trim.pack(fill="x")
        
        # Spacer frame to push button to bottom
        spacer_t = ttk.Frame(self.trim_tab)
        spacer_t.pack(fill="both", expand=True)
        
        # Trim Button Frame (fixed at bottom with minimum height)
        button_frame_t = ttk.Frame(self.trim_tab, height=80)
        button_frame_t.pack(fill="x", padx=15, pady=15)
        button_frame_t.pack_propagate(False)
        
        ttk.Button(
            button_frame_t,
            text="✂️ Trim Selected Videos (Lossless)",
            command=self.start_trimming,
            style='Primary.TButton'
        ).pack(pady=8, ipady=8, fill="x")
        
        # Initialize trim tab variables
        self.video_files_trim = []
        self.selected_videos_trim = {}
    
    def setup_join_tab(self):
        """Setup the join/concatenate tab (lossless)"""
        
        # File Selection Frame
        file_frame_j = ttk.LabelFrame(self.join_tab, text="📁 Video Selection (in order)", padding=15)
        file_frame_j.pack(fill="both", expand=False, padx=15, pady=10)
        
        btn_frame_j = ttk.Frame(file_frame_j)
        btn_frame_j.pack(fill="x")
        
        ttk.Button(
            btn_frame_j,
            text="➕ Add Videos",
            command=self.add_videos_join,
            style='Success.TButton'
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            btn_frame_j,
            text="🗑️ Clear All",
            command=self.clear_videos_join,
            style='Danger.TButton'
        ).pack(side="left")
        
        # Video List Frame with reordering
        list_frame_j = ttk.LabelFrame(self.join_tab, text="🔗 Video Order (will be joined in this order)", padding=15)
        list_frame_j.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Create a frame to hold the listbox and buttons side by side
        list_container = ttk.Frame(list_frame_j)
        list_container.pack(fill="both", expand=True)
        
        # Listbox with scrollbar
        scrollbar_j = ttk.Scrollbar(list_container)
        scrollbar_j.pack(side="right", fill="y")
        
        self.join_listbox = tk.Listbox(list_container, yscrollcommand=scrollbar_j.set, selectmode=tk.SINGLE, 
                                       height=10, font=('Segoe UI', 9), borderwidth=0, highlightthickness=1)
        self.join_listbox.pack(side="left", fill="both", expand=True)
        scrollbar_j.config(command=self.join_listbox.yview)
        
        # Reorder buttons
        reorder_frame = ttk.Frame(list_container)
        reorder_frame.pack(side="right", padx=(10, 0))
        
        ttk.Button(reorder_frame, text="↑ Move Up", command=self.move_up_join, width=12).pack(pady=2)
        ttk.Button(reorder_frame, text="↓ Move Down", command=self.move_down_join, width=12).pack(pady=2)
        ttk.Button(reorder_frame, text="🗑 Remove", command=self.remove_selected_join, width=12).pack(pady=10)
        
        # Compatibility check button and label
        ttk.Separator(list_frame_j, orient='horizontal').pack(fill='x', pady=10)
        check_frame = ttk.Frame(list_frame_j)
        check_frame.pack(fill="x", pady=5)
        
        ttk.Button(
            check_frame,
            text="✓ Check Compatibility",
            command=self.check_compatibility_join,
            style='Primary.TButton'
        ).pack(side="left")
        
        self.compatibility_label = ttk.Label(check_frame, text="Click 'Check Compatibility' before joining", 
                                            foreground="gray", font=('Segoe UI', 9))
        self.compatibility_label.pack(side="left", padx=15)
        
        # Info label
        info_label = ttk.Label(
            list_frame_j,
            text="⚡ Lossless joining: Fast processing with no quality loss (videos must have same codec/resolution/fps)",
            style='Success.TLabel',
            wraplength=700
        )
        info_label.pack(pady=(10, 0))
        
        # Output folder
        output_frame_j = ttk.LabelFrame(self.join_tab, text="📂 Output Settings", padding=15)
        output_frame_j.pack(fill="x", padx=15, pady=10)
        
        output_inner = ttk.Frame(output_frame_j)
        output_inner.pack(fill="x")
        ttk.Label(output_inner, text="Output Folder:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        self.output_path_join = tk.StringVar(value=str(Path.home() / "Videos" / "Joined"))
        ttk.Entry(output_inner, textvariable=self.output_path_join, width=55, font=('Segoe UI', 9)).pack(side="left", padx=5)
        ttk.Button(output_inner, text="📂 Browse", command=self.select_output_folder_join).pack(side="left", padx=5)
        
        # Progress Frame
        progress_frame_j = ttk.LabelFrame(self.join_tab, text="📊 Progress", padding=15)
        progress_frame_j.pack(fill="x", padx=15, pady=10)
        
        self.progress_label_join = ttk.Label(progress_frame_j, text="Ready to join videos", font=('Segoe UI', 9))
        self.progress_label_join.pack(fill="x", pady=(0, 8))
        
        self.progress_bar_join = ttk.Progressbar(progress_frame_j, mode="determinate", length=100)
        self.progress_bar_join.pack(fill="x")
        
        # Spacer frame to push button to bottom
        spacer_j = ttk.Frame(self.join_tab)
        spacer_j.pack(fill="both", expand=True)
        
        # Join Button Frame (fixed at bottom with minimum height)
        button_frame_j = ttk.Frame(self.join_tab, height=80)
        button_frame_j.pack(fill="x", padx=15, pady=15)
        button_frame_j.pack_propagate(False)
        
        ttk.Button(
            button_frame_j,
            text="🔗 Join Videos (Lossless)",
            command=self.start_joining,
            style='Primary.TButton'
        ).pack(pady=8, ipady=8, fill="x")
        
        # Initialize join tab variables
        self.video_files_join = []
    
    def setup_image_tab(self):
        """Setup the image converter tab"""
        
        # Check ImageMagick availability
        if not self.image_processor.is_available():
            # Show warning if ImageMagick not found
            warning_frame = ttk.Frame(self.image_tab)
            warning_frame.pack(expand=True, fill="both", padx=20, pady=20)
            
            ttk.Label(
                warning_frame,
                text="⚠️ ImageMagick Not Found",
                style='Warning.TLabel',
                font=('Segoe UI', 14, 'bold')
            ).pack(pady=(50, 10))
            
            ttk.Label(
                warning_frame,
                text="ImageMagick is required for image conversion.\n\n"
                     "Please install it from: https://imagemagick.org/script/download.php\n\n"
                     "After installation, restart the application.",
                font=('Segoe UI', 10),
                justify="center"
            ).pack(pady=10)
            return
        
        # Initialize image tab variables
        self.image_files = []
        self.selected_images = {}
        self.output_format_img = tk.StringVar(value="WebP")  # Best compression format
        self.quality_img = tk.IntVar(value=90)  # Best balanced quality
        self.resize_preset_img = tk.StringVar(value="Original")
        self.custom_width_img = tk.StringVar(value="1920")
        self.delete_originals_img = tk.BooleanVar(value=False)
        self.output_same_folder_img = tk.BooleanVar(value=True)
        self.output_path_img = tk.StringVar(value=str(Path.home() / "Pictures" / "Converted"))
        
        # File Selection Frame
        file_frame_img = ttk.LabelFrame(self.image_tab, text="📁 Image Selection", padding=15)
        file_frame_img.pack(fill="both", expand=False, padx=15, pady=10)
        
        btn_frame_img = ttk.Frame(file_frame_img)
        btn_frame_img.pack(fill="x")
        
        ttk.Button(
            btn_frame_img,
            text="➕ Add Images",
            command=self.add_images,
            style='Success.TButton'
        ).pack(side="left", padx=(0, 10))
        
        ttk.Button(
            btn_frame_img,
            text="🗑️ Clear All",
            command=self.clear_images,
            style='Danger.TButton'
        ).pack(side="left")
        
        # Supported formats info
        ttk.Label(
            btn_frame_img,
            text="Supports: JXR, JPG, PNG, BMP, TIFF, WebP, GIF, HEIC",
            foreground="gray",
            font=('Segoe UI', 8)
        ).pack(side="right")
        
        # Image List Frame
        list_frame_img = ttk.LabelFrame(self.image_tab, text="📋 Selected Images", padding=10)
        list_frame_img.pack(fill="both", expand=True, padx=15, pady=10)
        
        # Scrollbar and canvas for image list
        scrollbar_img = ttk.Scrollbar(list_frame_img)
        scrollbar_img.pack(side="right", fill="y")
        
        self.canvas_img = tk.Canvas(list_frame_img, yscrollcommand=scrollbar_img.set, bg='white',
                                    highlightthickness=0, borderwidth=0)
        self.canvas_img.pack(side="left", fill="both", expand=True)
        scrollbar_img.config(command=self.canvas_img.yview)
        
        self.image_list_frame = ttk.Frame(self.canvas_img)
        self.canvas_img.create_window((0, 0), window=self.image_list_frame, anchor="nw")
        
        # Conversion Settings Frame
        settings_frame = ttk.LabelFrame(self.image_tab, text="⚙️ Conversion Settings", padding=15)
        settings_frame.pack(fill="x", padx=15, pady=10)
        
        # Row 1: Output format and Quality
        row1 = ttk.Frame(settings_frame)
        row1.pack(fill="x", pady=5)
        
        ttk.Label(row1, text="Output Format:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        format_combo = ttk.Combobox(row1, textvariable=self.output_format_img, 
                                    values=list(self.image_processor.OUTPUT_FORMATS.keys()),
                                    state="readonly", width=10)
        format_combo.pack(side="left", padx=(0, 30))
        
        ttk.Label(row1, text="Quality:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        quality_scale = ttk.Scale(row1, from_=1, to=100, variable=self.quality_img, 
                                  orient="horizontal", length=150)
        quality_scale.pack(side="left", padx=(0, 5))
        self.quality_label_img = ttk.Label(row1, text="85%", width=5)
        self.quality_label_img.pack(side="left")
        
        # Update quality label when slider moves
        def update_quality_label(*args):
            self.quality_label_img.config(text=f"{self.quality_img.get()}%")
        self.quality_img.trace('w', update_quality_label)
        
        # Row 2: Resize options
        row2 = ttk.Frame(settings_frame)
        row2.pack(fill="x", pady=5)
        
        ttk.Label(row2, text="Resize:", font=('Segoe UI', 9, 'bold')).pack(side="left", padx=(0, 10))
        resize_combo = ttk.Combobox(row2, textvariable=self.resize_preset_img,
                                    values=list(self.image_processor.RESIZE_PRESETS.keys()),
                                    state="readonly", width=18)
        resize_combo.pack(side="left", padx=(0, 15))
        
        self.custom_width_frame = ttk.Frame(row2)
        ttk.Label(self.custom_width_frame, text="Width:").pack(side="left", padx=(0, 5))
        ttk.Entry(self.custom_width_frame, textvariable=self.custom_width_img, width=8).pack(side="left")
        ttk.Label(self.custom_width_frame, text="px").pack(side="left", padx=(2, 0))
        
        # Show/hide custom width based on selection
        def on_resize_change(*args):
            if self.resize_preset_img.get() == "Custom":
                self.custom_width_frame.pack(side="left", padx=10)
            else:
                self.custom_width_frame.pack_forget()
        self.resize_preset_img.trace('w', on_resize_change)
        
        # Row 3: Delete originals checkbox
        row3 = ttk.Frame(settings_frame)
        row3.pack(fill="x", pady=5)
        
        ttk.Checkbutton(
            row3,
            text="🗑️ Delete original files after successful conversion",
            variable=self.delete_originals_img
        ).pack(side="left")
        
        # Output Settings Frame
        output_frame_img = ttk.LabelFrame(self.image_tab, text="📂 Output Settings", padding=15)
        output_frame_img.pack(fill="x", padx=15, pady=10)
        
        # Output folder options
        output_row1 = ttk.Frame(output_frame_img)
        output_row1.pack(fill="x", pady=2)
        
        ttk.Radiobutton(
            output_row1,
            text="Same folder as source",
            variable=self.output_same_folder_img,
            value=True
        ).pack(side="left")
        
        output_row2 = ttk.Frame(output_frame_img)
        output_row2.pack(fill="x", pady=2)
        
        ttk.Radiobutton(
            output_row2,
            text="Custom folder:",
            variable=self.output_same_folder_img,
            value=False
        ).pack(side="left")
        
        ttk.Entry(output_row2, textvariable=self.output_path_img, width=45, 
                  font=('Segoe UI', 9)).pack(side="left", padx=5)
        ttk.Button(output_row2, text="📂 Browse", 
                   command=self.select_output_folder_img).pack(side="left", padx=5)
        
        # Progress Frame
        progress_frame_img = ttk.LabelFrame(self.image_tab, text="📊 Progress", padding=15)
        progress_frame_img.pack(fill="x", padx=15, pady=10)
        
        self.progress_label_img = ttk.Label(progress_frame_img, text="Ready to convert images", 
                                            font=('Segoe UI', 9))
        self.progress_label_img.pack(fill="x", pady=(0, 8))
        
        self.progress_bar_img = ttk.Progressbar(progress_frame_img, mode="determinate", length=100)
        self.progress_bar_img.pack(fill="x")
        
        # Error/Log Frame - copyable text area
        log_frame_img = ttk.LabelFrame(self.image_tab, text="📋 Log / Errors (select and Ctrl+C to copy)", padding=10)
        log_frame_img.pack(fill="x", padx=15, pady=5)
        
        log_scroll = ttk.Scrollbar(log_frame_img)
        log_scroll.pack(side="right", fill="y")
        
        self.log_text_img = tk.Text(log_frame_img, height=4, wrap='word', 
                                    yscrollcommand=log_scroll.set, font=('Consolas', 9),
                                    bg='#f8f8f8')
        self.log_text_img.pack(fill="x", expand=True)
        log_scroll.config(command=self.log_text_img.yview)
        self.log_text_img.insert('1.0', 'Ready. Errors and status will appear here.\n')
        
        # Convert Button Frame
        button_frame_img = ttk.Frame(self.image_tab, height=80)
        button_frame_img.pack(fill="x", padx=15, pady=15)
        button_frame_img.pack_propagate(False)
        
        ttk.Button(
            button_frame_img,
            text="🖼️ Convert Images",
            command=self.start_image_conversion,
            style='Primary.TButton'
        ).pack(pady=8, ipady=8, fill="x")
    
    def add_images(self):
        """Open file dialog to add images"""
        # Build file type filter
        extensions = ' '.join(f'*{ext}' for ext in self.image_processor.INPUT_FORMATS)
        files = filedialog.askopenfilenames(
            title="Select Image Files",
            filetypes=[
                ("Image Files", extensions),
                ("All Files", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.image_files:
                self.image_files.append(file)
                self.selected_images[file] = tk.BooleanVar(value=True)
        
        self.refresh_image_list()
    
    def clear_images(self):
        """Clear all images from the list"""
        self.image_files.clear()
        self.selected_images.clear()
        self.refresh_image_list()
    
    def refresh_image_list(self):
        """Refresh the image list display"""
        for widget in self.image_list_frame.winfo_children():
            widget.destroy()
        
        for image_path in self.image_files:
            filename = os.path.basename(image_path)
            size = self.get_file_size(image_path)
            
            cb = ttk.Checkbutton(
                self.image_list_frame,
                text=f"{filename} ({size})",
                variable=self.selected_images[image_path]
            )
            cb.pack(fill="x", pady=3, padx=5)
        
        self.image_list_frame.update_idletasks()
        self.canvas_img.config(scrollregion=self.canvas_img.bbox("all"))
    
    def select_output_folder_img(self):
        """Select output folder for converted images"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_img.set(folder)
            self.output_same_folder_img.set(False)
    
    def log_image_message(self, message):
        """Add a message to the image log text area"""
        self.log_text_img.insert('end', message + '\n')
        self.log_text_img.see('end')  # Scroll to bottom
    
    def clear_image_log(self):
        """Clear the image log"""
        self.log_text_img.delete('1.0', 'end')
    
    def start_image_conversion(self):
        """Start image conversion in a separate thread"""
        # Clear previous log
        self.root.after(0, self.clear_image_log)
        
        selected = [path for path, var in self.selected_images.items() if var.get()]
        
        if not selected:
            self.root.after(0, lambda: self.log_image_message("⚠️ No images selected. Please select at least one image."))
            return
        
        if not self.image_processor.is_available():
            self.root.after(0, lambda: self.log_image_message("❌ ERROR: ImageMagick is not available.\nPlease install it from https://imagemagick.org and restart."))
            return
        
        # Determine output directory
        output_dir = None if self.output_same_folder_img.get() else self.output_path_img.get()
        
        if output_dir:
            try:
                Path(output_dir).mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.root.after(0, lambda: self.log_image_message(f"❌ ERROR: Cannot create output directory:\n{str(e)}"))
                return
        
        # Determine resize width
        resize_width = None
        preset = self.resize_preset_img.get()
        if preset == "Custom":
            try:
                resize_width = int(self.custom_width_img.get())
            except ValueError:
                self.root.after(0, lambda: self.log_image_message("⚠️ Invalid width. Please enter a valid number in pixels."))
                return
        else:
            resize_width = self.image_processor.RESIZE_PRESETS.get(preset)
        
        self.root.after(0, lambda: self.log_image_message(f"Starting conversion of {len(selected)} image(s)..."))
        
        thread = threading.Thread(
            target=self.convert_images,
            args=(selected, output_dir, resize_width),
            daemon=True
        )
        thread.start()
    
    def convert_images(self, selected_files, output_dir, resize_width):
        """Convert images (runs in thread)"""
        total = len(selected_files)
        
        def progress_callback(current, total, filename):
            self.root.after(0, lambda: self.update_image_progress(current, total, filename))
        
        self.root.after(0, lambda: self.progress_bar_img.config(value=0))
        self.root.after(0, lambda: self.progress_label_img.config(text="Starting conversion..."))
        
        try:
            results = self.image_processor.batch_convert(
                input_files=selected_files,
                output_format=self.output_format_img.get(),
                output_dir=output_dir,
                quality=self.quality_img.get(),
                resize_width=resize_width,
                delete_originals=self.delete_originals_img.get(),
                progress_callback=progress_callback
            )
            
            # Show completion
            success_count = len(results['success'])
            failed_count = len(results['failed'])
            
            self.root.after(0, lambda: self.progress_bar_img.config(value=100))
            self.root.after(0, lambda: self.progress_label_img.config(
                text=f"✅ Complete: {success_count} converted, {failed_count} failed"
            ))
            
            # Log detailed results
            for msg in results['messages']:
                self.root.after(0, lambda m=msg: self.log_image_message(m))
            
            if failed_count > 0:
                self.root.after(0, lambda: self.log_image_message(f"\n⚠️ {failed_count} file(s) failed. Check errors above."))
            else:
                self.root.after(0, lambda: self.log_image_message(f"\n✅ Successfully converted {success_count} image(s)!"))
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            self.root.after(0, lambda: self.log_image_message(f"❌ ERROR: {str(e)}\n\nDetails:\n{error_details}"))
            self.root.after(0, lambda: self.progress_label_img.config(text="❌ Conversion failed - see log"))
    
    def update_image_progress(self, current, total, filename):
        """Update progress UI for image conversion"""
        progress = int((current / total) * 100)
        self.progress_bar_img.config(value=progress)
        self.progress_label_img.config(text=f"Converting {current}/{total}: {filename}")

    def toggle_trim_options(self):
        """Show/hide trim/cut options"""
        if self.enable_trim.get():
            self.trim_frame.pack(fill="x", pady=5)
        else:
            self.trim_frame.pack_forget()
    
    def add_videos(self):
        """Open file dialog to add videos"""
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
                ("All Files", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.video_files:
                self.video_files.append(file)
                self.selected_videos[file] = tk.BooleanVar(value=True)
        
        self.refresh_video_list()
    
    def clear_videos(self):
        """Clear all videos from the list"""
        self.video_files.clear()
        self.selected_videos.clear()
        self.refresh_video_list()
    
    def refresh_video_list(self):
        """Refresh the video list display with checkboxes and optional thumbnails"""
        # Clear existing widgets
        for widget in self.video_list_frame.winfo_children():
            widget.destroy()
        
        # Add checkboxes with optional thumbnails for each video
        for video_path in self.video_files:
            # Create frame for each video entry
            video_frame = ttk.Frame(self.video_list_frame)
            video_frame.pack(fill="x", pady=3, padx=5)
            
            # Get thumbnail only if enabled
            thumbnail = None
            if self.thumbnails_enabled.get():
                thumbnail = self.get_thumbnail(video_path)
            
            # Thumbnail label (only if thumbnails enabled and generated)
            if thumbnail:
                thumb_label = ttk.Label(video_frame, image=thumbnail)
                thumb_label.image = thumbnail  # Keep reference
                thumb_label.pack(side="left", padx=(0, 8))
            
            # Checkbox with filename
            filename = os.path.basename(video_path)
            cb = ttk.Checkbutton(
                video_frame,
                text=f"{filename} ({self.get_file_size(video_path)})",
                variable=self.selected_videos[video_path]
            )
            cb.pack(side="left", fill="x", expand=True)
            
            # Bind click event to update preview
            video_frame.bind("<Button-1>", lambda e, vp=video_path: self.update_preview(vp))
            if thumbnail:
                thumb_label.bind("<Button-1>", lambda e, vp=video_path: self.update_preview(vp))
        
        # Update scroll region
        self.video_list_frame.update_idletasks()
        self.canvas.config(scrollregion=self.canvas.bbox("all"))
    
    def get_thumbnail(self, video_path):
        """Get or generate thumbnail for video with maintained aspect ratio"""
        if video_path in self.thumbnails:
            return self.thumbnails[video_path]
        
        # Generate thumbnail
        thumbnail_path = os.path.join(self.temp_dir, f"{hash(video_path)}.jpg")
        
        try:
            # Extract full frame using FFmpeg (no size specified to keep original ratio)
            success = self.video_processor.extract_thumbnail(
                video_path, 
                thumbnail_path,
                timestamp="00:00:01",
                width=None,  # Will be set to -1 in extract_thumbnail
                height=None
            )
            
            if success and os.path.exists(thumbnail_path):
                # Load and resize with aspect ratio maintained
                img = Image.open(thumbnail_path)
                
                # Resize to fit within 80x45 while maintaining aspect ratio
                img.thumbnail((80, 45), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                self.thumbnails[video_path] = photo
                return photo
            else:
                # Return None if thumbnail generation failed
                return None
                
        except Exception as e:
            print(f"Error generating thumbnail: {e}")
            return None
    
    def update_preview(self, video_path):
        """Update the preview panel with video information"""
        self.current_preview_video = video_path
        
        # Update filename
        filename = os.path.basename(video_path)
        self.preview_filename_label.config(text=filename)
        
        # Get detailed video info
        info = self.video_processor.get_detailed_video_info(video_path)
        
        if info:
            self.preview_resolution_label.config(text=f"Resolution: {info.get('resolution', '-')}")
            self.preview_fps_label.config(text=f"Frame Rate: {info.get('fps', '-')} fps")
            self.preview_duration_label.config(text=f"Duration: {info.get('duration', '-')}")
            self.preview_codec_label.config(text=f"Codec: {info.get('codec', '-').upper()}")
            self.preview_bitrate_label.config(text=f"Bitrate: {info.get('bitrate', '-')}")
            self.preview_size_label.config(text=f"Size: {info.get('size', '-')}")
        else:
            self.preview_resolution_label.config(text="Resolution: -")
            self.preview_fps_label.config(text="Frame Rate: -")
            self.preview_duration_label.config(text="Duration: -")
            self.preview_codec_label.config(text="Codec: -")
            self.preview_bitrate_label.config(text="Bitrate: -")
            self.preview_size_label.config(text="Size: -")
        
        # Update preview image (larger thumbnail with aspect ratio maintained)
        thumbnail_path = os.path.join(self.temp_dir, f"{hash(video_path)}_preview.jpg")
        
        try:
            success = self.video_processor.extract_thumbnail(
                video_path,
                thumbnail_path,
                timestamp="00:00:01",
                width=None,  # Will be set to -1 in extract_thumbnail
                height=None
            )
            
            if success and os.path.exists(thumbnail_path):
                # Load and resize with aspect ratio maintained
                img = Image.open(thumbnail_path)
                
                # Resize to fit within 280x158 while maintaining aspect ratio
                img.thumbnail((280, 158), Image.Resampling.LANCZOS)
                
                photo = ImageTk.PhotoImage(img)
                self.preview_image_label.config(image=photo, text="", bg='#e0e0e0')
                self.preview_image_label.image = photo  # Keep a reference
            else:
                self.preview_image_label.config(text="Preview not available", image='', bg='#e0e0e0')
                
        except Exception as e:
            print(f"Error updating preview: {e}")
            self.preview_image_label.config(text="Preview error", image='', bg='#e0e0e0')
    
    def get_file_size(self, file_path):
        """Get human-readable file size"""
        size = os.path.getsize(file_path)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"
    
    def select_output_folder(self):
        """Select output folder for processed videos"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_var.set(folder)
    
    def add_videos_compress(self):
        """Open file dialog to add videos for compression"""
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
                ("All Files", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.video_files_compress:
                self.video_files_compress.append(file)
                self.selected_videos_compress[file] = tk.BooleanVar(value=True)
        
        self.refresh_video_list_compress()
    
    def clear_videos_compress(self):
        """Clear all videos from compression list"""
        self.video_files_compress.clear()
        self.selected_videos_compress.clear()
        self.refresh_video_list_compress()
    
    def refresh_video_list_compress(self):
        """Refresh the compression video list display"""
        for widget in self.video_list_frame_compress.winfo_children():
            widget.destroy()
        
        for video_path in self.video_files_compress:
            filename = os.path.basename(video_path)
            cb = ttk.Checkbutton(
                self.video_list_frame_compress,
                text=f"{filename} ({self.get_file_size(video_path)})",
                variable=self.selected_videos_compress[video_path]
            )
            cb.pack(fill="x", pady=3, padx=5)
        
        self.video_list_frame_compress.update_idletasks()
        self.canvas_compress.config(scrollregion=self.canvas_compress.bbox("all"))
    
    def select_output_folder_compress(self):
        """Select output folder for compressed videos"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_compress.set(folder)
    
    def add_videos_trim(self):
        """Open file dialog to add videos for trimming"""
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
                ("All Files", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.video_files_trim:
                self.video_files_trim.append(file)
                self.selected_videos_trim[file] = tk.BooleanVar(value=True)
        
        self.refresh_video_list_trim()
    
    def clear_videos_trim(self):
        """Clear all videos from trim list"""
        self.video_files_trim.clear()
        self.selected_videos_trim.clear()
        self.refresh_video_list_trim()
    
    def refresh_video_list_trim(self):
        """Refresh the trim video list display"""
        for widget in self.video_list_frame_trim.winfo_children():
            widget.destroy()
        
        for video_path in self.video_files_trim:
            filename = os.path.basename(video_path)
            cb = ttk.Checkbutton(
                self.video_list_frame_trim,
                text=f"{filename} ({self.get_file_size(video_path)})",
                variable=self.selected_videos_trim[video_path]
            )
            cb.pack(fill="x", pady=3, padx=5)
        
        self.video_list_frame_trim.update_idletasks()
        self.canvas_trim.config(scrollregion=self.canvas_trim.bbox("all"))
    
    def select_output_folder_trim(self):
        """Select output folder for trimmed videos"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_trim.set(folder)
    
    def start_trimming(self):
        """Start video trimming in a separate thread"""
        selected = [path for path, var in self.selected_videos_trim.items() if var.get()]
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one video to trim.")
            return
        
        # Validate time inputs
        trim_start = self.trim_start_var_tab.get()
        trim_end = self.trim_end_var_tab.get()
        
        if not trim_start:
            messagebox.showwarning("Invalid Input", "Please enter a start time.")
            return
        
        if not self.video_processor.check_ffmpeg():
            self.show_ffmpeg_error()
            return
        
        output_dir = Path(self.output_path_trim.get())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output directory:\n{str(e)}")
            return
        
        thread = threading.Thread(
            target=self.trim_videos,
            args=(selected,),
            daemon=True
        )
        thread.start()
    
    def trim_videos(self, video_paths):
        """Trim selected videos using lossless stream copy"""
        total = len(video_paths)
        output_dir = Path(self.output_path_trim.get())
        trim_start = self.trim_start_var_tab.get()
        trim_end = self.trim_end_var_tab.get() if self.trim_end_var_tab.get() else None
        
        success_count = 0
        failed_videos = []
        
        for idx, video_path in enumerate(video_paths, 1):
            filename = os.path.basename(video_path)
            self.update_progress_trim(f"Trimming {idx}/{total}: {filename}...", (idx - 1) / total * 100)
            
            try:
                # Generate output filename with prefix
                name_parts = os.path.splitext(filename)
                output_filename = f"trimmed-{name_parts[0]}{name_parts[1]}"
                output_path = output_dir / output_filename
                
                # Trim video (lossless)
                self.video_processor.trim_video_lossless(
                    str(video_path),
                    str(output_path),
                    trim_start=trim_start,
                    trim_end=trim_end
                )
                
                success_count += 1
                self.update_progress_trim(
                    f"Completed {idx}/{total}: {filename}",
                    idx / total * 100
                )
            except Exception as e:
                failed_videos.append((filename, str(e)))
                self.update_progress_trim(
                    f"Failed {idx}/{total}: {filename}",
                    idx / total * 100
                )
        
        # Show completion summary
        if failed_videos:
            error_msg = f"Trimming completed with errors.\n\n"
            error_msg += f"✓ Successfully trimmed: {success_count}/{total}\n"
            error_msg += f"✗ Failed: {len(failed_videos)}/{total}\n\n"
            error_msg += "Failed videos:\n"
            for fname, error in failed_videos:
                error_msg += f"• {fname}: {error}\n"
            
            self.root.after(0, lambda: self.show_ffmpeg_error(error_msg, "Trimming Results"))
        else:
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"All {total} video(s) trimmed successfully!\n\nOutput: {output_dir}"
            ))
        
        self.update_progress_trim("Ready", 0)
    
    def update_progress_trim(self, message, value):
        """Update trim progress bar and label"""
        self.root.after(0, lambda: self.progress_label_trim.config(text=message))
        self.root.after(0, lambda: self.progress_bar_trim.config(value=value))
    
    def add_videos_join(self):
        """Open file dialog to add videos for joining"""
        files = filedialog.askopenfilenames(
            title="Select Video Files (will be joined in order selected)",
            filetypes=[
                ("Video Files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
                ("All Files", "*.*")
            ]
        )
        
        for file in files:
            if file not in self.video_files_join:
                self.video_files_join.append(file)
        
        self.refresh_video_list_join()
    
    def clear_videos_join(self):
        """Clear all videos from join list"""
        self.video_files_join.clear()
        self.refresh_video_list_join()
        self.compatibility_label.config(text="Click 'Check Compatibility' before joining", fg="gray")
    
    def refresh_video_list_join(self):
        """Refresh the join video list display"""
        self.join_listbox.delete(0, tk.END)
        
        for video_path in self.video_files_join:
            filename = os.path.basename(video_path)
            self.join_listbox.insert(tk.END, f"{filename} ({self.get_file_size(video_path)})")
    
    def move_up_join(self):
        """Move selected video up in the list"""
        selection = self.join_listbox.curselection()
        if not selection or selection[0] == 0:
            return
        
        idx = selection[0]
        # Swap in the list
        self.video_files_join[idx], self.video_files_join[idx-1] = \
            self.video_files_join[idx-1], self.video_files_join[idx]
        
        self.refresh_video_list_join()
        self.join_listbox.select_set(idx-1)
        self.compatibility_label.config(text="Order changed - check compatibility again", fg="orange")
    
    def move_down_join(self):
        """Move selected video down in the list"""
        selection = self.join_listbox.curselection()
        if not selection or selection[0] >= len(self.video_files_join) - 1:
            return
        
        idx = selection[0]
        # Swap in the list
        self.video_files_join[idx], self.video_files_join[idx+1] = \
            self.video_files_join[idx+1], self.video_files_join[idx]
        
        self.refresh_video_list_join()
        self.join_listbox.select_set(idx+1)
        self.compatibility_label.config(text="Order changed - check compatibility again", fg="orange")
    
    def remove_selected_join(self):
        """Remove selected video from join list"""
        selection = self.join_listbox.curselection()
        if not selection:
            return
        
        idx = selection[0]
        del self.video_files_join[idx]
        self.refresh_video_list_join()
        self.compatibility_label.config(text="Video removed - check compatibility again", fg="orange")
    
    def check_compatibility_join(self):
        """Check if all videos are compatible for lossless joining"""
        if len(self.video_files_join) < 2:
            self.compatibility_label.config(text="⚠️ Need at least 2 videos to join", fg="red")
            return
        
        try:
            is_compatible, message = self.video_processor.check_video_compatibility(self.video_files_join)
            
            if is_compatible:
                self.compatibility_label.config(text=f"✓ {message}", fg="green")
            else:
                self.compatibility_label.config(text=f"✗ {message}", fg="red")
        except Exception as e:
            self.compatibility_label.config(text=f"✗ Error checking: {str(e)}", fg="red")
    
    def select_output_folder_join(self):
        """Select output folder for joined video"""
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_path_join.set(folder)
    
    def start_joining(self):
        """Start video joining in a separate thread"""
        if len(self.video_files_join) < 2:
            messagebox.showwarning("Insufficient Videos", "Please add at least 2 videos to join.")
            return
        
        if not self.video_processor.check_ffmpeg():
            self.show_ffmpeg_error()
            return
        
        output_dir = Path(self.output_path_join.get())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output directory:\n{str(e)}")
            return
        
        thread = threading.Thread(
            target=self.join_videos,
            daemon=True
        )
        thread.start()
    
    def join_videos(self):
        """Join videos using lossless concat demuxer"""
        output_dir = Path(self.output_path_join.get())
        
        self.update_progress_join("Checking compatibility...", 10)
        
        try:
            # Check compatibility first
            is_compatible, message = self.video_processor.check_video_compatibility(self.video_files_join)
            
            if not is_compatible:
                self.root.after(0, lambda: messagebox.showerror(
                    "Incompatible Videos",
                    f"{message}\n\nSuggestion: Use the Upscale tab to normalize all videos to the same resolution and codec first."
                ))
                self.update_progress_join("Failed - incompatible videos", 0)
                return
            
            self.update_progress_join("Joining videos (lossless)...", 30)
            
            # Generate output filename
            output_filename = f"joined-{Path(self.video_files_join[0]).stem}.mp4"
            output_path = output_dir / output_filename
            
            # Join videos
            self.video_processor.join_videos_concat(
                self.video_files_join,
                str(output_path)
            )
            
            self.update_progress_join("Complete!", 100)
            
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"Videos joined successfully!\n\nOutput: {output_path}\n\nTotal videos: {len(self.video_files_join)}"
            ))
            
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror(
                "Error",
                f"Failed to join videos:\n{str(e)}"
            ))
        
        self.update_progress_join("Ready", 0)
    
    def update_progress_join(self, message, value):
        """Update join progress bar and label"""
        self.root.after(0, lambda: self.progress_label_join.config(text=message))
        self.root.after(0, lambda: self.progress_bar_join.config(value=value))
    
    def start_compression(self):
        """Start video compression in a separate thread"""
        selected = [path for path, var in self.selected_videos_compress.items() if var.get()]
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one video to compress.")
            return
        
        if not self.video_processor.check_ffmpeg():
            self.show_ffmpeg_error()
            return
        
        output_dir = Path(self.output_path_compress.get())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output directory:\n{str(e)}")
            return
        
        thread = threading.Thread(
            target=self.compress_videos,
            args=(selected,),
            daemon=True
        )
        thread.start()
    
    def compress_videos(self, video_paths):
        """Compress selected videos"""
        total = len(video_paths)
        output_dir = Path(self.output_path_compress.get())
        codec = self.codec_var.get()
        quality = self.compress_quality.get()
        audio_codec = self.audio_codec_var.get()
        
        success_count = 0
        failed_videos = []
        
        for idx, video_path in enumerate(video_paths, 1):
            filename = os.path.basename(video_path)
            self.update_progress_compress(f"Compressing {idx}/{total}: {filename}...", (idx - 1) / total * 100)
            
            try:
                # Generate output filename with prefix
                name_parts = os.path.splitext(filename)
                output_filename = f"compressed-{name_parts[0]}{name_parts[1]}"
                output_path = output_dir / output_filename
                
                # Compress video
                self.video_processor.compress_video(
                    str(video_path),
                    str(output_path),
                    codec=codec,
                    quality=quality,
                    audio_codec=audio_codec
                )
                
                success_count += 1
                self.update_progress_compress(
                    f"Completed {idx}/{total}: {filename}",
                    idx / total * 100
                )
            except Exception as e:
                failed_videos.append((filename, str(e)))
                self.update_progress_compress(
                    f"Failed {idx}/{total}: {filename}",
                    idx / total * 100
                )
        
        # Show completion summary
        if failed_videos:
            error_msg = f"Compression completed with errors.\n\n"
            error_msg += f"✓ Successfully compressed: {success_count}/{total}\n"
            error_msg += f"✗ Failed: {len(failed_videos)}/{total}\n\n"
            error_msg += "Failed videos:\n"
            for fname, error in failed_videos:
                error_msg += f"• {fname}: {error}\n"
            
            self.root.after(0, lambda: self.show_ffmpeg_error(error_msg, "Compression Results"))
        else:
            self.root.after(0, lambda: messagebox.showinfo(
                "Success",
                f"All {total} video(s) compressed successfully!\n\nOutput: {output_dir}"
            ))
        
        self.update_progress_compress("Ready", 0)
    
    def update_progress_compress(self, message, value):
        """Update compression progress bar and label"""
        self.root.after(0, lambda: self.progress_label_compress.config(text=message))
        self.root.after(0, lambda: self.progress_bar_compress.config(value=value))
    
    def start_processing(self):
        """Start video processing in a separate thread"""
        selected = [path for path, var in self.selected_videos.items() if var.get()]
        
        if not selected:
            messagebox.showwarning("No Selection", "Please select at least one video to process.")
            return
        
        # Check if FFmpeg is available BEFORE starting
        if not self.video_processor.check_ffmpeg():
            self.show_ffmpeg_error()
            return
        
        # Create output directory if it doesn't exist
        output_dir = Path(self.output_path_var.get())
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output directory:\n{str(e)}")
            return
        
        # Disable button during processing
        self.btn_process.config(state="disabled")
        
        # Start processing thread
        thread = threading.Thread(
            target=self.process_videos,
            args=(selected,),
            daemon=True
        )
        thread.start()
    
    def _get_encoder_info(self, resolution):
        """Get encoder info string based on GPU and resolution"""
        # Parse resolution height
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
            target_height = 1080
        
        gpu_encoder = self.video_processor.gpu_encoder
        
        # Check if NVENC with 8K (will fallback to CPU)
        if gpu_encoder == "nvenc" and target_height > 4096:
            return "CPU HEVC Encoding"
        elif gpu_encoder == "nvenc":
            return "NVIDIA GPU Encoding"
        elif gpu_encoder == "amf":
            return "AMD GPU Encoding"
        elif gpu_encoder == "qsv":
            return "Intel GPU Encoding"
        else:
            return "CPU Encoding"
    
    def process_videos(self, video_paths):
        """Process selected videos"""
        total = len(video_paths)
        output_dir = Path(self.output_path_var.get())
        resolution = self.resolution_var.get()
        
        # Get trim settings
        enable_trim = self.enable_trim.get()
        trim_start = self.trim_start_var.get() if enable_trim else None
        trim_end = self.trim_end_var.get() if enable_trim and self.trim_end_var.get() else None
        
        # Determine encoder for status display
        encoder_info = self._get_encoder_info(resolution)
        
        success_count = 0
        failed_videos = []
        
        for idx, video_path in enumerate(video_paths, 1):
            filename = os.path.basename(video_path)
            self.update_progress(f"Processing {idx}/{total}: {filename} [{encoder_info}]...", (idx - 1) / total * 100)
            
            try:
                # Convert to HD
                output_name = f"scaled-{Path(filename).stem}_{resolution}{Path(filename).suffix}"
                output_path = output_dir / output_name
                
                self.video_processor.convert_to_hd(
                    input_path=video_path,
                    output_path=str(output_path),
                    resolution=resolution,
                    trim_start=trim_start,
                    trim_end=trim_end
                )
                
                success_count += 1
                self.update_progress(f"✓ Completed {idx}/{total}: {filename}", idx / total * 100)
                
            except Exception as e:
                failed_videos.append((filename, str(e)))
                self.update_progress(f"✗ Failed {idx}/{total}: {filename}", idx / total * 100)
        
        # Show completion summary
        self.update_progress(f"Complete! {success_count}/{total} videos processed", 100)
        self.root.after(0, lambda: self.processing_complete(success_count, total, failed_videos))
    
    def update_progress(self, message, percent):
        """Update progress bar and label"""
        self.root.after(0, lambda: self.progress_label.config(text=message))
        self.root.after(0, lambda: self.progress_bar.config(value=percent))
    
    def show_ffmpeg_error(self):
        """Show FFmpeg error in a custom dialog with copyable text"""
        error_window = tk.Toplevel(self.root)
        error_window.title("FFmpeg Not Found")
        error_window.geometry("600x400")
        error_window.resizable(False, False)
        
        # Center the window
        error_window.transient(self.root)
        error_window.grab_set()
        
        # Title
        title_label = tk.Label(
            error_window,
            text="⚠ FFmpeg Not Found",
            font=("Arial", 14, "bold"),
            fg="red",
            pady=10
        )
        title_label.pack()
        
        # Message frame with scrollbar
        text_frame = tk.Frame(error_window, padx=20, pady=10)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        error_text = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Consolas", 10),
            relief="solid",
            borderwidth=1
        )
        error_text.pack(fill="both", expand=True)
        scrollbar.config(command=error_text.yview)
        
        # Error message
        message = (
            "FFmpeg is required but not found.\n\n"
            "To install FFmpeg, run this command in PowerShell:\n\n"
            "    winget install Gyan.FFmpeg\n\n"
            "After installation:\n"
            "1. Close this application\n"
            "2. Restart your terminal/PowerShell\n"
            "3. Run the application again\n\n"
            "You can copy this message using Ctrl+C"
        )
        error_text.insert("1.0", message)
        error_text.config(state="disabled")  # Make read-only
        
        # OK button
        ok_button = tk.Button(
            error_window,
            text="OK",
            command=error_window.destroy,
            bg="#2196F3",
            fg="white",
            padx=30,
            pady=10,
            font=("Arial", 10, "bold")
        )
        ok_button.pack(pady=10)
        
        # Wait for window to close
        error_window.wait_window()
    
    def processing_complete(self, success_count, total, failed_videos):
        """Called when processing is complete"""
        self.btn_process.config(state="normal")
        
        if failed_videos:
            # Some videos failed - show in custom window with copyable text
            self.show_error_details(success_count, total, failed_videos)
        else:
            # All successful
            output_dir = self.output_path_var.get()
            messagebox.showinfo(
                "Success!",
                f"✓ Successfully processed all {total} video(s)\n\n"
                f"Output folder:\n{output_dir}"
            )
    
    def show_error_details(self, success_count, total, failed_videos):
        """Show processing errors in a custom dialog with copyable text"""
        error_window = tk.Toplevel(self.root)
        error_window.title("Processing Errors")
        error_window.geometry("700x500")
        error_window.resizable(True, True)
        
        # Center the window
        error_window.transient(self.root)
        error_window.grab_set()
        
        # Title
        title_label = tk.Label(
            error_window,
            text=f"⚠ Processing Complete: {success_count}/{total} Successful",
            font=("Arial", 14, "bold"),
            fg="orange" if success_count > 0 else "red",
            pady=10
        )
        title_label.pack()
        
        # Summary
        summary_label = tk.Label(
            error_window,
            text=f"✓ Successful: {success_count}  |  ✗ Failed: {len(failed_videos)}",
            font=("Arial", 11),
            pady=5
        )
        summary_label.pack()
        
        # Message frame with scrollbar
        text_frame = tk.Frame(error_window, padx=20, pady=10)
        text_frame.pack(fill="both", expand=True)
        
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side="right", fill="y")
        
        error_text = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Consolas", 9),
            relief="solid",
            borderwidth=1
        )
        error_text.pack(fill="both", expand=True)
        scrollbar.config(command=error_text.yview)
        
        # Error details
        message = "FAILED VIDEOS AND ERRORS:\n" + "="*60 + "\n\n"
        for idx, (filename, error) in enumerate(failed_videos, 1):
            message += f"{idx}. {filename}\n"
            message += f"   Error: {error}\n\n"
        
        message += "="*60 + "\n"
        message += "You can select and copy this text with Ctrl+C"
        
        error_text.insert("1.0", message)
        error_text.config(state="normal")  # Keep editable for copying
        
        # Button frame
        btn_frame = tk.Frame(error_window)
        btn_frame.pack(pady=10)
        
        # Copy All button
        def copy_all():
            error_window.clipboard_clear()
            error_window.clipboard_append(error_text.get("1.0", "end-1c"))
            copy_btn.config(text="✓ Copied!")
            error_window.after(2000, lambda: copy_btn.config(text="Copy All"))
        
        copy_btn = tk.Button(
            btn_frame,
            text="Copy All",
            command=copy_all,
            bg="#4CAF50",
            fg="white",
            padx=20,
            pady=8,
            font=("Arial", 10, "bold")
        )
        copy_btn.pack(side="left", padx=5)
        
        # OK button
        ok_button = tk.Button(
            btn_frame,
            text="OK",
            command=error_window.destroy,
            bg="#2196F3",
            fg="white",
            padx=30,
            pady=8,
            font=("Arial", 10, "bold")
        )
        ok_button.pack(side="left", padx=5)
        
        # Wait for window to close
        error_window.wait_window()


def check_prerequisites():
    """Check if FFmpeg is available, show helpful error if not"""
    try:
        from prerequisites_checker import PrerequisitesChecker
        
        checker = PrerequisitesChecker()
        
        # Quick check for FFmpeg (most critical requirement)
        ffmpeg_ok, ffmpeg_msg = checker.check_ffmpeg()
        
        if not ffmpeg_ok:
            # Show user-friendly error dialog
            root = tk.Tk()
            root.withdraw()  # Hide main window
            
            response = messagebox.askyesno(
                "Missing FFmpeg",
                "FFmpeg is required but not found on your system.\n\n"
                f"Details: {ffmpeg_msg}\n\n"
                "Would you like to run the setup wizard to install it?\n\n"
                "(You can also run 'setup.bat' manually)",
                icon='warning'
            )
            
            root.destroy()
            
            if response:
                # User wants to run setup wizard
                print("\n" + "="*60)
                print("Starting setup wizard...")
                print("="*60 + "\n")
                
                success = checker.run_full_check()
                if not success:
                    checker.interactive_install()
                
                print("\n" + "="*60)
                print("Please restart the application.")
                print("="*60 + "\n")
                sys.exit(0)
            else:
                # User declined, exit
                return False
        
        return True
        
    except ImportError:
        # Prerequisites checker not available, skip check
        return True
    except Exception as e:
        print(f"Warning: Prerequisites check failed: {e}")
        return True  # Continue anyway


def show_error_dialog(title, message, details=None):
    """Show an error dialog with copyable text"""
    # Also write to a log file for easy copying
    log_file = os.path.join(os.path.dirname(__file__), "error_log.txt")
    try:
        with open(log_file, 'w', encoding='utf-8') as f:
            f.write(f"=== {title} ===\n\n")
            f.write(f"Message: {message}\n\n")
            if details:
                f.write(f"Details:\n{details}\n")
        print(f"Error log written to: {log_file}")
    except:
        pass
    
    # Create a standalone Tk window for the error
    error_root = tk.Tk()
    error_root.title(title)
    error_root.geometry("700x500")
    error_root.resizable(True, True)
    
    # Center on screen
    error_root.update_idletasks()
    x = (error_root.winfo_screenwidth() - 700) // 2
    y = (error_root.winfo_screenheight() - 500) // 2
    error_root.geometry(f"700x500+{x}+{y}")
    
    # Error icon and message
    tk.Label(error_root, text="❌ " + title, font=('Segoe UI', 12, 'bold'), 
             anchor='w').pack(pady=(15, 5), padx=15, fill='x')
    tk.Label(error_root, text=message, wraplength=650, anchor='w', 
             justify='left').pack(pady=5, padx=15, fill='x')
    
    # Copyable text area for details
    tk.Label(error_root, text="Error Details (select and Ctrl+C to copy):", 
             font=('Segoe UI', 9, 'bold'), anchor='w').pack(pady=(10, 5), padx=15, fill='x')
    
    text_frame = tk.Frame(error_root)
    text_frame.pack(fill='both', expand=True, padx=15, pady=5)
    
    scrollbar = tk.Scrollbar(text_frame)
    scrollbar.pack(side='right', fill='y')
    
    text_area = tk.Text(text_frame, wrap='word', yscrollcommand=scrollbar.set, 
                        font=('Consolas', 9), bg='#f8f8f8')
    text_area.pack(side='left', fill='both', expand=True)
    scrollbar.config(command=text_area.yview)
    
    full_text = f"{message}\n\n{details if details else ''}"
    text_area.insert('1.0', full_text)
    
    # Buttons frame
    btn_frame = tk.Frame(error_root)
    btn_frame.pack(fill='x', padx=15, pady=15)
    
    def copy_to_clipboard():
        error_root.clipboard_clear()
        error_root.clipboard_append(full_text)
        copy_btn.config(text="✓ Copied!")
        error_root.after(1500, lambda: copy_btn.config(text="📋 Copy All"))
    
    def open_log_file():
        os.startfile(log_file) if os.path.exists(log_file) else None
    
    copy_btn = tk.Button(btn_frame, text="📋 Copy All", command=copy_to_clipboard, 
                         font=('Segoe UI', 9), padx=10, pady=5)
    copy_btn.pack(side='left', padx=5)
    
    tk.Button(btn_frame, text="📂 Open Log File", command=open_log_file,
              font=('Segoe UI', 9), padx=10, pady=5).pack(side='left', padx=5)
    
    tk.Button(btn_frame, text="Close", command=error_root.destroy,
              font=('Segoe UI', 9), padx=10, pady=5).pack(side='right', padx=5)
    
    # Also show log file location
    tk.Label(error_root, text=f"Log file: {log_file}", font=('Segoe UI', 8), 
             fg='gray').pack(pady=(0, 10))
    
    error_root.mainloop()


def main():
    # Check prerequisites on startup
    if not check_prerequisites():
        sys.exit(1)
    
    try:
        root = tk.Tk()
        
        # Try to use SOLID dependency injection via factory
        try:
            from src.app_factory import get_factory
            factory = get_factory()
            app = factory.create_app(root)
        except ImportError:
            # Fallback to legacy initialization if src module not available
            app = VideoUpscalerApp(root)
        
        root.mainloop()
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        
        # Show in GUI dialog
        try:
            show_error_dialog("Application Error", str(e), error_details)
        except Exception as dialog_error:
            # Fallback to console
            print(f"Error: {e}")
            print(error_details)
            print(f"(Dialog error: {dialog_error})")
        
        sys.exit(1)


if __name__ == "__main__":
    main()
