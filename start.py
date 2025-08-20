#!/usr/bin/env python3
"""
Simple startup script for Agent Desktop AI Extended
Handles missing dependencies gracefully
"""

import subprocess
import sys
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed."""
    missing = []
    
    try:
        import streamlit
    except ImportError:
        missing.append("streamlit")
    
    try:
        import psutil
    except ImportError:
        missing.append("psutil")
    
    try:
        import requests
    except ImportError:
        missing.append("requests")
    
    return missing

def install_dependencies(packages):
    """Install missing dependencies."""
    print(f"Installing missing dependencies: {', '.join(packages)}")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install"] + packages)
        print("✅ Dependencies installed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def main():
    """Main startup function."""
    print("🤖 Agent Desktop AI Extended - Startup")
    print("=" * 50)
    
    # Check current directory
    if not Path("main.py").exists():
        print("❌ main.py not found in current directory")
        print("Please run this script from the agent-desktop-ai-extended directory")
        return 1
    
    # Check dependencies
    missing = check_dependencies()
    if missing:
        print(f"⚠️  Missing dependencies: {', '.join(missing)}")
        
        install = input("Install missing dependencies? (y/n): ").lower().strip()
        if install in ['y', 'yes']:
            if not install_dependencies(missing):
                return 1
        else:
            print("❌ Cannot start without required dependencies")
            return 1
    
    # Check for CLI arguments
    if len(sys.argv) > 1:
        print("🔧 Running in CLI mode...")
        try:
            subprocess.run([sys.executable, "main.py"] + sys.argv[1:])
        except KeyboardInterrupt:
            print("\n👋 Goodbye!")
        return 0
    
    # Start GUI mode
    print("🌐 Starting Streamlit GUI...")
    print("📝 Note: Ollama and Vosk are optional - basic functionality will work without them")
    print("🔗 The app will open in your browser automatically")
    print("\nPress Ctrl+C to stop the application\n")
    
    try:
        # Try different ports if 8501 is busy
        import socket
        
        def is_port_free(port):
            """Check if a port is available."""
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.bind(('localhost', port))
                    return True
            except OSError:
                return False
        
        # Find an available port
        port_found = None
        for port in [8501, 8502, 8503, 8504, 8505]:
            if is_port_free(port):
                port_found = port
                break
            else:
                print(f"⚠️  Port {port} is busy, trying next...")
        
        if not port_found:
            print("❌ No available ports found. Try running: python fix_issues.py")
            return 1
        
        print(f"✅ Using port {port_found}")
        
        # Start Streamlit
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "main.py", 
            "--server.port", str(port_found),
            "--server.headless", "false",
            "--browser.gatherUsageStats", "false"
        ])
        
    except KeyboardInterrupt:
        print("\n👋 Goodbye!")
    except FileNotFoundError:
        print("❌ Streamlit not found. Please install it with: pip install streamlit")
        return 1
    except Exception as e:
        print(f"❌ Error starting Streamlit: {e}")
        print("💡 Try running: python fix_issues.py")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
