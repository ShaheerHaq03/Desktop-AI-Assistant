"""
Voice Recording and Transcription using Vosk (offline)
Supports multilingual offline speech recognition
"""

import asyncio
import json
import logging
import os
import wave
import time
from pathlib import Path
from typing import Optional, Dict, Any, Callable

import sounddevice as sd
import numpy as np

logger = logging.getLogger(__name__)

class VoiceRecorder:
    """Handles voice recording and offline transcription using Vosk."""
    
    def __init__(self, sample_rate: int = 16000, channels: int = 1, 
                 vosk_model_path: str = None, save_recordings: bool = True):
        self.sample_rate = sample_rate
        self.channels = channels
        self.save_recordings = save_recordings
        self.recordings_dir = Path.home() / ".agent_desktop_ai" / "recordings"
        
        if save_recordings:
            self.recordings_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize Vosk
        self.vosk_model = None
        self.vosk_rec = None
        
        # Resolve model path using precedence:
        # 1) explicit parameter, 2) VOSK_MODEL_PATH env var, 3) home dir default,
        # 4) project root 'vosk-model' folder (for local setups)
        resolved_model_path = None
        if vosk_model_path:
            resolved_model_path = Path(vosk_model_path)
        elif os.environ.get("VOSK_MODEL_PATH"):
            resolved_model_path = Path(os.environ["VOSK_MODEL_PATH"])
        else:
            home_default = Path.home() / ".agent_desktop_ai" / "vosk-model"
            project_root = Path(__file__).resolve().parent.parent  # repo root
            project_default = project_root / "vosk-model"
            if home_default.exists():
                resolved_model_path = home_default
            elif project_default.exists():
                resolved_model_path = project_default
            else:
                resolved_model_path = home_default

        self.vosk_model_path = resolved_model_path
        
        self._setup_vosk()
        
    def _setup_vosk(self):
        """Initialize Vosk speech recognition."""
        try:
            import vosk  # type: ignore
            
            if self.vosk_model_path.exists():
                effective_model_dir = self._resolve_model_dir(self.vosk_model_path)
                logger.info(f"Loading Vosk model from: {effective_model_dir}")
                self.vosk_model = vosk.Model(str(effective_model_dir))
                self.vosk_rec = vosk.KaldiRecognizer(self.vosk_model, self.sample_rate)
                logger.info("Vosk model loaded successfully")
            else:
                logger.warning(f"Vosk model not found at: {self.vosk_model_path}")
                logger.info("Please download a Vosk model from https://alphacephei.com/vosk/models")
                
        except ImportError:
            logger.error("Vosk not installed. Install with: pip install vosk")
        except Exception as e:
            logger.error(f"Failed to initialize Vosk: {e}")

    def _resolve_model_dir(self, base_path: Path) -> Path:
        """Resolve the actual model directory.

        Accepts either the model directory itself or a parent directory that
        contains exactly one subdirectory with the model files.
        """
        try:
            base_path = base_path.resolve()
            if base_path.is_dir():
                entries = list(base_path.iterdir())
                # If the directory already contains files, assume it is the model dir
                if any(entry.is_file() for entry in entries):
                    return base_path
                # If there is exactly one subdirectory, descend into it
                subdirs = [e for e in entries if e.is_dir()]
                if len(subdirs) == 1:
                    return self._resolve_model_dir(subdirs[0])
        except Exception as e:
            logger.debug(f"Model directory resolution fallback for {base_path}: {e}")
        return base_path
    
    def is_available(self) -> bool:
        """Check if voice recording is available."""
        return self.vosk_model is not None and self.vosk_rec is not None
    
    async def record_audio(self, duration: float = 5.0, 
                          silence_threshold: float = 0.01,
                          min_duration: float = 1.0,
                          on_volume: Optional[Callable[[float], None]] = None,
                          stop_event: Optional[object] = None) -> Optional[str]:
        """
        Record audio from microphone with automatic silence detection.
        
        Args:
            duration: Maximum recording duration in seconds
            silence_threshold: Silence detection threshold (0.0-1.0)
            min_duration: Minimum recording duration before silence detection
            on_volume: Optional callback receiving a float volume level (0..1+) for UI updates
            stop_event: Optional asyncio.Event to stop recording early from UI
            
        Returns:
            Path to recorded audio file or None if recording failed
        """
        try:
            logger.info(f"Starting audio recording (max {duration}s)")
            
            # Prepare recording
            audio_data = []
            silence_count = 0
            silence_limit = int(self.sample_rate * 0.5)  # 0.5 seconds of silence
            min_samples = int(self.sample_rate * min_duration)
            
            def audio_callback(indata, frames, time, status):
                """Audio input callback."""
                if status:
                    logger.warning(f"Audio input status: {status}")
                # instantaneous volume for UI
                try:
                    if on_volume is not None and frames > 0 and indata.shape[0] > 0:
                        import numpy as _np
                        chunk = indata[:, 0]
                        vol = float((_np.sqrt((_np.mean((_np.square(chunk)))))))
                        on_volume(vol)
                except Exception:
                    pass
                
                audio_data.extend(indata[:, 0].copy())
            
            # Start recording
            try:
                with sd.InputStream(
                    samplerate=self.sample_rate,
                    channels=self.channels,
                    callback=audio_callback,
                    dtype=np.float32
                ):
                    start_time = time.time()
                    
                    while time.time() - start_time < duration:
                        if stop_event is not None and stop_event.is_set():
                            logger.info("Stop requested, ending recording")
                            break
                        await asyncio.sleep(0.1)
                        
                        # Check for silence after minimum duration
                        if len(audio_data) > min_samples:
                            recent_audio = audio_data[-int(self.sample_rate * 0.1):]  # Last 0.1 seconds
                            if len(recent_audio) > 0:
                                volume = np.sqrt(np.mean(np.square(recent_audio)))
                                if on_volume is not None:
                                    try:
                                        on_volume(float(volume))
                                    except Exception:
                                        pass
                                
                                if volume < silence_threshold:
                                    silence_count += int(self.sample_rate * 0.1)
                                    if silence_count >= silence_limit:
                                        logger.info("Silence detected, stopping recording")
                                        break
                                else:
                                    silence_count = 0
            except Exception as e:
                logger.warning(f"Failed to open input stream at {self.sample_rate} Hz: {e}. Retrying with device default rate.")
                try:
                    dev_info = sd.query_devices(kind='input')
                    fallback_sr = int(dev_info.get('default_samplerate') or self.sample_rate)
                    with sd.InputStream(
                        samplerate=fallback_sr,
                        channels=self.channels,
                        callback=audio_callback,
                        dtype=np.float32
                    ):
                        start_time = time.time()
                        
                        while time.time() - start_time < duration:
                            if stop_event is not None and stop_event.is_set():
                                logger.info("Stop requested, ending recording")
                                break
                            await asyncio.sleep(0.1)
                            
                            # Check for silence after minimum duration
                            if len(audio_data) > int(fallback_sr * min_duration):
                                recent_audio = audio_data[-int(fallback_sr * 0.1):]
                                if len(recent_audio) > 0:
                                    volume = np.sqrt(np.mean(np.square(recent_audio)))
                                    if on_volume is not None:
                                        try:
                                            on_volume(float(volume))
                                        except Exception:
                                            pass
                                    if volume < silence_threshold:
                                        # 0.1s chunk
                                        silence_count += int(fallback_sr * 0.1)
                                        if silence_count >= int(fallback_sr * 0.5):
                                            logger.info("Silence detected, stopping recording")
                                            break
                                    else:
                                        silence_count = 0
                except Exception as e2:
                    logger.error(f"Audio recording failed to start: {e2}")
                    return None
            
            if not audio_data:
                logger.error("No audio data recorded")
                return None
            
            # Convert to numpy array and normalize
            audio_array = np.array(audio_data, dtype=np.float32)
            
            # Save audio file
            if self.save_recordings:
                timestamp = int(time.time())
                filename = f"recording_{timestamp}.wav"
                filepath = self.recordings_dir / filename
                
                # Save as WAV file
                with wave.open(str(filepath), 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)  # 16-bit
                    wf.setframerate(self.sample_rate)
                    
                    # Convert float32 to int16
                    audio_int16 = (audio_array * 32767).astype(np.int16)
                    wf.writeframes(audio_int16.tobytes())
                
                logger.info(f"Audio saved to: {filepath}")
                return str(filepath)
            else:
                # Return temporary file path
                temp_file = "/tmp/temp_recording.wav"
                with wave.open(temp_file, 'wb') as wf:
                    wf.setnchannels(self.channels)
                    wf.setsampwidth(2)
                    wf.setframerate(self.sample_rate)
                    
                    audio_int16 = (audio_array * 32767).astype(np.int16)
                    wf.writeframes(audio_int16.tobytes())
                
                return temp_file
                
        except Exception as e:
            logger.error(f"Audio recording failed: {e}")
            return None
    
    async def transcribe(self, audio_file: str) -> Optional[str]:
        """
        Transcribe audio file using Vosk offline speech recognition.
        
        Args:
            audio_file: Path to audio file
            
        Returns:
            Transcribed text or None if transcription failed
        """
        if not self.is_available():
            logger.error("Vosk not available for transcription")
            return None
        
        try:
            logger.info(f"Transcribing audio file: {audio_file}")
            
            # Read audio file
            with wave.open(audio_file, 'rb') as wf:
                # Verify audio format
                if wf.getframerate() != self.sample_rate:
                    logger.warning(f"Audio sample rate mismatch: {wf.getframerate()} vs {self.sample_rate}")
                
                # Read audio data in chunks
                results = []
                
                while True:
                    data = wf.readframes(4000)  # Read in chunks
                    if len(data) == 0:
                        break
                    
                    if self.vosk_rec.AcceptWaveform(data):
                        result = json.loads(self.vosk_rec.Result())
                        if result.get('text'):
                            results.append(result['text'])
                
                # Get final result
                final_result = json.loads(self.vosk_rec.FinalResult())
                if final_result.get('text'):
                    results.append(final_result['text'])
            
            # Combine results
            transcription = ' '.join(results).strip()
            
            if transcription:
                logger.info(f"Transcription: {transcription}")
                return transcription
            else:
                logger.warning("No speech detected in audio")
                return None
                
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return None
    
    async def record_and_transcribe(self, duration: float = 5.0) -> Optional[str]:
        """Record audio and transcribe in one step."""
        audio_file = await self.record_audio(duration)
        if audio_file:
            return await self.transcribe(audio_file)
        return None
    
    def list_input_devices(self) -> list:
        """List available audio input devices."""
        try:
            devices = sd.query_devices()
            input_devices = [
                {
                    'id': i,
                    'name': device['name'],
                    'channels': device['max_input_channels']
                }
                for i, device in enumerate(devices)
                if device['max_input_channels'] > 0
            ]
            return input_devices
        except Exception as e:
            logger.error(f"Failed to list input devices: {e}")
            return []
    
    def set_input_device(self, device_id: int):
        """Set the audio input device."""
        try:
            sd.default.device[0] = device_id  # Set input device
            logger.info(f"Set input device to: {device_id}")
        except Exception as e:
            logger.error(f"Failed to set input device: {e}")
    
    def test_microphone(self) -> bool:
        """Test microphone functionality."""
        try:
            logger.info("Testing microphone...")
            
            # Record a short test
            test_data = sd.rec(
                int(self.sample_rate * 1),  # 1 second
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=np.float32
            )
            sd.wait()
            
            # Check if we got audio data
            volume = np.sqrt(np.mean(np.square(test_data)))
            logger.info(f"Microphone test volume: {volume}")
            
            return volume > 0.001  # Some minimal threshold
            
        except Exception as e:
            logger.error(f"Microphone test failed: {e}")
            return False
    
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the loaded Vosk model."""
        if not self.vosk_model:
            return {
                'available': False,
                'model_path': str(self.vosk_model_path),
                'message': 'No Vosk model loaded'
            }
        
        return {
            'available': True,
            'model_path': str(self.vosk_model_path),
            'sample_rate': self.sample_rate,
            'channels': self.channels
        }
    
    def download_model_instructions(self) -> str:
        """Return instructions for downloading Vosk models."""
        return """
