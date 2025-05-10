from dotenv import load_dotenv
import os
import speech_recognition as sr
import json
import wave
import queue
import threading
import pyttsx3
from aip import AipSpeech
from datetime import datetime
import logging
from pathlib import Path
import time
import io
import audioop
import requests
import socket
from functools import lru_cache


class VoiceAssistant:
    """Voice assistant that handles speech recognition, speech synthesis, and conversation."""

    def __init__(self, log_dir="logs", baidu_app_id=None, baidu_api_key=None,
                 baidu_secret_key=None, deepseek_api_key=None):
        """Initialize voice assistant with necessary components.

        Args:
            log_dir (str): Directory for logs
            baidu_app_id (str): Baidu APP ID
            baidu_api_key (str): Baidu API Key
            baidu_secret_key (str): Baidu Secret Key
            deepseek_api_key (str): DeepSeek API Key
        """
        # Initialize logging
        self.logger = self._setup_logger('voice_assistant', log_dir)

        # Initialize speech recognition
        self.recognizer = sr.Recognizer()

        # Initialize Baidu Speech Client
        self.speech_client = None
        if all([baidu_app_id, baidu_api_key, baidu_secret_key]):
            self.speech_client = AipSpeech(baidu_app_id, baidu_api_key, baidu_secret_key)

        # Initialize DeepSeek API
        self.deepseek_api_key = os.getenv('DEEPSEEK_API_KEY')
        self.deepseek_api_url = os.getenv('DEEPSEEK_API_URL')

        # Initialize TTS engine
        self.voice_queue = queue.Queue()
        self.engine = pyttsx3.init()
        self._setup_voice_engine()

        # Start speech processing thread
        self.voice_thread = threading.Thread(target=self._process_voice_queue, daemon=True)
        self.voice_thread.start()

        # Create temp directory for audio files
        self.temp_audio_dir = Path(__file__).parent / 'temp_audio'
        self.temp_audio_dir.mkdir(exist_ok=True)

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

    def _setup_voice_engine(self):
        """Configure text-to-speech engine."""
        voices = self.engine.getProperty('voices')
        self.engine.setProperty('voice', voices[1].id)  # Female voice
        self.engine.setProperty('rate', 150)  # Speech rate
        self.engine.setProperty('volume', 0.8)  # Volume

    def _process_voice_queue(self):
        """Process the speech synthesis queue."""
        while True:
            try:
                message = self.voice_queue.get()
                self.engine.say(message)
                self.engine.runAndWait()
                self.voice_queue.task_done()
            except Exception as e:
                self.logger.error(f"Voice queue processing error: {e}")

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

    def _setup_audio_source(self, source):
        """Configure audio source parameters.

        Args:
            source: Microphone audio source
        """
        self.recognizer.adjust_for_ambient_noise(source, duration=1)
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.dynamic_energy_adjustment_damping = 0.15
        self.recognizer.dynamic_energy_ratio = 1.5
        self.recognizer.energy_threshold = 1500
        self.recognizer.pause_threshold = 0.5
        self.recognizer.operation_timeout = None
        self.recognizer.phrase_threshold = 0.3
        self.recognizer.non_speaking_duration = 0.5

    def recognize_speech(self, timeout=10, phrase_limit=5):
        """Capture microphone input and perform speech recognition.

        Args:
            timeout (int): Listening timeout in seconds
            phrase_limit (int): Maximum phrase duration in seconds

        Returns:
            str: Recognized text, or None if recognition fails
        """
        try:
            with sr.Microphone() as source:
                self._setup_audio_source(source)
                self.logger.info("Listening for speech...")

                # Capture audio
                audio = self.recognizer.listen(
                    source,
                    timeout=timeout,
                    phrase_time_limit=phrase_limit
                )

                # Process audio
                return self._process_audio_file(audio)
        except sr.WaitTimeoutError:
            self.logger.warning("Listening timed out, no speech detected")
            return None
        except Exception as e:
            self.logger.error(f"Speech recognition error: {e}")
            return None

    def _process_audio_file(self, audio):
        """Process audio files and perform speech recognition.

        Args:
            audio: Audio data

        Returns:
            str: Recognized text, or None if recognition fails
        """
        # Check network and online recognition availability
        network_available = self._check_network_connection()
        self.logger.info("Recognizing speech...")

        if network_available and self.speech_client:
            result = self._online_recognition(audio)
            if result:
                self.logger.info(f"Online recognition successful: {result}")
                return result

        self.logger.info("Using offline recognition")
        return None  # No online recognition successful

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
            'cuid': 'voice_assistant',
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
            audio: Audio data

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

    def _online_recognition(self, audio):
        """Perform online speech recognition using Baidu API.

        Args:
            audio: Audio data

        Returns:
            str: Recognized text, or None if recognition fails
        """
        try:
            # Convert audio to PCM
            pcm_data = self._convert_to_pcm(audio)

            # Get ASR configuration
            asr_config = self._get_asr_config()

            # Call Baidu Speech Recognition API
            result = self.speech_client.asr(pcm_data, 'pcm', 16000, asr_config)

            if result and result.get('err_no') == 0:
                return result.get('result')[0]

            self.logger.error(f"Baidu Speech Recognition failed: {result}")
            return None

        except Exception as e:
            self.logger.error(f"Online recognition error: {e}")
            return None

    def speak(self, text):
        """Convert text to speech.

        Args:
            text (str): Text to be converted to speech
        """
        if not text:
            return

        if self._check_network_connection() and self.speech_client:
            self._online_speak(text)
        else:
            self._offline_speak(text)

    def _online_speak(self, text):
        """Use Baidu TTS for speech synthesis.

        Args:
            text (str): Text to be spoken
        """
        try:
            result = self.speech_client.synthesis(text, 'zh', 1, {
                'spd': 6,  # Speed (0-9)
                'pit': 5,  # Pitch (0-9)
                'vol': 5,  # Volume (0-15)
                'per': 4,  # Voice selection
            })

            # Check if synthesis was successful
            if not isinstance(result, dict):
                # Create temporary file with a simple name (avoiding path issues)
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                temp_file = self.temp_audio_dir / f'tts_{timestamp}.mp3'

                with open(temp_file, 'wb') as f:
                    f.write(result)

                # Play audio using a different approach
                try:
                    # Try with playsound 1.2.2 (different argument handling)
                    from playsound import playsound
                    playsound(str(temp_file), True)  # True = blocking
                except Exception as play_error:
                    self.logger.warning(f"First playback method failed: {play_error}")
                    try:
                        # Alternative playback method using winsound on Windows
                        import platform
                        if platform.system() == 'Windows':
                            import winsound
                            # Convert mp3 to wav first
                            from pydub import AudioSegment
                            sound = AudioSegment.from_mp3(temp_file)
                            wav_file = temp_file.with_suffix('.wav')
                            sound.export(wav_file, format="wav")
                            winsound.PlaySound(str(wav_file), winsound.SND_FILENAME)
                            # Clean up the WAV file
                            os.remove(wav_file)
                        else:
                            # On non-Windows systems, try alternative method
                            import subprocess
                            subprocess.call(['mpg123', str(temp_file)], stdout=subprocess.DEVNULL,
                                            stderr=subprocess.DEVNULL)
                    except Exception as alt_error:
                        self.logger.warning(f"Alternative playback method failed: {alt_error}")
                        self._offline_speak(text)

                # Remove temporary file
                try:
                    os.remove(temp_file)
                except Exception as e:
                    self.logger.warning(f"Failed to delete temporary audio file: {e}")
            else:
                self.logger.error(f"Speech synthesis failed: {result}")
                self._offline_speak(text)
        except Exception as e:
            self.logger.error(f"Online speech synthesis error: {e}")
            self._offline_speak(text)

    def _offline_speak(self, text):
        """Use pyttsx3 for offline speech synthesis.

        Args:
            text (str): Text to be spoken
        """
        self.voice_queue.put(text)
        self.logger.info(f"Using offline speech synthesis")

    def chat(self, text):
        """Process user input text using DeepSeek AI chat.

        Args:
            text (str): User input text

        Returns:
            str: System response text
        """
        if not text:
            return "I didn't hear anything. Could you please try again?"

        if not self._check_network_connection():
            return "Sorry, I am currently unable to connect to the internet."

        if not self.deepseek_api_key or not self.deepseek_api_url:
            return "Sorry, I am not properly configured for chat functionality."

        try:
            headers = {
                "Authorization": f"Bearer {self.deepseek_api_key}",
                "Content-Type": "application/json"
            }

            data = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system",
                     "content": "You are a friendly, professional assistant named 小朋友 who provides concise "
                                "responses under 30 words. For unclear or incomplete questions, "
                                "politely ask for clarification in the user input language. Never mention your word "
                                "count limit."},
                    {"role": "user", "content": text}
                ],
                "temperature": 0.7,
                "max_tokens": 100
            }

            response = requests.post(
                self.deepseek_api_url,
                headers=headers,
                json=data,
                timeout=10
            )

            if response.status_code == 200:
                result = response.json()
                reply = result['choices'][0]['message']['content']
                self.logger.info(f"Chat response received")

                if reply:
                    sentences = reply.split('.')
                    shortened_reply = '.'.join(sentences[:1]) + '.' if len(sentences) > 2 else reply  # Keep the first 2 sentences
                    return shortened_reply.strip()
                return reply
            else:
                self.logger.error(f"API request failed: {response.status_code}, {response.text}")
                # return "Sorry, I couldn't process your request. Please try again."
                return "抱歉，我无法将代码注释或内容翻译成中文。如果您需要技术帮助或代码修改，请告诉我！"

        except requests.exceptions.Timeout:
            # return "Sorry, the request timed out. Please try again."
            return "抱歉，请求超时。请再试一次。"
        except requests.exceptions.ConnectionError:
            # return "Sorry, I'm having trouble connecting to the server."
            return "抱歉，我无法连接到服务器。"
        except Exception as e:
            self.logger.error(f"Chat processing error: {e}")
            # return "I encountered an error while processing your request."
            return "处理您的请求时遇到错误。"




