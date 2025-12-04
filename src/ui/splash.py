"""
Splash Screen Module
Displays a professional loading screen during application initialization
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time


class SplashScreen:
    """Professional splash screen with loading animation"""
    
    def __init__(self, root: tk.Tk, duration: float = 3.0):
        """
        Initialize splash screen
        
        Args:
            root: Tkinter root window
            duration: Minimum display duration in seconds
        """
        self.root = root
        self.duration = duration
        self.start_time = time.time()
        self.is_closing = False
        
        # Configure window
        self.root.withdraw()  # Hide main window
        
        # Create splash window
        splash = tk.Toplevel(root)
        splash.title("Loading...")
        splash.geometry("500x300")
        splash.resizable(False, False)
        
        # Remove window decorations
        splash.attributes('-topmost', True)
        
        # Center on screen
        splash.update_idletasks()
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        x = (screen_width - 500) // 2
        y = (screen_height - 300) // 2
        splash.geometry(f"500x300+{x}+{y}")
        
        # Configure background
        splash.configure(bg='#2c3e50')
        
        # Title
        title_font = tkfont.Font(family='Segoe UI', size=24, weight='bold')
        title = tk.Label(
            splash,
            text="Video Editor Pro",
            font=title_font,
            bg='#2c3e50',
            fg='#ecf0f1'
        )
        title.pack(pady=(40, 20))
        
        # Subtitle
        subtitle_font = tkfont.Font(family='Segoe UI', size=10)
        subtitle = tk.Label(
            splash,
            text="Professional video processing with GPU acceleration",
            font=subtitle_font,
            bg='#2c3e50',
            fg='#bdc3c7'
        )
        subtitle.pack(pady=(0, 30))
        
        # Loading indicator
        self.progress_canvas = tk.Canvas(
            splash,
            width=300,
            height=20,
            bg='#2c3e50',
            highlightthickness=0
        )
        self.progress_canvas.pack(pady=20)
        
        # Progress bar background
        self.progress_canvas.create_rectangle(
            10, 5, 290, 15,
            fill='#34495e',
            outline='#95a5a6'
        )
        
        self.progress_rect = self.progress_canvas.create_rectangle(
            10, 5, 10, 15,
            fill='#3498db',
            outline='#3498db'
        )
        
        # Loading text
        self.status_label = tk.Label(
            splash,
            text="Initializing services...",
            font=('Segoe UI', 9),
            bg='#2c3e50',
            fg='#95a5a6'
        )
        self.status_label.pack(pady=(0, 10))
        
        self.splash_window = splash
        self.running = True
        
        # Start animation loop
        self._animate_progress()
    
    def _animate_progress(self):
        """Animate progress bar"""
        if not self.running:
            return
        
        elapsed = time.time() - self.start_time
        progress = min((elapsed / self.duration) * 280, 280)
        
        self.progress_canvas.coords(
            self.progress_rect,
            10, 5, 10 + progress, 15
        )
        
        if elapsed < self.duration:
            self.splash_window.after(50, self._animate_progress)
    
    def set_status(self, message: str):
        """Update status message"""
        self.status_label.config(text=message)
        self.splash_window.update()
    
    def close(self):
        """Close splash screen and show main window"""
        if not self.running:
            return
        
        self.running = False
        
        # Ensure minimum display time
        elapsed = time.time() - self.start_time
        remaining = max(0, self.duration - elapsed)
        
        if remaining > 0:
            self.splash_window.after(int(remaining * 1000), self._close_window)
        else:
            self._close_window()
    
    def _close_window(self):
        """Actually close the splash window"""
        try:
            self.splash_window.destroy()
            self.root.deiconify()  # Show main window
        except tk.TclError:
            pass  # Window already closed
