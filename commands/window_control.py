"""
Cross-platform Window Controller
Handles window focusing, clicking, typing, and screenshots
"""

import asyncio
import logging
import platform
import time
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class WindowController:
    """Cross-platform window and GUI controller."""
    
    def __init__(self):
        self.system = platform.system()
        self._setup_dependencies()
    
    def _setup_dependencies(self):
        """Initialize platform-specific dependencies."""
        self.pyautogui = None
        self.pygetwindow = None
        
        try:
            import pyautogui
            self.pyautogui = pyautogui
            # Disable failsafe for headless environments
            self.pyautogui.FAILSAFE = False
        except ImportError:
            logger.warning("pyautogui not available - some features disabled")
        
        try:
            import pygetwindow as gw
            self.pygetwindow = gw
        except ImportError:
            logger.warning("pygetwindow not available - window management disabled")
    
    async def focus_window(self, window_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """Focus a window by name."""
        try:
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would focus window: {window_name}',
                    'window_name': window_name
                }
            
            if not self.pygetwindow:
                return {
                    'success': False,
                    'message': 'Window management not available - install pygetwindow'
                }
            
            # Find windows with matching name
            windows = self.pygetwindow.getWindowsWithTitle(window_name)
            
            if not windows:
                # Try partial match
                all_windows = self.pygetwindow.getAllWindows()
                windows = [w for w in all_windows if window_name.lower() in w.title.lower()]
            
            if not windows:
                return {
                    'success': False,
                    'message': f'No window found matching: {window_name}',
                    'available_windows': [w.title for w in self.pygetwindow.getAllWindows()[:10]]
                }
            
            # Focus the first matching window
            target_window = windows[0]
            target_window.activate()
            
            return {
                'success': True,
                'message': f'Focused window: {target_window.title}',
                'window_title': target_window.title
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to focus window: {e}',
                'error': str(e)
            }
    
    async def click_at(self, x: int, y: int, dry_run: bool = False) -> Dict[str, Any]:
        """Click at specific coordinates."""
        try:
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would click at ({x}, {y})',
                    'coordinates': [x, y]
                }
            
            if not self.pyautogui:
                return {
                    'success': False,
                    'message': 'GUI automation not available - install pyautogui'
                }
            
            # Get screen size
            screen_width, screen_height = self.pyautogui.size()
            
            # Validate coordinates
            if x < 0 or x > screen_width or y < 0 or y > screen_height:
                return {
                    'success': False,
                    'message': f'Coordinates ({x}, {y}) out of screen bounds ({screen_width}x{screen_height})'
                }
            
            # Perform click
            self.pyautogui.click(x, y)
            
            return {
                'success': True,
                'message': f'Clicked at ({x}, {y})',
                'coordinates': [x, y]
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to click: {e}',
                'error': str(e)
            }
    
    async def type_text(self, text: str, dry_run: bool = False) -> Dict[str, Any]:
        """Type text at current cursor position."""
        try:
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would type: {text[:50]}{"..." if len(text) > 50 else ""}',
                    'text_length': len(text)
                }
            
            if not self.pyautogui:
                return {
                    'success': False,
                    'message': 'GUI automation not available - install pyautogui'
                }
            
            # Type text with a small delay between characters for reliability
            self.pyautogui.write(text, interval=0.01)
            
            return {
                'success': True,
                'message': f'Typed text ({len(text)} characters)',
                'text_length': len(text)
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to type text: {e}',
                'error': str(e)
            }
    
    async def take_screenshot(self, filename: str = None, dry_run: bool = False) -> Dict[str, Any]:
        """Take a screenshot and save it."""
        try:
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would take screenshot',
                    'filename': filename or 'screenshot.png'
                }
            
            if not self.pyautogui:
                return {
                    'success': False,
                    'message': 'Screenshot functionality not available - install pyautogui'
                }
            
            # Generate filename if not provided
            if not filename:
                timestamp = int(time.time())
                filename = f"screenshot_{timestamp}.png"
            
            # Ensure screenshots directory exists
            screenshots_dir = Path.home() / ".agent_desktop_ai" / "screenshots"
            screenshots_dir.mkdir(parents=True, exist_ok=True)
            
            filepath = screenshots_dir / filename
            
            # Take screenshot
            screenshot = self.pyautogui.screenshot()
            screenshot.save(str(filepath))
            
            return {
                'success': True,
                'message': f'Screenshot saved: {filepath}',
                'filepath': str(filepath),
                'size': screenshot.size
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to take screenshot: {e}',
                'error': str(e)
            }
    
    async def get_window_list(self) -> Dict[str, Any]:
        """Get list of open windows."""
        try:
            if not self.pygetwindow:
                return {
                    'success': False,
                    'message': 'Window management not available',
                    'windows': []
                }
            
            windows = []
            for window in self.pygetwindow.getAllWindows():
                if window.title.strip():  # Skip windows with empty titles
                    windows.append({
                        'title': window.title,
                        'left': window.left,
                        'top': window.top,
                        'width': window.width,
                        'height': window.height,
                        'visible': window.visible
                    })
            
            return {
                'success': True,
                'message': f'Found {len(windows)} windows',
                'windows': windows
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get window list: {e}',
                'error': str(e)
            }
    
    async def get_mouse_position(self) -> Dict[str, Any]:
        """Get current mouse position."""
        try:
            if not self.pyautogui:
                return {
                    'success': False,
                    'message': 'Mouse position not available'
                }
            
            x, y = self.pyautogui.position()
            
            return {
                'success': True,
                'x': x,
                'y': y,
                'position': [x, y]
            }
            
        except Exception as e:
            return {
                'success': False,
                'message': f'Failed to get mouse position: {e}',
                'error': str(e)
            }
