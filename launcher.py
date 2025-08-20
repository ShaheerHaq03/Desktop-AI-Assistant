#!/usr/bin/env python3
"""
Agent Desktop AI Extended - Application Launcher
Choose between Streamlit web GUI or native Windows desktop GUI.
"""

import sys
import os
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

class LauncherWindow:
    """Simple launcher window to choose interface type."""
    
    def __init__(self):
        self.root = tk.Tk()
        self.setup_window()
        self.create_ui()
    
    def setup_window(self):
        """Configure the launcher window."""
        self.root.title("🚀 Agent Desktop AI Extended - Launcher")
        self.root.geometry("500x400")
        # Allow user to resize the launcher window
        self.root.resizable(True, True)
        self.root.minsize(500, 400)
        
        # Center the window
        self.root.eval('tk::PlaceWindow . center')
        
        # Configure for modern appearance
        self.root.configure(bg='#f0f0f0')
        
        try:
            # Set icon if available
            self.root.iconbitmap("icon.ico")
        except:
            pass
    
    def create_ui(self):
        """Create the launcher interface."""
        # Main container with padding
        main_frame = ttk.Frame(self.root, padding=20)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Header
        title_label = ttk.Label(
            main_frame, 
            text="🤖 Agent Desktop AI Extended",
            font=('Segoe UI', 16, 'bold')
        )
        title_label.pack(pady=(0, 10))
        
        subtitle_label = ttk.Label(
            main_frame,
            text="Local AI Assistant with Safety Controls",
            font=('Segoe UI', 10)
        )
        subtitle_label.pack(pady=(0, 30))
        
        # Interface selection
        selection_frame = ttk.LabelFrame(main_frame, text="Choose Interface", padding=15)
        selection_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Windows Desktop App option
        desktop_frame = ttk.Frame(selection_frame)
        desktop_frame.pack(fill=tk.X, pady=(0, 15))
        
        desktop_btn = ttk.Button(
            desktop_frame,
            text="🖥️ Windows Desktop App",
            command=self.launch_desktop_app,
            width=30
        )
        desktop_btn.pack(side=tk.LEFT)
        
        desktop_desc = ttk.Label(
            desktop_frame,
            text="Native Windows application with modern UI",
            font=('Segoe UI', 9),
            foreground='gray'
        )
        desktop_desc.pack(side=tk.LEFT, padx=(10, 0))
        
        # Web App option
        web_frame = ttk.Frame(selection_frame)
        web_frame.pack(fill=tk.X, pady=(0, 15))
        
        web_btn = ttk.Button(
            web_frame,
            text="🌐 Web Interface (Streamlit)",
            command=self.launch_web_app,
            width=30
        )
        web_btn.pack(side=tk.LEFT)
        
        web_desc = ttk.Label(
            web_frame,
            text="Browser-based interface (requires browser)",
            font=('Segoe UI', 9),
            foreground='gray'
        )
        web_desc.pack(side=tk.LEFT, padx=(10, 0))
        
        # CLI option
        cli_frame = ttk.Frame(selection_frame)
        cli_frame.pack(fill=tk.X)
        
        cli_btn = ttk.Button(
            cli_frame,
            text="💻 Command Line Interface",
            command=self.launch_cli,
            width=30
        )
        cli_btn.pack(side=tk.LEFT)
        
        cli_desc = ttk.Label(
            cli_frame,
            text="Text-based terminal interface",
            font=('Segoe UI', 9),
            foreground='gray'
        )
        cli_desc.pack(side=tk.LEFT, padx=(10, 0))
        
        # Status section
        status_frame = ttk.LabelFrame(main_frame, text="System Status", padding=15)
        status_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 20))
        
        # Check dependencies
        self.status_text = tk.Text(status_frame, height=6, wrap=tk.WORD, state=tk.DISABLED, 
                                  font=('Consolas', 9), bg='#f8f8f8')
        self.status_text.pack(fill=tk.BOTH, expand=True)
        
        self.check_system_status()
        
        # Bottom buttons
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X)
        
        ttk.Button(
            button_frame,
            text="📖 Documentation",
            command=self.show_documentation
        ).pack(side=tk.LEFT)
        
        ttk.Button(
            button_frame,
            text="⚙️ Settings",
            command=self.show_settings
        ).pack(side=tk.LEFT, padx=(10, 0))
        
        ttk.Button(
            button_frame,
            text="❌ Exit",
            command=self.root.quit
        ).pack(side=tk.RIGHT)
    
    def check_system_status(self):
        """Check system status and dependencies."""
        self.status_text.config(state=tk.NORMAL)
        self.status_text.delete(1.0, tk.END)
        
        status_messages = []
        
        # Check Python version
        import platform
        python_version = platform.python_version()
        status_messages.append(f"✓ Python {python_version}")
        
        # Check core dependencies
        try:
            import psutil
            status_messages.append("✓ System monitoring (psutil)")
        except ImportError:
            status_messages.append("❌ System monitoring (psutil) - install with: pip install psutil")
        
        try:
            import requests
            status_messages.append("✓ HTTP client (requests)")
        except ImportError:
            status_messages.append("❌ HTTP client (requests) - install with: pip install requests")
        
        try:
            import streamlit
            status_messages.append("✓ Web interface (streamlit)")
        except ImportError:
            status_messages.append("⚠ Web interface (streamlit) - install with: pip install streamlit")
        
        # Check Ollama
        try:
            import subprocess
            result = subprocess.run(['ollama', 'list'], capture_output=True, timeout=5)
            if result.returncode == 0:
                status_messages.append("✓ Ollama AI service available")
            else:
                status_messages.append("⚠ Ollama installed but not responding")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            status_messages.append("⚠ Ollama not installed - install from https://ollama.ai")
        except Exception:
            status_messages.append("⚠ Ollama status unknown")
        
        # Check voice dependencies
        try:
            import sounddevice
            import vosk
            status_messages.append("✓ Voice recognition available")
        except ImportError:
            status_messages.append("⚠ Voice recognition - install with: pip install sounddevice vosk")
        
        # Display status
        for message in status_messages:
            self.status_text.insert(tk.END, message + "\n")
        
        self.status_text.config(state=tk.DISABLED)
    
    def launch_desktop_app(self):
        """Launch the native Windows desktop application."""
        try:
            # Check if windows_app.py exists
            if not Path("windows_app.py").exists():
                messagebox.showerror(
                    "File Not Found",
                    "windows_app.py not found in current directory.\nPlease ensure all files are present."
                )
                return
            
            # Launch the Windows desktop app
            subprocess.Popen([sys.executable, "windows_app.py"])
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch desktop app:\n{str(e)}")
    
    def launch_web_app(self):
        """Launch the Streamlit web interface."""
        try:
            # Check if streamlit is available
            try:
                import streamlit
            except ImportError:
                messagebox.showerror(
                    "Streamlit Not Found",
                    "Streamlit is required for web interface.\nInstall with: pip install streamlit"
                )
                return
            
            # Check if main.py or start.py exists
            if Path("start.py").exists():
                subprocess.Popen([sys.executable, "start.py"])
            elif Path("main.py").exists():
                subprocess.Popen([sys.executable, "main.py"])
            else:
                messagebox.showerror(
                    "File Not Found",
                    "Neither start.py nor main.py found.\nPlease ensure all files are present."
                )
                return
            
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch web app:\n{str(e)}")
    
    def launch_cli(self):
        """Launch the command line interface."""
        try:
            # Launch CLI in a new command prompt window
            if os.name == 'nt':  # Windows
                if Path("start.py").exists():
                    subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', f'python start.py --simulate "help"'])
                elif Path("main.py").exists():
                    subprocess.Popen(['cmd', '/c', 'start', 'cmd', '/k', f'python main.py --simulate "help"'])
                else:
                    messagebox.showerror("File Not Found", "No suitable entry point found for CLI mode.")
                    return
            else:
                # For other platforms
                subprocess.Popen([sys.executable, "start.py", "--simulate", "help"])
            
            self.root.quit()
            
        except Exception as e:
            messagebox.showerror("Launch Error", f"Failed to launch CLI:\n{str(e)}")
    
    def show_documentation(self):
        """Show documentation options."""
        doc_window = tk.Toplevel(self.root)
        doc_window.title("Documentation")
        doc_window.geometry("400x300")
        doc_window.resizable(False, False)
        
        # Center the window
        doc_window.transient(self.root)
        doc_window.grab_set()
        
        frame = ttk.Frame(doc_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="📖 Documentation", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        
        # Available documentation
        docs = [
            ("README.md", "Complete project documentation"),
            ("QUICKSTART.md", "Quick start guide"),
            ("INSTALL.md", "Installation instructions"),
        ]
        
        for doc_file, description in docs:
            doc_frame = ttk.Frame(frame)
            doc_frame.pack(fill=tk.X, pady=5)
            
            if Path(doc_file).exists():
                btn = ttk.Button(
                    doc_frame,
                    text=f"📄 {doc_file}",
                    command=lambda f=doc_file: self.open_file(f)
                )
                btn.pack(side=tk.LEFT)
                
                ttk.Label(doc_frame, text=description, foreground='gray').pack(side=tk.LEFT, padx=(10, 0))
            else:
                ttk.Label(doc_frame, text=f"❌ {doc_file} (not found)", foreground='red').pack()
        
        ttk.Button(frame, text="Close", command=doc_window.destroy).pack(pady=20)
    
    def open_file(self, filename):
        """Open a file with the default system application."""
        try:
            if os.name == 'nt':  # Windows
                os.startfile(filename)
            else:  # macOS and Linux
                subprocess.call(['open' if sys.platform == 'darwin' else 'xdg-open', filename])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open {filename}:\n{str(e)}")
    
    def show_settings(self):
        """Show basic settings dialog."""
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("350x200")
        settings_window.resizable(False, False)
        
        # Center the window
        settings_window.transient(self.root)
        settings_window.grab_set()
        
        frame = ttk.Frame(settings_window, padding=20)
        frame.pack(fill=tk.BOTH, expand=True)
        
        ttk.Label(frame, text="⚙️ Settings", font=('Segoe UI', 14, 'bold')).pack(pady=(0, 20))
        
        ttk.Label(frame, text="Configuration is handled within each interface.", 
                 foreground="gray").pack(pady=10)
        
        ttk.Label(frame, text="• Desktop App: Settings button in sidebar", 
                 foreground="gray").pack(anchor=tk.W, pady=2)
        
        ttk.Label(frame, text="• Web Interface: Sidebar controls", 
                 foreground="gray").pack(anchor=tk.W, pady=2)
        
        ttk.Label(frame, text="• CLI: Command line arguments", 
                 foreground="gray").pack(anchor=tk.W, pady=2)
        
        ttk.Button(frame, text="Close", command=settings_window.destroy).pack(pady=20)
    
    def run(self):
        """Start the launcher."""
        try:
            self.root.mainloop()
        except KeyboardInterrupt:
            self.root.quit()


def main():
    """Main entry point for the launcher."""
    try:
        launcher = LauncherWindow()
        launcher.run()
    except Exception as e:
        # Fallback if GUI fails
        print("GUI launcher failed, using command line fallback:")
        print(f"Error: {e}")
        print("\nAvailable options:")
        print("1. python windows_app.py    # Windows Desktop App")
        print("2. python start.py          # Web Interface")  
        print("3. python start.py --simulate 'help'  # CLI Mode")
        
        choice = input("\nEnter choice (1-3) or press Enter to exit: ").strip()
        
        if choice == "1":
            subprocess.run([sys.executable, "windows_app.py"])
        elif choice == "2":
            subprocess.run([sys.executable, "start.py"])
        elif choice == "3":
            subprocess.run([sys.executable, "start.py", "--simulate", "help"])
        
        sys.exit(0)


if __name__ == "__main__":
    main()
