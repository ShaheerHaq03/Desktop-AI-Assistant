"""
Cross-platform Application Launcher
Handles opening applications with platform-specific commands and safety checks
"""

import asyncio
import json
import logging
import platform
import subprocess
import os
from pathlib import Path
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class AppLauncher:
    """Cross-platform application launcher with configurable mappings."""
    
    def __init__(self, config_file: str = None):
        self.system = platform.system()
        
        # Load configuration
        if config_file:
            self.config_file = Path(config_file)
        else:
            self.config_file = Path.home() / ".agent_desktop_ai" / "app_mappings.json"
        
        self._load_app_mappings()
    
    def _load_app_mappings(self):
        """Load application mappings from config file."""
        default_mappings = self._get_default_mappings()
        
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    custom_mappings = json.load(f)
                    # Merge custom mappings with defaults
                    for system, apps in custom_mappings.items():
                        if system in default_mappings:
                            default_mappings[system].update(apps)
                        else:
                            default_mappings[system] = apps
        except Exception as e:
            logger.error(f"Failed to load app mappings: {e}")
        
        self.app_mappings = default_mappings
        self._save_app_mappings()  # Ensure file exists with defaults
    
    def _save_app_mappings(self):
        """Save application mappings to config file."""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_file, 'w') as f:
                json.dump(self.app_mappings, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save app mappings: {e}")
    
    def _get_default_mappings(self) -> Dict[str, Dict[str, Any]]:
        """Get default application mappings for each platform."""
        return {
            "Windows": {
                "chrome": {
                    "paths": [
                        "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
                        "C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
                        "%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe"
                    ],
                    "start_command": "start chrome"
                },
                "firefox": {
                    "paths": [
                        "C:\\Program Files\\Mozilla Firefox\\firefox.exe",
                        "C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe"
                    ],
                    "start_command": "start firefox"
                },
                "vscode": {
                    "paths": [
                        "%LOCALAPPDATA%\\Programs\\Microsoft VS Code\\Code.exe",
                        "C:\\Program Files\\Microsoft VS Code\\Code.exe"
                    ],
                    "start_command": "code"
                },
                "notepad": {
                    "paths": ["C:\\Windows\\System32\\notepad.exe"],
                    "start_command": "notepad"
                },
                "calculator": {
                    "paths": ["calc.exe"],
                    "start_command": "calc"
                },
                "explorer": {
                    "paths": ["explorer.exe"],
                    "start_command": "explorer"
                },
                "spotify": {
                    "paths": ["%APPDATA%\\Spotify\\Spotify.exe"],
                    "start_command": "start spotify:"
                }
            },
            "Darwin": {  # macOS
                "chrome": {
                    "paths": ["/Applications/Google Chrome.app"],
                    "open_command": "open -a 'Google Chrome'"
                },
                "firefox": {
                    "paths": ["/Applications/Firefox.app"],
                    "open_command": "open -a Firefox"
                },
                "safari": {
                    "paths": ["/Applications/Safari.app"],
                    "open_command": "open -a Safari"
                },
                "vscode": {
                    "paths": ["/Applications/Visual Studio Code.app"],
                    "open_command": "open -a 'Visual Studio Code'"
                },
                "textedit": {
                    "paths": ["/System/Applications/TextEdit.app"],
                    "open_command": "open -a TextEdit"
                },
                "finder": {
                    "paths": ["/System/Library/CoreServices/Finder.app"],
                    "open_command": "open -a Finder"
                },
                "spotify": {
                    "paths": ["/Applications/Spotify.app"],
                    "open_command": "open -a Spotify"
                },
                "calculator": {
                    "paths": ["/System/Applications/Calculator.app"],
                    "open_command": "open -a Calculator"
                }
            },
            "Linux": {
                "chrome": {
                    "paths": ["/usr/bin/google-chrome", "/opt/google/chrome/google-chrome"],
                    "exec_command": "google-chrome"
                },
                "firefox": {
                    "paths": ["/usr/bin/firefox", "/snap/bin/firefox"],
                    "exec_command": "firefox"
                },
                "vscode": {
                    "paths": ["/usr/bin/code", "/snap/bin/code"],
                    "exec_command": "code"
                },
                "gedit": {
                    "paths": ["/usr/bin/gedit"],
                    "exec_command": "gedit"
                },
                "nautilus": {
                    "paths": ["/usr/bin/nautilus"],
                    "exec_command": "nautilus"
                },
                "spotify": {
                    "paths": ["/snap/bin/spotify", "/usr/bin/spotify"],
                    "exec_command": "spotify"
                },
                "calculator": {
                    "paths": ["/usr/bin/gnome-calculator", "/usr/bin/calc"],
                    "exec_command": "gnome-calculator"
                }
            }
        }
    
    async def open_app(self, app_name: str, dry_run: bool = False) -> Dict[str, Any]:
        """
        Open an application by name.
        
        Args:
            app_name: Name of the application to open
            dry_run: If True, simulate the action without executing
            
        Returns:
            Result dictionary with success status and details
        """
        try:
            app_name_lower = app_name.lower().strip()
            
            if dry_run:
                return {
                    'success': True,
                    'message': f'[DRY RUN] Would open app: {app_name}',
                    'app_name': app_name,
                    'system': self.system
                }
            
            # Get system-specific mappings
            system_apps = self.app_mappings.get(self.system, {})
            
            if app_name_lower in system_apps:
                result = await self._open_mapped_app(app_name_lower, system_apps[app_name_lower])
            else:
                result = await self._open_generic_app(app_name)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to open app {app_name}: {e}")
            return {
                'success': False,
                'message': f'Failed to open app: {str(e)}',
                'error': str(e)
            }
    
    async def _open_mapped_app(self, app_name: str, app_config: Dict[str, Any]) -> Dict[str, Any]:
        """Open an app using predefined mapping configuration."""
        
        # Try direct path execution first
        if 'paths' in app_config:
            for path in app_config['paths']:
                # Expand environment variables
                expanded_path = os.path.expandvars(path)
                
                if os.path.exists(expanded_path):
                    try:
                        if self.system == "Windows":
                            subprocess.Popen([expanded_path], shell=False)
                        else:
                            subprocess.Popen([expanded_path])
                        
                        return {
                            'success': True,
                            'message': f'Opened {app_name} from {expanded_path}',
                            'path': expanded_path,
                            'method': 'direct_path'
                        }
                    except Exception as e:
                        logger.warning(f"Failed to open {app_name} from path {expanded_path}: {e}")
                        continue
        
        # Try system-specific commands
        if self.system == "Windows" and 'start_command' in app_config:
            try:
                subprocess.Popen(app_config['start_command'], shell=True)
                return {
                    'success': True,
                    'message': f'Opened {app_name} using start command',
                    'command': app_config['start_command'],
                    'method': 'start_command'
                }
            except Exception as e:
                logger.warning(f"Start command failed for {app_name}: {e}")
        
        elif self.system == "Darwin" and 'open_command' in app_config:
            try:
                subprocess.Popen(app_config['open_command'], shell=True)
                return {
                    'success': True,
                    'message': f'Opened {app_name} using open command',
                    'command': app_config['open_command'],
                    'method': 'open_command'
                }
            except Exception as e:
                logger.warning(f"Open command failed for {app_name}: {e}")
        
        elif self.system == "Linux" and 'exec_command' in app_config:
            try:
                subprocess.Popen(app_config['exec_command'], shell=True)
                return {
                    'success': True,
                    'message': f'Opened {app_name} using exec command',
                    'command': app_config['exec_command'],
                    'method': 'exec_command'
                }
            except Exception as e:
                logger.warning(f"Exec command failed for {app_name}: {e}")
        
        return {
            'success': False,
            'message': f'Failed to open {app_name} - no working method found',
            'app_name': app_name
        }
    
    async def _open_generic_app(self, app_name: str) -> Dict[str, Any]:
        """Try to open an app using generic system methods."""
        
        try:
            if self.system == "Windows":
                # Try as a direct command first
                subprocess.Popen(f"start {app_name}", shell=True)
                return {
                    'success': True,
                    'message': f'Opened {app_name} using generic start command',
                    'method': 'generic_start'
                }
            
            elif self.system == "Darwin":
                # Try with open -a
                subprocess.Popen(f"open -a '{app_name}'", shell=True)
                return {
                    'success': True,
                    'message': f'Opened {app_name} using generic open command',
                    'method': 'generic_open'
                }
            
            elif self.system == "Linux":
                # Try as direct command
                subprocess.Popen([app_name])
                return {
                    'success': True,
                    'message': f'Opened {app_name} as direct command',
                    'method': 'direct_exec'
                }
            
        except Exception as e:
            logger.error(f"Generic app launch failed for {app_name}: {e}")
        
        return {
            'success': False,
            'message': f'Unable to open {app_name} - app not found or not configured',
            'suggestion': 'Try adding the app to the configuration file or use the full path'
        }
    
    def add_app_mapping(self, app_name: str, config: Dict[str, Any]):
        """Add a new application mapping."""
        system_apps = self.app_mappings.setdefault(self.system, {})
        system_apps[app_name.lower()] = config
        self._save_app_mappings()
        logger.info(f"Added app mapping for {app_name}")
    
    def remove_app_mapping(self, app_name: str):
        """Remove an application mapping."""
        system_apps = self.app_mappings.get(self.system, {})
        if app_name.lower() in system_apps:
            del system_apps[app_name.lower()]
            self._save_app_mappings()
            logger.info(f"Removed app mapping for {app_name}")
    
    def list_available_apps(self) -> List[str]:
        """Get list of configured applications for current system."""
        return list(self.app_mappings.get(self.system, {}).keys())
    
    def get_app_info(self, app_name: str) -> Optional[Dict[str, Any]]:
        """Get configuration information for a specific app."""
        system_apps = self.app_mappings.get(self.system, {})
        return system_apps.get(app_name.lower())
    
    async def verify_app_exists(self, app_name: str) -> Dict[str, Any]:
        """Verify if an app exists and can be launched."""
        try:
            app_name_lower = app_name.lower()
            system_apps = self.app_mappings.get(self.system, {})
            
            if app_name_lower in system_apps:
                app_config = system_apps[app_name_lower]
                
                # Check if any of the configured paths exist
                if 'paths' in app_config:
                    for path in app_config['paths']:
                        expanded_path = os.path.expandvars(path)
                        if os.path.exists(expanded_path):
                            return {
                                'exists': True,
                                'path': expanded_path,
                                'method': 'path_exists'
                            }
                
                return {
                    'exists': False,
                    'message': f'App {app_name} is configured but no valid paths found',
                    'config': app_config
                }
            else:
                return {
                    'exists': False,
                    'message': f'App {app_name} not configured',
                    'suggestion': 'Use generic launch or add to configuration'
                }
                
        except Exception as e:
            return {
                'exists': False,
                'error': str(e)
            }
    
    def get_system_info(self) -> Dict[str, Any]:
        """Get system information relevant to app launching."""
        return {
            'system': self.system,
            'platform': platform.platform(),
            'available_apps': self.list_available_apps(),
            'config_file': str(self.config_file)
        }