def main():
    """Main function to run the voice assistant."""
    load_dotenv()

    # Create assistant with environment variables
    assistant = VoiceAssistant(
        baidu_app_id=os.getenv('BAIDU_APP_ID'),
        baidu_api_key=os.getenv('BAIDU_API_KEY'),
        baidu_secret_key=os.getenv('BAIDU_SECRET_KEY'),
        deepseek_api_key=os.getenv('DEEPSEEK_API_KEY')
    )

    print("\n" + "=" * 50)
    print("Voice Assistant Started")
    print("Speak to interact. Press Ctrl+C to exit.")
    print("=" * 50 + "\n")

    try:
        while True:
            try:
                # Get user input via speech
                recognized_text = assistant.recognize_speech()

                if recognized_text:
                    print(f"\nYou said: {recognized_text}")

                    # Get response from chat
                    response = assistant.chat(recognized_text)
                    print(f"\nAssistant: {response}")

                    # Speak the response
                    assistant.speak(response)
                else:
                    print("\nNo speech detected. Please try again...")

                time.sleep(0.5)  # Reduce CPU usage

            except KeyboardInterrupt:
                raise
            except Exception as e:
                print(f"\nError: {e}")
                time.sleep(1)
                continue

    except KeyboardInterrupt:
        print("\n\nExiting Voice Assistant...")
    finally:
        print("Voice Assistant closed.")


# if __name__ == "__main__":
#     main()