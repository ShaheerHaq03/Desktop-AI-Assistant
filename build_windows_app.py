#!/usr/bin/env python3
"""
Build script for creating Windows executable of Agent Desktop AI Extended.
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path

def check_requirements():
    """Check if required dependencies are installed."""
    try:
        import PyInstaller
        print("✓ PyInstaller found")
    except ImportError:
        print("❌ PyInstaller not found. Installing...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
        print("✓ PyInstaller installed")
    
    # Check if UPX is available (optional, for smaller executables)
    try:
        subprocess.check_output(["upx", "--version"], stderr=subprocess.STDOUT)
        print("✓ UPX found (will compress executable)")
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("⚠ UPX not found (executable will be larger)")
        return False

def create_spec_file():
    """Create PyInstaller spec file for Windows app."""
    spec_content = '''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['windows_app.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('config', 'config'),
        ('core', 'core'),
        ('commands', 'commands'),
        ('utils', 'utils'),
        ('mic_input', 'mic_input'),
        ('README.md', '.'),
        ('QUICKSTART.md', '.'),
        ('requirements.txt', '.'),
    ],
    hiddenimports=[
        'asyncio',
        'tkinter',
        'tkinter.ttk',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.filedialog',
        'threading',
        'json',
        'platform',
        'datetime',
        'webbrowser',
        'psutil',
        'requests',
        'httpx',
        'pathlib',
        # Core modules
        'core.llm_client',
        'core.intent_parser', 
        'core.task_router',
        'core.safety',
        # Command modules
        'commands.open_apps',
        'commands.fs_manager',
        'commands.process_manager',
        'commands.window_control',
        # Utils
        'utils.logger',
        # Optional voice modules
        'sounddevice',
        'vosk',
        'numpy',
        'scipy',
        # Optional GUI modules
        'pyautogui',
        'pygetwindow',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'streamlit',
        'matplotlib',
        'pandas',
        'jupyter',
        'notebook',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='AgentDesktopAI',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,  # Enable UPX compression if available
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # No console window for GUI app
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    version='version_info.txt',
    icon='icon.ico',  # App icon if available
)
'''
    
    with open('AgentDesktopAI.spec', 'w') as f:
        f.write(spec_content)
    
    print("✓ Created AgentDesktopAI.spec")

def create_version_info():
    """Create version info file for Windows executable."""
    version_info = '''# UTF-8
#
# For more details about fixed file info 'ffi' see:
# http://msdn.microsoft.com/en-us/library/ms646997.aspx
VSVersionInfo(
  ffi=FixedFileInfo(
    filevers=(1,0,0,0),
    prodvers=(1,0,0,0),
    mask=0x3f,
    flags=0x0,
    OS=0x40004,
    fileType=0x1,
    subtype=0x0,
    date=(0, 0)
  ),
  kids=[
    StringFileInfo([
      StringTable(
        u'040904B0',
        [StringStruct(u'CompanyName', u'Agent Desktop AI Extended'),
         StringStruct(u'FileDescription', u'Local AI Assistant with Safety Controls'),
         StringStruct(u'FileVersion', u'1.0.0.0'),
         StringStruct(u'InternalName', u'AgentDesktopAI'),
         StringStruct(u'LegalCopyright', u'© 2024 Agent Desktop AI Extended Project'),
         StringStruct(u'OriginalFilename', u'AgentDesktopAI.exe'),
         StringStruct(u'ProductName', u'Agent Desktop AI Extended'),
         StringStruct(u'ProductVersion', u'1.0.0.0')])
      ]),
    VarFileInfo([VarStruct(u'Translation', [1033, 1200])])
  ]
)
'''
    
    with open('version_info.txt', 'w') as f:
        f.write(version_info)
    
    print("✓ Created version_info.txt")

def create_app_icon():
    """Create a simple app icon (if needed)."""
    # This is a placeholder - you would typically have an actual .ico file
    # For now, we'll just note that an icon should be placed here
    icon_path = Path("icon.ico")
    if not icon_path.exists():
        print("⚠ No icon.ico found - executable will use default icon")
        print("  To add custom icon: place 'icon.ico' in project directory")
    else:
        print("✓ Found icon.ico")

def build_executable(use_upx=False):
    """Build the Windows executable."""
    print("🔨 Building Windows executable...")
    
    # Clean previous builds
    if os.path.exists("dist"):
        shutil.rmtree("dist")
        print("✓ Cleaned previous dist directory")
    
    if os.path.exists("build"):
        shutil.rmtree("build")
        print("✓ Cleaned previous build directory")
    
    # Build command
    cmd = [
        sys.executable, "-m", "PyInstaller",
        "AgentDesktopAI.spec",
        "--clean",
        "--noconfirm"
    ]
    
    if not use_upx:
        cmd.append("--noupx")
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("✓ Build completed successfully!")
        
        # Check output
        exe_path = Path("dist/AgentDesktopAI.exe")
        if exe_path.exists():
            size_mb = exe_path.stat().st_size / (1024 * 1024)
            print(f"✓ Executable created: {exe_path} ({size_mb:.1f} MB)")
            return True
        else:
            print("❌ Executable not found in dist directory")
            return False
            
    except subprocess.CalledProcessError as e:
        print(f"❌ Build failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def create_installer_script():
    """Create a simple batch installer script."""
    installer_content = '''@echo off
echo Agent Desktop AI Extended - Windows Installer
echo.

REM Create application directory
set APP_DIR=%USERPROFILE%\\AppData\\Local\\AgentDesktopAI
if not exist "%APP_DIR%" mkdir "%APP_DIR%"

REM Copy executable
echo Copying application files...
copy "AgentDesktopAI.exe" "%APP_DIR%\\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy application files
    pause
    exit /b 1
)

REM Create desktop shortcut
echo Creating desktop shortcut...
set SHORTCUT=%USERPROFILE%\\Desktop\\Agent Desktop AI.lnk
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%SHORTCUT%'); $Shortcut.TargetPath = '%APP_DIR%\\AgentDesktopAI.exe'; $Shortcut.WorkingDirectory = '%APP_DIR%'; $Shortcut.Description = 'Agent Desktop AI Extended - Local AI Assistant'; $Shortcut.Save()"

REM Create start menu shortcut
echo Creating start menu shortcut...
set START_MENU=%APPDATA%\\Microsoft\\Windows\\Start Menu\\Programs
set START_SHORTCUT=%START_MENU%\\Agent Desktop AI.lnk
powershell -Command "$WshShell = New-Object -comObject WScript.Shell; $Shortcut = $WshShell.CreateShortcut('%START_SHORTCUT%'); $Shortcut.TargetPath = '%APP_DIR%\\AgentDesktopAI.exe'; $Shortcut.WorkingDirectory = '%APP_DIR%'; $Shortcut.Description = 'Agent Desktop AI Extended - Local AI Assistant'; $Shortcut.Save()"

echo.
echo Installation completed successfully!
echo.
echo Application installed to: %APP_DIR%
echo Desktop shortcut created: %USERPROFILE%\\Desktop\\Agent Desktop AI.lnk
echo Start menu shortcut created
echo.
echo You can now run the application from:
echo - Desktop shortcut
echo - Start menu
echo - Directly: %APP_DIR%\\AgentDesktopAI.exe
echo.
pause
'''
    
    with open('dist/install.bat', 'w') as f:
        f.write(installer_content)
    
    print("✓ Created install.bat installer script")

def create_readme():
    """Create README for the distribution."""
    readme_content = '''# Agent Desktop AI Extended - Windows Application

## What's Included

- `AgentDesktopAI.exe` - Main application executable
- `install.bat` - Installer script (optional)
- This README file

## Quick Start

### Option 1: Direct Run
1. Double-click `AgentDesktopAI.exe` to run the application
2. The application will create its configuration directory automatically

### Option 2: Install (Recommended)
1. Right-click `install.bat` and select "Run as administrator"
2. Follow the installation prompts
3. Use desktop or start menu shortcuts to launch the app

## First Use

1. The application starts in **SAFE MODE** by default
2. All commands are simulated - no actual system changes
3. Try these commands:
   - "What time is it?"
   - "Show system status" 
   - "Help"

## Enabling Features

### For AI Intelligence (Optional):
1. Install Ollama from https://ollama.ai
2. Run: `ollama pull gemma3:12b`
3. Run: `ollama serve`

### For Voice Control (Optional):
1. Install Python audio dependencies
2. Download Vosk models

## Safety Features

- 🛡️ **Dry Run Mode**: Actions simulated by default
- 🔧 **Capabilities**: Enable only needed features
- 📊 **Logging**: Complete audit trail
- 🏠 **Safe Paths**: File access restrictions

## System Requirements

- Windows 10/11 (64-bit)
- 4GB RAM minimum (8GB recommended with AI)
- 100MB disk space for app (+ space for AI models)

## Troubleshooting

### Application Won't Start
- Try running as administrator
- Check Windows Defender/antivirus exclusions
- Ensure .NET Framework is installed

### Voice Features Not Working
- Check microphone permissions
- Install voice dependencies separately
- Use text input as alternative

### Ollama Connection Issues
- Ensure Ollama is installed and running
- Check http://localhost:11434/api/tags
- Application works without Ollama (fallback mode)

## Support

This is the Windows desktop version of Agent Desktop AI Extended.
For documentation and source code, visit the project repository.

Version: 1.0.0
Built: {build_date}
'''
    
    from datetime import datetime
    
    with open('dist/README.txt', 'w') as f:
        f.write(readme_content.format(build_date=datetime.now().strftime("%Y-%m-%d")))
    
    print("✓ Created README.txt for distribution")

def main():
    """Main build process."""
    print("🚀 Agent Desktop AI Extended - Windows Build Process")
    print("=" * 60)
    
    # Check requirements
    use_upx = check_requirements()
    
    # Create build files
    create_spec_file()
    create_version_info()
    create_app_icon()
    
    # Build executable
    if build_executable(use_upx):
        # Create distribution extras
        create_installer_script()
        create_readme()
        
        print("\n" + "=" * 60)
        print("🎉 BUILD COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nFiles created in 'dist' directory:")
        print("- AgentDesktopAI.exe (main application)")
        print("- install.bat (installer script)")
        print("- README.txt (user instructions)")
        print("\nTo distribute:")
        print("1. Zip the entire 'dist' directory")
        print("2. Users can run AgentDesktopAI.exe directly")
        print("3. Or use install.bat for system installation")
        print("\n✅ Ready for distribution!")
    else:
        print("\n❌ BUILD FAILED!")
        print("Check error messages above for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
