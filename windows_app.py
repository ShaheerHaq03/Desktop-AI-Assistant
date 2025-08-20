#!/usr/bin/env python3
"""
Agent Desktop AI Extended - Windows Desktop Application
A native Windows desktop application with modern UI using tkinter.
"""

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox, filedialog
import asyncio
import threading
import json
import platform
import os
import sys
from pathlib import Path
from datetime import datetime
import webbrowser

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from core.llm_client import OllamaClient
from core.intent_parser import IntentParser
from core.task_router import TaskRouter
from core.safety import SafetyManager, CapabilityManager

try:
    from mic_input.listen import VoiceRecorder
except ImportError:
    class VoiceRecorder:
        def __init__(self):
            pass
        def is_available(self):
            return False
        async def record_audio(self):
            return None
        async def transcribe(self, audio_file):
            return None

from utils.logger import HistoryLogger


class ModernScrolledText(scrolledtext.ScrolledText):
    """Enhanced scrolled text widget with modern appearance."""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        self.configure(
            font=('Segoe UI', 10),
            wrap=tk.WORD,
            padx=10,
            pady=10,
            selectbackground='#0078d4',
            insertbackground='#000000'
        )


class StatusBar(ttk.Frame):
    """Status bar widget for the bottom of the application."""
    
    def __init__(self, parent):
        super().__init__(parent, relief=tk.SUNKEN, borderwidth=1)
        self.status_var = tk.StringVar()
        self.status_var.set("Ready")
        
        self.status_label = ttk.Label(self, textvariable=self.status_var, anchor=tk.W)
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # System info on the right
        self.system_info = ttk.Label(
            self, 
            text=f"Windows • Python {platform.python_version()}", 
            anchor=tk.E
        )
        self.system_info.pack(side=tk.RIGHT, padx=5)
    
    def set_status(self, message):
        """Update status message."""
        self.status_var.set(message)
        self.update()


