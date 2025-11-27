"""
Video Editor Pro - Production-Ready Architecture
SOLID-compliant video processing application
"""

__version__ = "2.3.0"
__author__ = "AI-Assisted Development (GitHub Copilot)"

from .app_factory import ApplicationFactory, get_factory

__all__ = [
    'ApplicationFactory',
    'get_factory',
]
