"""
Speech Recognition Service
Uses Vosk for offline speech-to-text conversion
"""
import logging
import os
import re
import json
from pathlib import Path
from typing import Optional, Tuple
import subprocess

logger = logging.getLogger(__name__)


class SpeechRecognitionService:
    """Service for speech-to-text conversion using Vosk"""

    def __init__(self, model_path: Optional[str] = None):
        """
        Initialize speech recognition service

        Args:
            model_path: Path to Vosk model (if not provided, uses default)
        """
        self.model_path = model_path or os.getenv(
            'VOSK_MODEL_PATH',
            '/usr/local/share/vosk-models/vosk-model-small-en-us-0.15'
        )
        self.sample_rate = 16000

    async def transcribe_audio(self, file_path: str) -> Optional[str]:
        """
        Transcribe audio file to text using Vosk

        Args:
            file_path: Path to audio file (OGG from Telegram)

        Returns:
            Transcribed text or None if failed
        """
        try:
            # Import vosk here to avoid dependency issues
            try:
                from vosk import Model, KaldiRecognizer
                import wave
            except ImportError:
                logger.error("Vosk not installed. Install: pip install vosk")
                return None

            # Convert OGG to WAV if needed
            wav_path = await self._convert_to_wav(file_path)
            if not wav_path:
                return None

            # Check if model exists
            if not os.path.exists(self.model_path):
                logger.error(f"Vosk model not found at {self.model_path}")
                logger.info("Download model: https://alphacephei.com/vosk/models")
                return None

            # Load Vosk model
            model = Model(self.model_path)

            # Open WAV file
            wf = wave.open(wav_path, "rb")

            # Check audio format
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != self.sample_rate:
                logger.error(f"Audio must be WAV format mono PCM, 16kHz")
                wf.close()
                return None

            # Create recognizer
            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)

            # Process audio
            results = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    result = json.loads(rec.Result())
                    if 'text' in result:
                        results.append(result['text'])

            # Get final result
            final_result = json.loads(rec.FinalResult())
            if 'text' in final_result:
                results.append(final_result['text'])

            wf.close()

            # Cleanup WAV file
            if os.path.exists(wav_path) and wav_path != file_path:
                os.remove(wav_path)

            # Combine results
            text = ' '.join(results).strip()
            logger.info(f"Transcribed: {text}")
            return text if text else None

        except Exception as e:
            logger.error(f"Error transcribing audio: {e}")
            return None

    async def _convert_to_wav(self, input_file: str) -> Optional[str]:
        """
        Convert OGG/OPUS to WAV using ffmpeg

        Args:
            input_file: Path to input audio file

        Returns:
            Path to WAV file or None
        """
        try:
            output_file = input_file.rsplit('.', 1)[0] + '.wav'

            # Use ffmpeg to convert (use full path to avoid PATH issues)
            ffmpeg_path = '/usr/bin/ffmpeg'
            cmd = [
                ffmpeg_path,
                '-i', input_file,
                '-ar', str(self.sample_rate),  # 16kHz
                '-ac', '1',  # Mono
                '-y',  # Overwrite
                output_file
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )

            if result.returncode == 0 and os.path.exists(output_file):
                return output_file
            else:
                logger.error(f"FFmpeg conversion failed: {result.stderr.decode()}")
                return None

        except FileNotFoundError:
            logger.error("ffmpeg not found. Install: apt-get install ffmpeg")
            return None
        except Exception as e:
            logger.error(f"Error converting audio: {e}")
            return None

    def extract_name_from_text(self, text: str) -> Optional[str]:
        """
        Extract name from text containing "my name is [Name]"

        Args:
            text: Transcribed text

        Returns:
            Extracted name or None
        """
        # Pattern to match "my name is [Name]"
        # More flexible: handles "my name's", "name is", etc.
        patterns = [
            r'my\s+names?\s+is\s+([a-zA-Z]+)',
            r'my\s+names?\s+([a-zA-Z]+)',
            r'name\s+is\s+([a-zA-Z]+)',
            r'i\s+am\s+([a-zA-Z]+)',
        ]

        text_lower = text.lower()

        for pattern in patterns:
            match = re.search(pattern, text_lower)
            if match:
                name = match.group(1).capitalize()
                logger.info(f"Extracted name: {name}")
                return name

        logger.warning(f"Could not extract name from: {text}")
        return None

    def check_phrase(self, text: str, phrase: str = "my name is") -> bool:
        """
        Check if text contains specific phrase

        Args:
            text: Transcribed text
            phrase: Phrase to check for

        Returns:
            True if phrase found
        """
        return phrase.lower() in text.lower()

    async def process_voice_message(
        self,
        file_path: str
    ) -> Tuple[Optional[str], Optional[str], bool]:
        """
        Process voice message: transcribe, check phrase, extract name

        Args:
            file_path: Path to audio file

        Returns:
            Tuple of (transcribed_text, extracted_name, has_phrase)
        """
        # Transcribe
        text = await self.transcribe_audio(file_path)

        if not text:
            return None, None, False

        # Check for phrase
        has_phrase = self.check_phrase(text, "my name is")

        # Extract name if phrase present
        name = None
        if has_phrase:
            name = self.extract_name_from_text(text)

        return text, name, has_phrase


# Global instance
speech_service = SpeechRecognitionService()