To use voice recognition, please download a Vosk model:

1. Visit: https://alphacephei.com/vosk/models
2. Download a model for your language (e.g., vosk-model-en-us-0.22)
3. Extract the model to: {model_path}
4. Rename the extracted folder to 'vosk-model'

Recommended models:
- English: vosk-model-en-us-0.22 (1.8GB) or vosk-model-small-en-us-0.15 (40MB)
- Multilingual: vosk-model-small-0.15 (40MB)

Example commands:
wget https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip
unzip vosk-model-small-en-us-0.15.zip
mv vosk-model-small-en-us-0.15 {model_path}
        """.format(model_path=self.vosk_model_path)

# Mock implementation for when Vosk is not available
class MockVoiceRecorder:
    """Mock voice recorder for testing and fallback."""
    
    def __init__(self, *args, **kwargs):
        self.sample_rate = 16000
        self.channels = 1
    
    def is_available(self) -> bool:
        return False
    
    async def record_audio(self, duration: float = 5.0, **kwargs) -> Optional[str]:
        logger.warning("Using mock voice recorder - no audio recorded")
        return None
    
    async def transcribe(self, audio_file: str) -> Optional[str]:
        logger.warning("Using mock voice recorder - no transcription available")
        return "Mock transcription - please install Vosk for real voice recognition"
    
    async def record_and_transcribe(self, duration: float = 5.0) -> Optional[str]:
        return "Mock transcription - please install Vosk"
    
    def list_input_devices(self) -> list:
        return []
    
    def set_input_device(self, device_id: int):
        pass
    
    def test_microphone(self) -> bool:
        return False
    
    def get_model_info(self) -> Dict[str, Any]:
        return {
            'available': False,
            'message': 'Mock voice recorder - install Vosk and download models'
        }
    
    def download_model_instructions(self) -> str:
        return "Mock voice recorder - please install the required dependencies"

# Factory function to create appropriate voice recorder
def create_voice_recorder(**kwargs) -> VoiceRecorder:
    """Create a voice recorder instance, falling back to mock if dependencies missing."""
    try:
        import vosk
        import sounddevice as sd
        return VoiceRecorder(**kwargs)
    except ImportError as e:
        logger.warning(f"Voice recording dependencies not available: {e}")
        return MockVoiceRecorder(**kwargs)
