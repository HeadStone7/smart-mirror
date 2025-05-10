from aip import AipSpeech
import os
import speech_recognition as sr
import io
import wave
import audioop
import socket
import logging
from functools import lru_cache
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()


class RecognizeSpeech:
    """Speech recognition class using Baidu Speech Recognition API."""

    def __init__(self, app_id=os.getenv('BAIDU_APP_ID'), api_key=os.getenv('BAIDU_API_KEY'),
                 secret_key=os.getenv('BAIDU_SECRET_KEY'), log_dir="logs"):
        """Initialize speech recognition with Baidu credentials.

        Args:
            app_id (str): Baidu APP ID
            api_key (str): Baidu API Key
            secret_key (str): Baidu Secret Key
            log_dir (str): Directory for logs
        """
        # Initialize logging
        self.logger = self._setup_logger('baidu_recognizer', log_dir)

        # Initialize speech recognizer
        self.recognizer = sr.Recognizer()

        # Initialize Baidu Speech Client
        self.speech_client = AipSpeech(app_id, api_key, secret_key)

        # Configure speech recognition parameters
        self.configure_recognizer()

    def _setup_logger(self, name, log_dir):
        """Set up logger configuration.

        Args:
            name (str): Logger name
            log_dir (str): Directory for logs

        Returns:
            logging.Logger: Configured logger
        """
        logger = logging.getLogger(name)
        logger.setLevel(logging.INFO)

        # Create log directory if it doesn't exist
        log_path = Path(log_dir)
        log_path.mkdir(exist_ok=True)

        # File handler
        file_handler = logging.FileHandler(
            log_path / f"{name}_{datetime.now().strftime('%Y%m%d')}.log"
        )
        file_handler.setLevel(logging.INFO)

        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)

        # Create formatter
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)

        # Add handlers to logger
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

        return logger

    def configure_recognizer(self):
        """Configure speech recognizer parameters."""
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.energy_threshold = 1500
        self.recognizer.pause_threshold = 0.5
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5

    @lru_cache(maxsize=1)
    def _check_network_connection(self, timeout=3):
        """Check network connection status with caching.

        Args:
            timeout (int): Connection timeout in seconds

        Returns:
            bool: True if network is available, False otherwise
        """
        try:
            socket.create_connection(("baidu.com", 80), timeout=timeout)
            return True
        except (OSError, socket.timeout):
            return False

    def _get_asr_config(self):
        """Get Baidu Speech Recognition API parameters.

        Returns:
            dict: Configuration parameters
        """
        return {
            'dev_pid': 1537,  # Mandarin with simple English
            'format': 'pcm',
            'rate': 16000,
            'channel': 1,
            'cuid': 'speech_recognizer',
            'speech_quality': 9,
            'enable_voice_detection': True,
            'vad_silence_end': 100,
            'enable_long_speech': True,
            'enable_itn': True,
            'enable_punctuation': True
        }

    def _convert_to_pcm(self, audio):
        """Convert audio data to PCM format compatible with speech recognition.

        Args:
            audio: Audio data from recognizer

        Returns:
            bytes: PCM audio data
        """
        # Get WAV format audio data
        wav_data = audio.get_wav_data()

        # Convert WAV to PCM
        with wave.open(io.BytesIO(wav_data), 'rb') as wf:
            # Check if audio parameters meet requirements
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
                # Audio conversion needed
                pcm_data = b''
                while True:
                    chunk = wf.readframes(4096)
                    if not chunk:
                        break
                    # Convert stereo to mono if necessary
                    if wf.getnchannels() == 2:
                        chunk = audioop.tomono(chunk, wf.getsampwidth(), 1, 1)
                    # Resample if sample rate is not 16000Hz
                    if wf.getframerate() != 16000:
                        chunk, _ = audioop.ratecv(chunk, wf.getsampwidth(), 1,
                                                  wf.getframerate(), 16000, None)
                    pcm_data += chunk
            else:
                # Audio parameters meet requirements, read PCM data directly
                pcm_data = wf.readframes(wf.getnframes())

        return pcm_data

    def recognize_from_microphone(self, timeout=10, phrase_limit=5):
        """Capture microphone input and perform speech recognition.

        Args:
            timeout (int): Listening timeout in seconds
            phrase_limit (int): Maximum phrase duration in seconds

        Returns:
            str: Recognized text, or None if recognition fails
        """
        try:
            with sr.Microphone() as source:
                self.logger.info("Listening for speech...")

                # Adjust for ambient noise
                self.recognizer.adjust_for_ambient_noise(source, duration=1)

                # Capture audio
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )

                return self.recognize_audio(audio)

        except sr.WaitTimeoutError:
            self.logger.warning("Listening timed out, no speech detected")
            return None
        except Exception as e:
            self.logger.error(f"Speech recognition error: {e}")
            return None

    def recognize_from_file(self, audio_file_path):
        """Perform speech recognition on an audio file.

        Args:
            audio_file_path (str): Path to audio file

        Returns:
            str: Recognized text, or None if recognition fails
        """
        try:
            with sr.AudioFile(audio_file_path) as source:
                audio = self.recognizer.record(source)
                return self.recognize_audio(audio)
        except Exception as e:
            self.logger.error(f"File recognition error: {e}")
            return None

    def recognize_audio(self, audio):
        """Process audio data and perform speech recognition.

        Args:
            audio: Audio data from recognizer

        Returns:
            str: Recognized text, or None if recognition fails
        """
        # Check network availability
        if not self._check_network_connection():
            self.logger.error("Network unavailable for speech recognition")
            return None

        self.logger.info("Recognizing speech...")

        try:
            # Convert audio to PCM
            pcm_data = self._convert_to_pcm(audio)

            # Get ASR configuration
            asr_config = self._get_asr_config()

            # Call Baidu Speech Recognition API
            result = self.speech_client.asr(pcm_data, 'pcm', 16000, asr_config)

            if result and result.get('err_no') == 0:
                recognized_text = result.get('result')[0]
                self.logger.info(f"Recognition successful: {recognized_text}")
                return recognized_text

            self.logger.error(f"Baidu Speech Recognition failed: {result}")
            return None

        except Exception as e:
            self.logger.error(f"Speech recognition processing error: {e}")
            return None


