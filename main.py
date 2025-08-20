#!/usr/bin/env python3
"""
Agent Desktop AI Extended - Main Entry Point
A local, offline, multilingual voice-controlled personal assistant with strict safety boundaries.
"""

import argparse
import asyncio
import sys
import os
import json
import platform
from pathlib import Path

import streamlit as st
import subprocess

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))

from core.llm_client import OllamaClient
from core.intent_parser import IntentParser
from core.task_router import TaskRouter
from core.safety import SafetyManager, CapabilityManager
try:
    from mic_input.listen import VoiceRecorder
except ImportError:
    # Fallback when voice dependencies are not available
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

class AgentDesktopAI:
    """Main application class for the AI assistant."""
    
    def __init__(self, dry_run=True):
        self.dry_run = dry_run
        self.logger = HistoryLogger()
        self.safety_manager = SafetyManager()
        self.capability_manager = CapabilityManager()
        self.llm_client = OllamaClient()
        self.intent_parser = IntentParser(self.llm_client)
        self.task_router = TaskRouter(self.safety_manager, self.capability_manager, dry_run=dry_run)
        self.voice_recorder = VoiceRecorder()
        
    async def process_voice_command(self):
        """Process a voice command through the full pipeline."""
        try:
            # Record audio with live waveform
            st.info("🎤 Recording... Speak now!")
            volume_placeholder = st.empty()
            last_volume = {"v": 0.0}
            def on_volume(v: float):
                # Only store value from background audio thread
                try:
                    last_volume["v"] = float(v)
                except Exception:
                    pass

            # Start recording task
            record_task = asyncio.create_task(self.voice_recorder.record_audio(on_volume=on_volume))
            # UI update loop while recording
            while not record_task.done():
                level = max(0.0, min(1.0, last_volume["v"]))
                bars = int(level * 20)
                volume_placeholder.markdown("`" + ("█" * bars).ljust(20) + "`")
                await asyncio.sleep(0.1)

            audio_file = await record_task
            
            if not audio_file:
                st.error("Failed to record audio")
                return None
                
            # Transcribe
            st.info("🗣️ Transcribing...")
            transcription = await self.voice_recorder.transcribe(audio_file)
            
            if not transcription:
                st.error("Failed to transcribe audio")
                return None
                
            volume_placeholder.empty()
            st.success(f"Heard: {transcription}")
            # Add user's transcribed speech to chat history
            if 'messages' in st.session_state:
                st.session_state.messages.append({"role": "user", "content": transcription})
            
            # Parse intent
            st.info("🧠 Understanding intent...")
            intent = await self.intent_parser.parse(transcription)
            
            if not intent:
                st.error("Failed to understand intent")
                return None
                
            # Optionally show intent for debugging
            with st.expander("Parsed intent"):
                st.json(intent)
            
            # Execute task
            st.info("⚡ Executing task...")
            result = await self.task_router.execute(intent)
            
            # Log everything
            self.logger.log_interaction(transcription, intent, result)

            # Add assistant response to chat
            assistant_text = result.get("message", "Task processed") if isinstance(result, dict) else str(result)
            if 'messages' in st.session_state:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": assistant_text,
                    "result": result
                })

            return result
            
        except Exception as e:
            error_msg = f"Error processing voice command: {str(e)}"
            st.error(error_msg)
            self.logger.log_error(error_msg)
            return None
    
    async def process_text_command(self, text):
        """Process a text command through the pipeline."""
        try:
            # Parse intent
            intent = await self.intent_parser.parse(text)
            
            if not intent:
                st.error("Failed to understand intent")
                return None
                
            # Execute task
            result = await self.task_router.execute(intent)
            
            # Log everything
            self.logger.log_interaction(text, intent, result)
            
            return result
            
        except Exception as e:
            error_msg = f"Error processing text command: {str(e)}"
            st.error(error_msg)
            self.logger.log_error(error_msg)
            return None

