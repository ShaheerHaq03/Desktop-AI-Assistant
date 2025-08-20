"""
Safety Manager - Handles consent, capabilities, and security boundaries
Implements strict safety controls with user confirmation for sensitive operations
"""

import json
import hashlib
import time
import os
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
import asyncio
import threading
try:
    import tkinter as tk
    from tkinter import messagebox
    _TK_AVAILABLE = True
except Exception:
    tk = None  # type: ignore
    messagebox = None  # type: ignore
    _TK_AVAILABLE = False
import platform

logger = logging.getLogger(__name__)

class SafetyManager:
    """Manages safety controls and user consent for sensitive operations."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path.home() / ".agent_desktop_ai"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.consents_file = self.config_dir / "consents.json"
        self.history_file = self.config_dir / "safety_history.json"
        
        self._load_consents()
        
    def _load_consents(self):
        """Load stored user consents."""
        try:
            if self.consents_file.exists():
                with open(self.consents_file, 'r') as f:
                    self._consents = json.load(f)
            else:
                self._consents = {}
        except Exception as e:
            logger.error(f"Failed to load consents: {e}")
            self._consents = {}
    
    def _save_consents(self):
        """Save user consents to file."""
        try:
            with open(self.consents_file, 'w') as f:
                json.dump(self._consents, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save consents: {e}")
    
    def _hash_action(self, action: str, target: str) -> str:
        """Create a hash for an action to store consent."""
        content = f"{action}:{target}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    async def confirm_action(self, action: str, target: str, 
                           description: str = None, 
                           timeout: int = 30,
                           requires_password: bool = False) -> Dict[str, Any]:
        """
        Request user confirmation for a potentially dangerous action.
        
        Returns:
            Dict with 'allowed', 'permanent', 'cancelled' keys
        """
        if description is None:
            description = f"Execute {action} on {target}"
        
        # Check if we have permanent consent for this action
        action_hash = self._hash_action(action, target)
        if action_hash in self._consents:
            consent = self._consents[action_hash]
            if consent.get("permanent", False) and time.time() < consent.get("expires", float('inf')):
                logger.info(f"Using stored consent for {action}")
                return {"allowed": True, "permanent": True, "cancelled": False}
        
        # Request confirmation from user
        result = await self._request_confirmation(
            action, target, description, timeout, requires_password
        )
        
        # Store consent if permanent was selected
        if result["allowed"] and result["permanent"]:
            self._consents[action_hash] = {
                "action": action,
                "target": target,
                "timestamp": time.time(),
                "permanent": True,
                "expires": time.time() + (30 * 24 * 60 * 60)  # 30 days
            }
            self._save_consents()
        
        # Log the decision
        self._log_consent_decision(action, target, result)
        
        return result
    
    async def _request_confirmation(self, action: str, target: str, 
                                  description: str, timeout: int,
                                  requires_password: bool = False) -> Dict[str, Any]:
        """Request confirmation through GUI or CLI."""
        
        # Try GUI confirmation first
        if self._can_use_gui():
            return await self._gui_confirmation(action, target, description, timeout)
        else:
            return await self._cli_confirmation(action, target, description, timeout, requires_password)
    
    def _can_use_gui(self) -> bool:
        """Check if GUI confirmation is available."""
        try:
            # If tkinter is not available, GUI cannot be used
            if not _TK_AVAILABLE:
                return False
            # On Windows and macOS, tkinter should generally be available
            if platform.system() in ["Windows", "Darwin"]:
                return True
            
            # On Linux, check if display is available
            if platform.system() == "Linux":
                return os.environ.get("DISPLAY") is not None
            
            return False
        except Exception:
            return False
    
    async def _gui_confirmation(self, action: str, target: str, 
                               description: str, timeout: int) -> Dict[str, Any]:
        """Show GUI confirmation dialog."""
        result = {"allowed": False, "permanent": False, "cancelled": True}
        
        def show_dialog():
            try:
                root = tk.Tk()
                root.withdraw()  # Hide main window
                root.attributes('-topmost', True)
                
                # Create custom dialog
                dialog = tk.Toplevel(root)
                dialog.title("⚠️ Safety Confirmation Required")
                dialog.geometry("500x300")
                dialog.configure(bg='white')
                dialog.attributes('-topmost', True)
                
                # Warning icon and text
                warning_frame = tk.Frame(dialog, bg='white')
                warning_frame.pack(pady=20, padx=20, fill='x')
                
                tk.Label(warning_frame, text="⚠️", font=("Arial", 24), 
                        bg='white', fg='orange').pack()
                tk.Label(warning_frame, text="Potentially Dangerous Action", 
                        font=("Arial", 14, "bold"), bg='white').pack(pady=5)
                
                # Description
                desc_frame = tk.Frame(dialog, bg='white')
                desc_frame.pack(pady=10, padx=20, fill='both', expand=True)
                
                tk.Label(desc_frame, text=f"Action: {action}", 
                        font=("Arial", 10), bg='white', anchor='w').pack(fill='x')
                tk.Label(desc_frame, text=f"Target: {target}", 
                        font=("Arial", 10), bg='white', anchor='w').pack(fill='x')
                tk.Label(desc_frame, text=f"Description: {description}", 
                        font=("Arial", 10), bg='white', anchor='w', wraplength=450).pack(fill='x', pady=5)
                
                # Checkbox for permanent consent
                permanent_var = tk.BooleanVar()
                tk.Checkbutton(desc_frame, text="Remember this decision (30 days)", 
                             variable=permanent_var, bg='white').pack(anchor='w', pady=5)
                
                # Buttons
                button_frame = tk.Frame(dialog, bg='white')
                button_frame.pack(pady=20, padx=20, fill='x')
                
                def allow():
                    result["allowed"] = True
                    result["permanent"] = permanent_var.get()
                    result["cancelled"] = False
                    dialog.destroy()
                    root.quit()
                
                def deny():
                    result["allowed"] = False
                    result["permanent"] = False
                    result["cancelled"] = False
                    dialog.destroy()
                    root.quit()
                
                tk.Button(button_frame, text="Allow", command=allow, 
                         bg='green', fg='white', width=15).pack(side='left', padx=5)
                tk.Button(button_frame, text="Deny", command=deny, 
                         bg='red', fg='white', width=15).pack(side='left', padx=5)
                
                # Auto-deny after timeout
                def timeout_handler():
                    result["cancelled"] = True
                    dialog.destroy()
                    root.quit()
                
                root.after(timeout * 1000, timeout_handler)
                
                # Center dialog
                dialog.update_idletasks()
                x = (dialog.winfo_screenwidth() // 2) - (dialog.winfo_width() // 2)
                y = (dialog.winfo_screenheight() // 2) - (dialog.winfo_height() // 2)
                dialog.geometry(f"+{x}+{y}")
                
                root.mainloop()
                
            except Exception as e:
                logger.error(f"GUI confirmation failed: {e}")
                result["cancelled"] = True
        
        # Run dialog in a thread to avoid blocking
        thread = threading.Thread(target=show_dialog)
        thread.daemon = True
        thread.start()
        thread.join(timeout + 1)  # Wait a bit longer than the timeout
        
        return result
    
    async def _cli_confirmation(self, action: str, target: str, 
                               description: str, timeout: int,
                               requires_password: bool = False) -> Dict[str, Any]:
        """Show CLI confirmation prompt."""
        print("\n" + "="*60)
        print("⚠️  SAFETY CONFIRMATION REQUIRED ⚠️")
        print("="*60)
        print(f"Action: {action}")
        print(f"Target: {target}")
        print(f"Description: {description}")
        print("\nThis action could potentially be dangerous or irreversible.")
        
        if requires_password:
            print("\n⚠️  This action requires additional confirmation.")
            password = input("Please type 'CONFIRM' to proceed: ")
            if password != "CONFIRM":
                return {"allowed": False, "permanent": False, "cancelled": False}
        
        print(f"\nYou have {timeout} seconds to respond.")
        print("Options:")
        print("  y / yes    - Allow this action once")
        print("  Y / YES    - Allow this action and remember (30 days)")
        print("  n / no     - Deny this action")
        print("  <Enter>    - Cancel")
        
        try:
            # Use asyncio timeout for the input
            response = await asyncio.wait_for(
                asyncio.to_thread(input, "\nYour choice: "),
                timeout=timeout
            )
            
            raw_response = response.strip()
            lower_response = raw_response.lower()
            
            if lower_response in ['y', 'yes']:
                return {"allowed": True, "permanent": False, "cancelled": False}
            elif raw_response in ['Y', 'YES']:
                return {"allowed": True, "permanent": True, "cancelled": False}
            elif lower_response in ['n', 'no']:
                return {"allowed": False, "permanent": False, "cancelled": False}
            else:
                return {"allowed": False, "permanent": False, "cancelled": True}
                
        except asyncio.TimeoutError:
            print(f"\nTimeout after {timeout} seconds. Action denied.")
            return {"allowed": False, "permanent": False, "cancelled": True}
        except Exception as e:
            logger.error(f"CLI confirmation failed: {e}")
            return {"allowed": False, "permanent": False, "cancelled": True}
    
    def _log_consent_decision(self, action: str, target: str, result: Dict[str, Any]):
        """Log the consent decision for audit purposes."""
        try:
            log_entry = {
                "timestamp": time.time(),
                "action": action,
                "target": target,
                "allowed": result["allowed"],
                "permanent": result["permanent"],
                "cancelled": result["cancelled"]
            }
            
            # Load existing history
            history = []
            if self.history_file.exists():
                try:
                    with open(self.history_file, 'r') as f:
                        history = json.load(f)
                except Exception:
                    pass
            
            # Add new entry and keep only last 1000 entries
            history.append(log_entry)
            history = history[-1000:]
            
            # Save back
            with open(self.history_file, 'w') as f:
                json.dump(history, f, indent=2)
                
        except Exception as e:
            logger.error(f"Failed to log consent decision: {e}")
    
    def revoke_consent(self, action: str, target: str = None):
        """Revoke stored consent for an action."""
        if target:
            action_hash = self._hash_action(action, target)
            if action_hash in self._consents:
                del self._consents[action_hash]
                self._save_consents()
        else:
            # Revoke all consents for this action type
            to_remove = [h for h, c in self._consents.items() if c.get("action") == action]
            for hash_key in to_remove:
                del self._consents[hash_key]
            if to_remove:
                self._save_consents()
    
    def clear_all_consents(self):
        """Clear all stored consents."""
        self._consents = {}
        self._save_consents()

class CapabilityManager:
    """Manages enabled capabilities and feature flags."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path.home() / ".agent_desktop_ai"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        self.capabilities_file = self.config_dir / "capabilities.json"
        self._load_capabilities()
    
    def _load_capabilities(self):
        """Load capability settings."""
        default_capabilities = {
            "fs": False,                  # File system access
            "process_control": False,     # Process management
            "window_control": True,       # Window/GUI control
            "browser_control": True,      # Browser automation
            "run_shell": False,          # Shell command execution
            "network": True,             # Network access
            "clipboard": True,           # Clipboard access
            "screenshot": True,          # Screen capture
            "microphone": True,          # Voice input
            "system_info": True          # System information
        }
        
        try:
            if self.capabilities_file.exists():
                with open(self.capabilities_file, 'r') as f:
                    loaded = json.load(f)
                    # Merge with defaults to handle new capabilities
                    default_capabilities.update(loaded)
            
            self._capabilities = default_capabilities
            
        except Exception as e:
            logger.error(f"Failed to load capabilities: {e}")
            self._capabilities = default_capabilities
        
        # Always save to ensure file exists with all capabilities
        self._save_capabilities()
    
    def _save_capabilities(self):
        """Save capability settings."""
        try:
            with open(self.capabilities_file, 'w') as f:
                json.dump(self._capabilities, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save capabilities: {e}")
    
    def get_capabilities(self) -> Dict[str, bool]:
        """Get current capability settings."""
        return self._capabilities.copy()
    
    def is_enabled(self, capability: str) -> bool:
        """Check if a capability is enabled."""
        return self._capabilities.get(capability, False)
    
    def enable_capability(self, capability: str):
        """Enable a specific capability."""
        if capability in self._capabilities:
            self._capabilities[capability] = True
            self._save_capabilities()
            logger.info(f"Enabled capability: {capability}")
    
    def disable_capability(self, capability: str):
        """Disable a specific capability."""
        if capability in self._capabilities:
            self._capabilities[capability] = False
            self._save_capabilities()
            logger.info(f"Disabled capability: {capability}")
    
    def update_capabilities(self, updates: Dict[str, bool]):
        """Update multiple capabilities at once."""
        for capability, enabled in updates.items():
            if capability in self._capabilities:
                self._capabilities[capability] = enabled
        
        self._save_capabilities()
        logger.info(f"Updated capabilities: {updates}")
    
    def get_capability_description(self, capability: str) -> str:
        """Get description of what a capability allows."""
        descriptions = {
            "fs": "File system access - read, write, and modify files",
            "process_control": "Process management - view and control running processes",
            "window_control": "Window and GUI control - focus windows, click, type",
            "browser_control": "Browser automation - open URLs, control web pages",
            "run_shell": "Shell command execution - run system commands",
            "network": "Network access - make web requests",
            "clipboard": "Clipboard access - read and write clipboard content",
            "screenshot": "Screen capture - take screenshots",
            "microphone": "Voice input - record and process audio",
            "system_info": "System information - CPU, memory, disk usage"
        }
        
        return descriptions.get(capability, "Unknown capability")

# Safe path manager
class SafePathManager:
    """Manages safe paths for file system operations."""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            config_dir = Path.home() / ".agent_desktop_ai"
        
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # Default safe paths
        self.safe_paths = [
            str(Path.home() / "Documents"),
            str(Path.home() / "Downloads"),
            str(Path.home() / "Desktop"),
            str(Path.home() / "Projects"),
            str(self.config_dir)
        ]
        
        # Load custom safe paths if they exist
        safe_paths_file = self.config_dir / "safe_paths.json"
        if safe_paths_file.exists():
            try:
                with open(safe_paths_file, 'r') as f:
                    custom_paths = json.load(f)
                    self.safe_paths.extend(custom_paths)
            except Exception as e:
                logger.error(f"Failed to load safe paths: {e}")
    
    def is_safe_path(self, path: str) -> bool:
        """Check if a path is within the safe directories."""
        try:
            path_obj = Path(path).resolve()
            
            for safe_path in self.safe_paths:
                safe_path_obj = Path(safe_path).resolve()
                try:
                    path_obj.relative_to(safe_path_obj)
                    return True
                except ValueError:
                    continue
            
            return False
            
        except Exception as e:
            logger.error(f"Path safety check failed: {e}")
            return False
    
    def add_safe_path(self, path: str):
        """Add a new safe path."""
        if os.path.exists(path) and path not in self.safe_paths:
            self.safe_paths.append(str(Path(path).resolve()))
    
    def get_safe_paths(self) -> List[str]:
        """Get list of all safe paths."""
        return self.safe_paths.copy()
