import os
import groq
from groq import Groq
from PyQt6.QtCore import pyqtSignal, QObject
from translator import DeepTranslatorEngine
import threading
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class AudioTranslatorSignals(QObject):
    # Emits the final translated text
    translation_ready = pyqtSignal(str)

class AudioTranslator:
    def __init__(self):
        self.signals = AudioTranslatorSignals()
        self.reload_keys()
        
        # Initialize the English to Indonesian text translator
        self.text_translator = DeepTranslatorEngine(source='en', target='id')

    def reload_keys(self):
        load_dotenv(override=True)
        keys_str = os.environ.get("GROQ_API_KEYS", "")
        if keys_str:
            self.api_keys = [k.strip() for k in keys_str.split(",") if k.strip()]
        else:
            single_key = os.environ.get("GROQ_API_KEY", "")
            self.api_keys = [single_key] if single_key else []
            
        self.current_key_index = 0
        
        if not self.api_keys:
            print("WARNING: No Groq API keys found in .env!")
            self.client = None
        else:
            self.client = Groq(api_key=self.api_keys[self.current_key_index])

    def rotate_key(self):
        if len(self.api_keys) > 1:
            self.current_key_index = (self.current_key_index + 1) % len(self.api_keys)
            self.client = Groq(api_key=self.api_keys[self.current_key_index])
            print(f"--- Rotated to Groq API Key #{self.current_key_index + 1} ---")
            return True
        return False

    def validate_keys(self) -> tuple[bool, str]:
        """
        Tests the current API key by fetching models.
        Returns (True, "") if valid, (False, error_message) if invalid.
        """
        if not self.client:
            return False, "No API key provided."
        try:
            self.client.models.list()
            return True, ""
        except groq.AuthenticationError:
            return False, "Invalid API Key. Please ensure you copied it correctly."
        except Exception as e:
            return False, f"Connection error: {str(e)}"

    def process_audio(self, wav_bytes: bytes):
        """
        Takes raw WAV bytes, sends to Groq for transcription, 
        translates the transcript, and emits the result.
        """
        if not self.client:
            return
            
        thread = threading.Thread(target=self._process_async, args=(wav_bytes,))
        thread.daemon = True
        thread.start()

    def _process_async(self, wav_bytes: bytes, retries=0):
        try:
            # 1. Transcribe with Groq (Whisper)
            # Send the in-memory bytes. Groq requires a tuple of (filename, file-like object)
            completion = self.client.audio.transcriptions.create(
                file=("audio.wav", wav_bytes),
                model="whisper-large-v3",
                prompt="Specify context or spelling if needed", # Optional
                response_format="json",
                language="en", # Hardcoded to English per user request
                temperature=0.0
            )
            
            english_text = completion.text.strip()
            
            if english_text:
                # 2. Translate English to Indonesian
                indonesian_text = self.text_translator.translate(english_text)
                
                # 3. Emit the final text to the UI
                self.signals.translation_ready.emit(indonesian_text)
                
        except groq.RateLimitError as e:
            print(f"Rate limit reached on key #{self.current_key_index + 1}.")
            # If we haven't tried all keys yet, rotate and retry this same audio chunk
            if retries < len(self.api_keys) - 1:
                if self.rotate_key():
                    self._process_async(wav_bytes, retries + 1)
            else:
                self.signals.translation_ready.emit("All API keys are out of quota.")
                print("All API keys hit Rate Limits.")
                
        except Exception as e:
            print(f"Groq API or Translation Error: {e}")