def run_streamlit_gui():
    """Run the Streamlit GUI interface."""
    st.set_page_config(
        page_title="Agent Desktop AI Extended",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🤖 Agent Desktop AI Extended")
    st.subheader("Local, Offline, Voice-Controlled Personal Assistant")
    
    # Initialize session state
    if 'agent' not in st.session_state:
        st.session_state.agent = AgentDesktopAI(dry_run=True)
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    
    # Sidebar for settings and capabilities
    with st.sidebar:
        st.header("⚙️ Settings")
        
        # Safety mode toggle
        dry_run_mode = st.checkbox("🛡️ Dry Run Mode (Safe)", value=True, help="When enabled, actions are simulated but not executed")
        if dry_run_mode != st.session_state.agent.dry_run:
            st.session_state.agent = AgentDesktopAI(dry_run=dry_run_mode)
        
        # Capabilities
        st.header("🔧 Capabilities")
        capabilities = st.session_state.agent.capability_manager.get_capabilities()
        
        fs_enabled = st.checkbox("📁 File System", value=capabilities.get("fs", False))
        process_enabled = st.checkbox("💻 Process Control", value=capabilities.get("process_control", False))
        window_enabled = st.checkbox("🪟 Window Control", value=capabilities.get("window_control", True))
        browser_enabled = st.checkbox("🌐 Browser Control", value=capabilities.get("browser_control", True))
        shell_enabled = st.checkbox("⚠️ Shell Commands", value=capabilities.get("run_shell", False))
        
        new_capabilities = {
            "fs": fs_enabled,
            "process_control": process_enabled,
            "window_control": window_enabled,
            "browser_control": browser_enabled,
            "run_shell": shell_enabled
        }
        
        if new_capabilities != capabilities:
            st.session_state.agent.capability_manager.update_capabilities(new_capabilities)
        
        # System info
        st.header("📊 System Info")
        st.text(f"OS: {platform.system()}")
        st.text(f"Python: {platform.python_version()}")
        
        # Clear history
        if st.button("🗑️ Clear History"):
            st.session_state.messages = []
            st.rerun()
    
    # Chat interface (outside columns)
    st.header("💬 Chat")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])
            if "result" in message:
                with st.expander("Result Details"):
                    st.json(message["result"])
    
    # Text input (must be outside columns)
    if prompt := st.chat_input("Type your command here..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        # Process command
        with st.chat_message("assistant"):
            with st.spinner("Processing..."):
                result = asyncio.run(st.session_state.agent.process_text_command(prompt))
            
            if result:
                if result.get("success"):
                    st.success(result.get("message", "Task completed successfully"))
                else:
                    st.error(result.get("message", "Task failed"))
                
                # Add assistant response
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": result.get("message", "Task processed"),
                    "result": result
                })
            else:
                st.error("Failed to process command")
    
    # Action buttons and controls
    col1, col2 = st.columns([3, 1])
    
    with col2:
        # Voice input
        st.header("🎤 Voice")
        
        if 'rec_running' not in st.session_state:
            st.session_state.rec_running = False
        if 'rec_stop_event' not in st.session_state:
            st.session_state.rec_stop_event = None
        if 'rec_volume' not in st.session_state:
            st.session_state.rec_volume = 0.0

        if not st.session_state.rec_running:
            if st.button("🎙️ Record Voice Command", use_container_width=True):
                # Start async recording pipeline with a stop event
                # Use a simple flag object because Streamlit may not have a running event loop here
                class _Stop:
                    def __init__(self):
                        self._flag = False
                    def set(self):
                        self._flag = True
                    def is_set(self):
                        return self._flag
                st.session_state.rec_stop_event = _Stop()
                st.session_state.rec_running = True

                async def on_volume(v: float):
                    st.session_state.rec_volume = float(v)

                async def pipeline():
                    # Run recording with stop event and live volume updates
                    audio = await st.session_state.agent.voice_recorder.record_audio(
                        duration=60,
                        on_volume=lambda v: st.session_state.__setitem__('rec_volume', float(v)),
                        stop_event=st.session_state.rec_stop_event
                    )
                    if audio:
                        tx = await st.session_state.agent.voice_recorder.transcribe(audio)
                        if tx:
                            st.session_state.messages.append({"role": "user", "content": tx})
                            res = await st.session_state.agent.process_text_command(tx)
                            msg = res.get("message", "Task processed") if isinstance(res, dict) else str(res)
                            st.session_state.messages.append({"role": "assistant", "content": msg, "result": res})
                    st.session_state.rec_running = False
                    st.session_state.rec_volume = 0.0
                    st.session_state.rec_stop_event = None

                # Run the async pipeline from a fresh event loop in a background thread
                import threading
                def _runner():
                    import asyncio as _a
                    _a.run(pipeline())
                threading.Thread(target=_runner, daemon=True).start()
                st.rerun()
        else:
            # Show live volume and a Stop button
            vol = max(0.0, min(1.0, st.session_state.rec_volume))
            bars = int(vol * 20)
            st.markdown("`" + ("█" * bars).ljust(20) + "`")
            if st.button("⏹ Stop", use_container_width=True):
                if st.session_state.rec_stop_event is not None:
                    st.session_state.rec_stop_event.set()
            # keep UI refreshing while recording
            st.experimental_rerun()
        
        # Quick actions
        st.header("⚡ Quick Actions")
        
        if st.button("🕐 Current Time", use_container_width=True):
            result = asyncio.run(st.session_state.agent.process_text_command("What time is it?"))
        
        if st.button("💻 System Status", use_container_width=True):
            result = asyncio.run(st.session_state.agent.process_text_command("Show system status"))
        
        if st.button("📁 List Files", use_container_width=True):
            result = asyncio.run(st.session_state.agent.process_text_command("List files in current directory"))
        
        # Safety warnings
        st.header("⚠️ Safety")
        if dry_run_mode:
            st.success("🛡️ Safe mode enabled - actions are simulated")
        else:
            st.warning("⚠️ Live mode - actions will be executed!")
            
        if shell_enabled and not dry_run_mode:
            st.error("🚨 Shell commands enabled in live mode - be careful!")