class AgentDesktopWindows:
    """Windows desktop application for Agent Desktop AI Extended."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.setup_styles()
        
        # Initialize AI components
        self.dry_run = True
        self.logger = HistoryLogger()
        self.safety_manager = SafetyManager()
        self.capability_manager = CapabilityManager()
        self.llm_client = OllamaClient()
        self.intent_parser = IntentParser(self.llm_client)
        self.task_router = TaskRouter(self.safety_manager, self.capability_manager, dry_run=self.dry_run)
        self.voice_recorder = VoiceRecorder()
        
        # Chat history
        self.chat_history = []
        
        # Create UI
        self.create_ui()
        
        # Start with a welcome message
        self.add_chat_message("Assistant", "🤖 Agent Desktop AI Extended is ready!\nType a command or click a quick action button.", "#1f77b4")
    
    def setup_window(self):
        """Configure main window."""
        self.root.title("🤖 Agent Desktop AI Extended")
        self.root.geometry("1000x700")
        self.root.minsize(800, 600)
        
        # Set icon (if available)
        try:
            self.root.iconbitmap("icon.ico")
        except:
            pass
        
        # Configure window style for modern appearance
        self.root.configure(bg='#f0f0f0')
    
    def setup_styles(self):
        """Configure modern ttk styles."""
        style = ttk.Style()
        
        # Use Windows 10/11 theme if available
        available_themes = style.theme_names()
        if 'winnative' in available_themes:
            style.theme_use('winnative')
        elif 'vista' in available_themes:
            style.theme_use('vista')
        else:
            style.theme_use('default')
        
        # Configure custom styles
        style.configure('Header.TLabel', font=('Segoe UI', 12, 'bold'))
        style.configure('Subheader.TLabel', font=('Segoe UI', 10, 'bold'))
        style.configure('Action.TButton', font=('Segoe UI', 9))
        style.configure('Danger.TButton', background='#d73527', foreground='white')
        style.configure('Success.TButton', background='#107c10', foreground='white')
    
    def create_ui(self):
        """Create the main user interface."""
        # Main container
        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Header
        header_frame = ttk.Frame(main_frame)
        header_frame.pack(fill=tk.X, pady=(0, 10))
        
        title_label = ttk.Label(header_frame, text="🤖 Agent Desktop AI Extended", style='Header.TLabel')
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = ttk.Label(header_frame, text="Local AI Assistant with Safety Controls")
        subtitle_label.pack(side=tk.LEFT, padx=(10, 0))
        
        # Main content area
        content_frame = ttk.Frame(main_frame)
        content_frame.pack(fill=tk.BOTH, expand=True)
        
        # Left panel - Chat
        chat_frame = ttk.LabelFrame(content_frame, text="💬 Chat", padding=10)
        chat_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        # Chat display
        self.chat_display = ModernScrolledText(
            chat_frame, 
            height=20, 
            state=tk.DISABLED,
            bg='white',
            fg='black'
        )
        self.chat_display.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Input area
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X)
        
        self.command_var = tk.StringVar()
        command_entry = ttk.Entry(input_frame, textvariable=self.command_var, font=('Segoe UI', 10))
        command_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        command_entry.bind('<Return>', lambda e: self.send_command())
        
        send_button = ttk.Button(input_frame, text="Send", command=self.send_command, style='Action.TButton')
        send_button.pack(side=tk.RIGHT)
        
        # Voice button
        voice_button = ttk.Button(input_frame, text="🎤", command=self.voice_command, width=4)
        voice_button.pack(side=tk.RIGHT, padx=(0, 5))
        
        # Right panel - Controls
        control_frame = ttk.Frame(content_frame)
        control_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(5, 0))
        
        # Safety controls
        safety_frame = ttk.LabelFrame(control_frame, text="🛡️ Safety", padding=10)
        safety_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.dry_run_var = tk.BooleanVar(value=True)
        dry_run_check = ttk.Checkbutton(
            safety_frame, 
            text="Dry Run Mode (Safe)", 
            variable=self.dry_run_var,
            command=self.toggle_dry_run
        )
        dry_run_check.pack(anchor=tk.W)
        
        self.safety_status = ttk.Label(safety_frame, text="🛡️ Safe mode enabled", foreground='green')
        self.safety_status.pack(anchor=tk.W, pady=(5, 0))
        
        # Capabilities
        capabilities_frame = ttk.LabelFrame(control_frame, text="🔧 Capabilities", padding=10)
        capabilities_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.capability_vars = {}
        capabilities = self.capability_manager.get_capabilities()
        
        for cap_name, cap_enabled in capabilities.items():
            var = tk.BooleanVar(value=cap_enabled)
            self.capability_vars[cap_name] = var
            
            # Create readable names
            readable_names = {
                "fs": "📁 File System",
                "process_control": "💻 Process Control",
                "window_control": "🪟 Window Control",
                "browser_control": "🌐 Browser Control",
                "run_shell": "⚠️ Shell Commands"
            }
            
            display_name = readable_names.get(cap_name, cap_name)
            check = ttk.Checkbutton(
                capabilities_frame,
                text=display_name,
                variable=var,
                command=self.update_capabilities
            )
            check.pack(anchor=tk.W, pady=1)
        
        # Quick actions
        actions_frame = ttk.LabelFrame(control_frame, text="⚡ Quick Actions", padding=10)
        actions_frame.pack(fill=tk.X, pady=(0, 10))
        
        quick_actions = [
            ("🕐 Current Time", "What time is it?"),
            ("💻 System Status", "Show system status"),
            ("📁 List Files", "List files in current directory"),
            ("❓ Help", "help"),
        ]
        
        for button_text, command in quick_actions:
            btn = ttk.Button(
                actions_frame,
                text=button_text,
                command=lambda cmd=command: self.quick_action(cmd),
                style='Action.TButton'
            )
            btn.pack(fill=tk.X, pady=2)
        
        # System info
        info_frame = ttk.LabelFrame(control_frame, text="📊 System Info", padding=10)
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = f"OS: {platform.system()}\nPython: {platform.python_version()}\nArchitecture: {platform.architecture()[0]}"
        info_label = ttk.Label(info_frame, text=info_text, justify=tk.LEFT)
        info_label.pack(anchor=tk.W)
        
        # Control buttons
        buttons_frame = ttk.Frame(control_frame)
        buttons_frame.pack(fill=tk.X)
        
        clear_btn = ttk.Button(buttons_frame, text="🗑️ Clear Chat", command=self.clear_chat)
        clear_btn.pack(fill=tk.X, pady=2)
        
        settings_btn = ttk.Button(buttons_frame, text="⚙️ Settings", command=self.show_settings)
        settings_btn.pack(fill=tk.X, pady=2)
        
        about_btn = ttk.Button(buttons_frame, text="ℹ️ About", command=self.show_about)
        about_btn.pack(fill=tk.X, pady=2)
        
        # Status bar
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def add_chat_message(self, sender, message, color="#000000"):
        """Add a message to the chat display."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.chat_display.config(state=tk.NORMAL)
        
        # Add timestamp and sender
        self.chat_display.insert(tk.END, f"[{timestamp}] {sender}: ", f"sender_{sender}")
        self.chat_display.tag_config(f"sender_{sender}", foreground=color, font=('Segoe UI', 10, 'bold'))
        
        # Add message
        self.chat_display.insert(tk.END, f"{message}\n\n")
        
        self.chat_display.config(state=tk.DISABLED)
        self.chat_display.see(tk.END)
        
        # Store in history
        self.chat_history.append({
            "timestamp": timestamp,
            "sender": sender,
            "message": message
        })
    
    def send_command(self):
        """Send a text command."""
        command = self.command_var.get().strip()
        if not command:
            return
        
        # Clear input
        self.command_var.set("")
        
        # Add user message
        self.add_chat_message("You", command, "#0078d4")
        
        # Process command in background
        self.status_bar.set_status("Processing command...")
        threading.Thread(target=self.process_command_async, args=(command,), daemon=True).start()
    
    def process_command_async(self, command):
        """Process command asynchronously."""
        try:
            # Run async command processing
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.process_text_command(command))
            loop.close()
            
            # Update UI in main thread
            self.root.after(0, self.handle_command_result, result)
        except Exception as e:
            error_msg = f"Error processing command: {str(e)}"
            self.root.after(0, self.handle_command_error, error_msg)
    
    def handle_command_result(self, result):
        """Handle command result in main thread."""
        if result:
            success = result.get("success", False)
            message = result.get("message", "Task processed")
            intent_type = result.get("intent_type", "")
            
            if success:
                self.add_chat_message("Assistant", f"✅ {message}", "#107c10")
                
                # Show specific content based on intent type
                if intent_type == "list_files" and result.get("files"):
                    files = result["files"]
                    if files:
                        file_list = "\n📁 Files and Folders:\n"
                        for file_info in files:
                            name = file_info.get("name", "Unknown")
                            file_type = file_info.get("type", "unknown")
                            size = file_info.get("size", 0)
                            
                            if file_type == "directory":
                                icon = "📁"
                                size_str = "(folder)"
                            else:
                                icon = "📄"
                                if size > 1024*1024:  # MB
                                    size_str = f"({size/(1024*1024):.1f} MB)"
                                elif size > 1024:  # KB
                                    size_str = f"({size/1024:.1f} KB)"
                                else:
                                    size_str = f"({size} bytes)"
                            
                            file_list += f"  {icon} {name} {size_str}\n"
                        
                        self.add_chat_message("Assistant", file_list, "#0078d4")
                
                elif intent_type == "get_system_info" and result.get("system_info"):
                    info = result["system_info"]
                    system_details = f"\n💻 System Details:\n"
                    system_details += f"  OS: {info.get('os', 'Unknown')}\n"
                    system_details += f"  CPU Usage: {info.get('cpu_percent', 0)}%\n"
                    system_details += f"  Memory Usage: {info.get('memory_percent', 0)}%\n"
                    system_details += f"  Disk Usage: {info.get('disk_usage', 0)}%\n"
                    self.add_chat_message("Assistant", system_details, "#0078d4")
                
            else:
                self.add_chat_message("Assistant", f"❌ {message}", "#d73527")
            
            # Show raw details only if it's not a special case we handled above
            if result.get("details") and intent_type not in ["list_files", "get_system_info"]:
                details = json.dumps(result["details"], indent=2)
                self.add_chat_message("Assistant", f"Details:\n{details}", "#666666")
        else:
            self.add_chat_message("Assistant", "❌ Failed to process command", "#d73527")
        
        self.status_bar.set_status("Ready")
    
    def handle_command_error(self, error_msg):
        """Handle command error in main thread."""
        self.add_chat_message("Assistant", f"❌ {error_msg}", "#d73527")
        self.status_bar.set_status("Error")
    
    async def process_text_command(self, text):
        """Process a text command through the pipeline."""
        try:
            # Parse intent
            intent = await self.intent_parser.parse(text)
            
            if not intent:
                return {"success": False, "message": "Failed to understand intent"}
            
            # Execute task
            result = await self.task_router.execute(intent)
            
            # Log everything
            self.logger.log_interaction(text, intent, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing text command: {str(e)}"
            self.logger.log_error(error_msg)
            return {"success": False, "message": error_msg}
    
    def voice_command(self):
        """Handle voice command button click."""
        if not self.voice_recorder.is_available():
            messagebox.showwarning("Voice Not Available", "Voice recognition is not available. Please install voice dependencies.")
            return
        
        self.add_chat_message("Assistant", "🎤 Recording voice... Please speak now.", "#ff8c00")
        self.status_bar.set_status("Recording voice...")
        
        # Process voice command in background
        threading.Thread(target=self.process_voice_async, daemon=True).start()
    
    def process_voice_async(self):
        """Process voice command asynchronously."""
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(self.process_voice_command())
            loop.close()
            
            self.root.after(0, self.handle_voice_result, result)
        except Exception as e:
            error_msg = f"Error processing voice: {str(e)}"
            self.root.after(0, self.handle_command_error, error_msg)
    
    async def process_voice_command(self):
        """Process a voice command through the full pipeline."""
        try:
            # Record audio
            audio_file = await self.voice_recorder.record_audio()
            
            if not audio_file:
                return {"success": False, "message": "Failed to record audio"}
            
            # Transcribe
            transcription = await self.voice_recorder.transcribe(audio_file)
            
            if not transcription:
                return {"success": False, "message": "Failed to transcribe audio"}
            
            # Parse intent
            intent = await self.intent_parser.parse(transcription)
            
            if not intent:
                return {"success": False, "message": "Failed to understand intent"}
            
            # Execute task
            result = await self.task_router.execute(intent)
            
            # Log everything
            self.logger.log_interaction(transcription, intent, result)
            
            # Add transcription to result
            if result:
                result["transcription"] = transcription
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing voice command: {str(e)}"
            self.logger.log_error(error_msg)
            return {"success": False, "message": error_msg}
    
    def handle_voice_result(self, result):
        """Handle voice command result."""
        if result and result.get("transcription"):
            self.add_chat_message("You", f"🎤 {result['transcription']}", "#0078d4")
        
        self.handle_command_result(result)
    
    def quick_action(self, command):
        """Execute a quick action command."""
        self.command_var.set(command)
        self.send_command()
    
    def toggle_dry_run(self):
        """Toggle dry run mode."""
        self.dry_run = self.dry_run_var.get()
        
        # Recreate task router with new dry run setting
        self.task_router = TaskRouter(
            self.safety_manager, 
            self.capability_manager, 
            dry_run=self.dry_run
        )
        
        # Update status
        if self.dry_run:
            self.safety_status.config(text="🛡️ Safe mode enabled", foreground='green')
            self.add_chat_message("System", "🛡️ Dry run mode enabled - actions will be simulated", "#107c10")
        else:
            self.safety_status.config(text="⚠️ Live mode active", foreground='red')
            self.add_chat_message("System", "⚠️ Live mode enabled - actions will be executed!", "#d73527")
    
    def update_capabilities(self):
        """Update capability settings."""
        new_capabilities = {}
        for cap_name, var in self.capability_vars.items():
            new_capabilities[cap_name] = var.get()
        
        self.capability_manager.update_capabilities(new_capabilities)
        
        # Show enabled capabilities
        enabled = [name for name, enabled in new_capabilities.items() if enabled]
        if enabled:
            self.add_chat_message("System", f"🔧 Enabled capabilities: {', '.join(enabled)}", "#666666")
    
    def clear_chat(self):
        """Clear the chat history."""
        if messagebox.askyesno("Clear Chat", "Are you sure you want to clear the chat history?"):
            self.chat_display.config(state=tk.NORMAL)
            self.chat_display.delete(1.0, tk.END)
            self.chat_display.config(state=tk.DISABLED)
            self.chat_history.clear()
            self.add_chat_message("Assistant", "🤖 Chat cleared. How can I help you?", "#1f77b4")
    
    def show_settings(self):
        """Show settings dialog."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")
        settings_window.resizable(False, False)
        
        # Center the window
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        notebook = ttk.Notebook(settings_window)
        notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # General settings tab
        general_frame = ttk.Frame(notebook)
        notebook.add(general_frame, text="General")
        
        ttk.Label(general_frame, text="Configuration options will be added here.", 
                 foreground="gray").pack(pady=20)
        
        # Safety settings tab
        safety_frame = ttk.Frame(notebook)
        notebook.add(safety_frame, text="Safety")
        
        ttk.Label(safety_frame, text="Advanced safety options will be added here.", 
                 foreground="gray").pack(pady=20)
        
        # Close button
        close_btn = ttk.Button(settings_window, text="Close", 
                              command=settings_window.destroy)
        close_btn.pack(pady=10)
    
    def show_about(self):
        """Show about dialog."""
        about_text = """Agent Desktop AI Extended
        
A local, offline, voice-controlled personal assistant with strict safety boundaries.

Features:
• Local AI processing with Ollama
• Voice recognition with Vosk
• Safety-first design with dry-run mode
• Comprehensive system control capabilities
• Cross-platform Windows application

Version: 1.0.0
Platform: Windows
Python: {python_version}

© 2024 Agent Desktop AI Extended Project
Licensed under MIT License"""
        
        messagebox.showinfo(
            "About Agent Desktop AI Extended",
            about_text.format(python_version=platform.python_version())
        )
    
    def run(self):
        """Start the application."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.root.quit()


def main():
    """Main entry point for Windows application."""
    try:
        app = AgentDesktopWindows()
        app.run()
    except Exception as e:
        messagebox.showerror("Error", f"Failed to start application: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
