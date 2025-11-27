"""
Video List Manager
Manages video file list and selection following Single Responsibility Principle
"""

from typing import List, Set, Optional, Callable
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog

from ..core.logger import get_logger
from ..core.exceptions import FileError


logger = get_logger(__name__)


class VideoListManager:
    """Manages list of video files and their selection state"""
    
    def __init__(self, parent: tk.Widget):
        self.parent = parent
        self.video_files: List[Path] = []
        self.selected_videos: Set[Path] = set()
        self.on_selection_changed: Optional[Callable[[Path], None]] = None
        
        # Create UI
        self._create_ui()
    
    def _create_ui(self) -> None:
        """Create video list UI components"""
        # Frame for list and scrollbar
        list_frame = ttk.Frame(self.parent)
        list_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(list_frame)
        scrollbar.pack(side="right", fill="y")
        
        # Listbox
        self.listbox = tk.Listbox(
            list_frame,
            selectmode=tk.MULTIPLE,
            yscrollcommand=scrollbar.set,
            font=('Segoe UI', 9),
            bg='white',
            selectbackground='#3498db',
            selectforeground='white',
            relief='flat',
            borderwidth=1,
            highlightthickness=1,
            highlightbackground='#bdc3c7'
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        scrollbar.config(command=self.listbox.yview)
        
        # Bind selection event
        self.listbox.bind('<<ListboxSelect>>', self._on_select)
        
        # Button frame
        btn_frame = ttk.Frame(self.parent)
        btn_frame.pack(fill="x", padx=5, pady=5)
        
        ttk.Button(
            btn_frame,
            text="📁 Add Videos",
            command=self.add_videos,
            style='Primary.TButton'
        ).pack(side="left", padx=2)
        
        ttk.Button(
            btn_frame,
            text="🗑️ Remove Selected",
            command=self.remove_selected,
            style='Danger.TButton'
        ).pack(side="left", padx=2)
        
        ttk.Button(
            btn_frame,
            text="📋 Clear All",
            command=self.clear_all,
            style='Danger.TButton'
        ).pack(side="left", padx=2)
    
    def add_videos(self) -> None:
        """Open file dialog and add selected videos"""
        filetypes = [
            ("Video files", "*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.webm"),
            ("All files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(
            title="Select video files",
            filetypes=filetypes
        )
        
        if files:
            for file_path in files:
                path = Path(file_path)
                if path not in self.video_files:
                    self.video_files.append(path)
                    self.listbox.insert(tk.END, path.name)
                    logger.info(f"Added video: {path.name}")
            
            logger.info(f"Total videos: {len(self.video_files)}")
    
    def remove_selected(self) -> None:
        """Remove selected videos from list"""
        selected_indices = self.listbox.curselection()
        
        # Remove in reverse order to maintain indices
        for index in reversed(selected_indices):
            path = self.video_files[index]
            self.video_files.pop(index)
            self.listbox.delete(index)
            self.selected_videos.discard(path)
            logger.info(f"Removed video: {path.name}")
    
    def clear_all(self) -> None:
        """Clear all videos from list"""
        self.video_files.clear()
        self.selected_videos.clear()
        self.listbox.delete(0, tk.END)
        logger.info("Cleared all videos")
    
    def get_video_files(self) -> List[Path]:
        """Get list of all video files"""
        return self.video_files.copy()
    
    def get_selected_videos(self) -> List[Path]:
        """Get list of selected video files"""
        selected_indices = self.listbox.curselection()
        return [self.video_files[i] for i in selected_indices]
    
    def set_selection_callback(self, callback: Callable[[Path], None]) -> None:
        """Set callback for selection changes"""
        self.on_selection_changed = callback
    
    def _on_select(self, event) -> None:
        """Handle selection change"""
        selected_indices = self.listbox.curselection()
        
        if selected_indices and self.on_selection_changed:
            # Get the first selected video
            index = selected_indices[0]
            video_path = self.video_files[index]
            self.on_selection_changed(video_path)


class ThumbnailVideoListManager(VideoListManager):
    """Video list manager with thumbnail support"""
    
    def __init__(
        self,
        parent: tk.Widget,
        thumbnail_extractor,
        thumbnail_size: tuple = (80, 45)
    ):
        self.thumbnail_extractor = thumbnail_extractor
        self.thumbnail_size = thumbnail_size
        self.thumbnails = {}
        self.thumbnails_enabled = tk.BooleanVar(value=False)
        
        super().__init__(parent)
    
    def _create_ui(self) -> None:
        """Create UI with thumbnail toggle"""
        # Thumbnail toggle
        ttk.Checkbutton(
            self.parent,
            text="🖼️ Show Thumbnails",
            variable=self.thumbnails_enabled,
            command=self._toggle_thumbnails,
            style='TCheckbutton'
        ).pack(anchor="w", padx=5, pady=5)
        
        # Rest of UI
        super()._create_ui()
    
    def _toggle_thumbnails(self) -> None:
        """Toggle thumbnail display"""
        # This would require a refresh of the video list display
        # Implementation depends on specific UI framework
        logger.info(f"Thumbnails enabled: {self.thumbnails_enabled.get()}")
