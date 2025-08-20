"""
Helper utilities for the Agent Desktop AI Extended
"""

import os
import platform
import subprocess
import sys
from pathlib import Path
from typing import Dict, Any, Optional, List

def get_system_context() -> Dict[str, Any]:
    """Get comprehensive system context information."""
    try:
        import psutil
        
        context = {
            'platform': {
                'system': platform.system(),
                'platform': platform.platform(),
                'architecture': platform.architecture(),
                'machine': platform.machine(),
                'processor': platform.processor(),
                'python_version': platform.python_version()
            },
            'resources': {
                'cpu_count': psutil.cpu_count(),
                'cpu_percent': psutil.cpu_percent(interval=1),
                'memory': {
                    'total': psutil.virtual_memory().total,
                    'available': psutil.virtual_memory().available,
                    'percent': psutil.virtual_memory().percent
                },
                'disk': {
                    'total': psutil.disk_usage('/').total if platform.system() != 'Windows' else psutil.disk_usage('C:').total,
                    'free': psutil.disk_usage('/').free if platform.system() != 'Windows' else psutil.disk_usage('C:').free,
                    'percent': psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('C:').percent
                }
            },
            'environment': {
                'user': os.getenv('USER') or os.getenv('USERNAME'),
                'home': str(Path.home()),
                'cwd': os.getcwd(),
                'path_separator': os.pathsep,
                'line_separator': os.linesep
            },
            'python': {
                'executable': sys.executable,
                'version': sys.version,
                'path': sys.path[:3]  # First 3 paths only
            }
        }
        
        return context
        
    except Exception as e:
        return {
            'error': str(e),
            'platform': {
                'system': platform.system(),
                'python_version': platform.python_version()
            }
        }

def get_running_browsers() -> List[str]:
    """Get list of currently running browser processes."""
    try:
        import psutil
        
        browser_names = ['chrome', 'firefox', 'safari', 'edge', 'opera', 'brave']
        running_browsers = []
        
        for proc in psutil.process_iter(['name']):
            try:
                proc_name = proc.info['name'].lower()
                for browser in browser_names:
                    if browser in proc_name:
                        if browser not in running_browsers:
                            running_browsers.append(browser)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
                
        return running_browsers
        
    except ImportError:
        return []
    except Exception:
        return []

def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are available."""
    dependencies = {
        'streamlit': False,
        'psutil': False,
        'vosk': False,
        'sounddevice': False,
        'numpy': False,
        'pyautogui': False,
        'pygetwindow': False,
        'requests': False,
        'httpx': False
    }
    
    for dep in dependencies:
        try:
            __import__(dep)
            dependencies[dep] = True
        except ImportError:
            dependencies[dep] = False
    
    return dependencies

def format_file_size(size_bytes: int) -> str:
    """Format file size in human readable format."""
    if size_bytes == 0:
        return "0B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    import math
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return f"{s} {size_names[i]}"

def is_admin() -> bool:
    """Check if running with administrator/root privileges."""
    try:
        if platform.system() == "Windows":
            import ctypes
            return ctypes.windll.shell32.IsUserAnAdmin()
        else:
            return os.getuid() == 0
    except:
        return False

def get_network_info() -> Dict[str, Any]:
    """Get basic network information."""
    try:
        import socket
        
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        
        return {
            'hostname': hostname,
            'local_ip': local_ip,
            'has_internet': check_internet_connection()
        }
    except:
        return {
            'hostname': 'unknown',
            'local_ip': 'unknown',
            'has_internet': False
        }

def check_internet_connection() -> bool:
    """Check if internet connection is available."""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except:
        return False

def sanitize_filename(filename: str) -> str:
    """Sanitize filename for cross-platform compatibility."""
    import re
    
    # Remove invalid characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Remove leading/trailing whitespace and dots
    filename = filename.strip(' .')
    
    # Ensure it's not empty
    if not filename:
        filename = 'unnamed'
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename

def create_desktop_shortcut(name: str, target: str, description: str = "") -> bool:
    """Create desktop shortcut (Windows only)."""
    try:
        if platform.system() != "Windows":
            return False
            
        import winshell
        from win32com.client import Dispatch
        
        desktop = winshell.desktop()
        path = os.path.join(desktop, f"{name}.lnk")
        
        shell = Dispatch('WScript.Shell')
        shortcut = shell.CreateShortCut(path)
        shortcut.Targetpath = target
        shortcut.Description = description
        shortcut.save()
        
        return True
        
    except:
        return False

def get_installed_apps() -> List[Dict[str, str]]:
    """Get list of installed applications."""
    apps = []
    system = platform.system()
    
    try:
        if system == "Windows":
            apps = _get_windows_apps()
        elif system == "Darwin":
            apps = _get_macos_apps()
        elif system == "Linux":
            apps = _get_linux_apps()
    except:
        pass
    
    return apps

def _get_windows_apps() -> List[Dict[str, str]]:
    """Get installed Windows applications."""
    apps = []
    try:
        import winreg
        
        # Check common installation paths
        keys = [
            (winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall"),
            (winreg.HKEY_CURRENT_USER, r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall")
        ]
        
        for hkey, subkey in keys:
            try:
                with winreg.OpenKey(hkey, subkey) as reg_key:
                    for i in range(winreg.QueryInfoKey(reg_key)[0]):
                        try:
                            app_key = winreg.EnumKey(reg_key, i)
                            with winreg.OpenKey(reg_key, app_key) as app_reg:
                                name = winreg.QueryValueEx(app_reg, "DisplayName")[0]
                                try:
                                    install_location = winreg.QueryValueEx(app_reg, "InstallLocation")[0]
                                except FileNotFoundError:
                                    install_location = ""
                                
                                apps.append({
                                    'name': name,
                                    'path': install_location
                                })
                        except:
                            continue
            except:
                continue
                
    except ImportError:
        pass
    
    return apps[:20]  # Limit to first 20 apps

def _get_macos_apps() -> List[Dict[str, str]]:
    """Get installed macOS applications."""
    apps = []
    try:
        apps_dir = Path("/Applications")
        if apps_dir.exists():
            for app_path in apps_dir.glob("*.app"):
                apps.append({
                    'name': app_path.stem,
                    'path': str(app_path)
                })
    except:
        pass
    
    return apps

def _get_linux_apps() -> List[Dict[str, str]]:
    """Get installed Linux applications."""
    apps = []
    try:
        # Check /usr/share/applications for .desktop files
        desktop_files = Path("/usr/share/applications").glob("*.desktop")
        
        for desktop_file in desktop_files:
            try:
                with open(desktop_file, 'r') as f:
                    content = f.read()
                    
                # Extract Name and Exec from .desktop file
                name = ""
                exec_path = ""
                
                for line in content.split('\n'):
                    if line.startswith('Name=') and not name:
                        name = line.split('=', 1)[1]
                    elif line.startswith('Exec='):
                        exec_path = line.split('=', 1)[1].split()[0]
                
                if name:
                    apps.append({
                        'name': name,
                        'path': exec_path
                    })
                    
            except:
                continue
                
    except:
        pass
    
    return apps[:20]  # Limit to first 20 apps