def run_cli():
    """Run the CLI interface."""
    parser = argparse.ArgumentParser(description="Agent Desktop AI Extended - CLI Mode")
    parser.add_argument("--dry-run", action="store_true", default=True, help="Run in safe simulation mode")
    parser.add_argument("--run", action="store_true", help="Run in live execution mode")
    parser.add_argument("--simulate", type=str, help="Simulate a specific command")
    parser.add_argument("--enable-module", type=str, help="Enable specific modules (comma-separated)")
    
    args = parser.parse_args()
    
    # Determine run mode
    dry_run = True
    if args.run:
        dry_run = False
        print("⚠️  WARNING: Live execution mode enabled!")
        confirm = input("Are you sure you want to proceed? (yes/no): ")
        if confirm.lower() != "yes":
            print("Cancelled.")
            return
    
    # Initialize agent
    agent = AgentDesktopAI(dry_run=dry_run)
    
    # Enable specific modules if requested
    if args.enable_module:
        modules = args.enable_module.split(",")
        capabilities = agent.capability_manager.get_capabilities()
        for module in modules:
            if module.strip() in capabilities:
                capabilities[module.strip()] = True
        agent.capability_manager.update_capabilities(capabilities)
        print(f"Enabled modules: {args.enable_module}")
    
    # Handle simulation mode
    if args.simulate:
        print(f"Simulating command: {args.simulate}")
        result = asyncio.run(agent.process_text_command(args.simulate))
        if result:
            print("Result:", json.dumps(result, indent=2))
        return
    
    print("Agent Desktop AI Extended - CLI Mode")
    print("Type 'quit' to exit, 'voice' for voice input")
    print(f"Mode: {'DRY RUN' if dry_run else 'LIVE EXECUTION'}")
    
    while True:
        try:
            command = input("\n> ")
            
            if command.lower() == "quit":
                break
            elif command.lower() == "voice":
                print("Voice recording not implemented in CLI mode. Use GUI mode instead.")
                continue
            elif not command.strip():
                continue
            
            result = asyncio.run(agent.process_text_command(command))
            if result:
                print("Result:", json.dumps(result, indent=2))
                
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    # Check if we should run Streamlit GUI or CLI
    if len(sys.argv) == 1:
        # No arguments - run Streamlit GUI
        print("Starting Streamlit GUI...")
        subprocess.run([sys.executable, "-m", "streamlit", "run", __file__, "--server.port", "8501"])
    else:
        # Arguments provided - run CLI
        run_cli()

# Streamlit entry point
if "streamlit" in sys.modules:
    run_streamlit_gui()
