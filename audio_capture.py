import soundcard as sc
import soundfile as sf
import io
import threading
import time
from PyQt6.QtCore import pyqtSignal, QObject
import numpy as np

class AudioCaptureSignals(QObject):
    # Emits the in-memory WAV file bytes
    audio_ready = pyqtSignal(bytes)

class AudioCapture(threading.Thread):
    def __init__(self, chunk_duration=4.0):
        super().__init__()
        self.chunk_duration = chunk_duration
        self.signals = AudioCaptureSignals()
        self.running = False
        self.samplerate = 44100
        # Silence threshold: avoid sending pure silence to save API quota
        self.silence_threshold = 0.005

    def run(self):
        self.running = True
        try:
            # Get default speaker and its loopback microphone (captures what you hear)
            default_speaker = sc.default_speaker()
            mic = sc.get_microphone(id=default_speaker.id, include_loopback=True)
            
            print(f"Capturing loopback from: {default_speaker.name}")
            
            with mic.recorder(samplerate=self.samplerate) as recorder:
                while self.running:
                    # frames_to_record = sample rate * duration
                    frames_to_record = int(self.samplerate * self.chunk_duration)
                    data = recorder.record(numframes=frames_to_record)
                    
                    # Simple VAD (Voice Activity Detection) - Check if volume exceeds threshold
                    if np.max(np.abs(data)) > self.silence_threshold:
                        # Convert to wav bytes in memory
                        wav_io = io.BytesIO()
                        # Use PCM_16 (16-bit) to reduce file size slightly over 32-bit float
                        sf.write(wav_io, data, self.samplerate, format='wav', subtype='PCM_16')
                        wav_bytes = wav_io.getvalue()
                        self.signals.audio_ready.emit(wav_bytes)
                    else:
                        pass # It was silence, do nothing and loop again

        except Exception as e:
            print(f"Audio capture error: {e}")

    def stop(self):
        self.running = False
