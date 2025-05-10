import os
from aip import AipSpeech
import pyaudio
import wave
from dotenv import load_dotenv
import audioop
import pyttsx3
import tempfile

load_dotenv()

# Baidu API credentials
APP_ID = os.getenv('BAIDU_APP_ID')
API_KEY = os.getenv('BAIDU_API_KEY')
SECRET_KEY = os.getenv('BAIDU_SECRET_KEY')

# Validate credentials
if not all([APP_ID, API_KEY, SECRET_KEY]):
    raise ValueError("Baidu API credentials are not set. Please check your environment variables.")
client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)


# Record audio from microphone
def record_audio_until_silence():
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    SILENCE_THRESHOLD = 500
    SILENCE_DURATION = 2  # seconds
    p = pyaudio.PyAudio()

    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

    print("Listening... Press Ctrl+C to stop.")
    frames = []
    silent_chunks = 0
    max_silent_chunks = int(SILENCE_DURATION * RATE / CHUNK)

    try:
        while True:
            data = stream.read(CHUNK)
            frames.append(data)
            rms = audioop.rms(data, 2)

            if rms < SILENCE_THRESHOLD:
                silent_chunks += 1
                if silent_chunks > max_silent_chunks:
                    # Silence detected, save current segment
                    if frames:
                        # Save to temporary file
                        with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as tmpfile:
                            filename = tmpfile.name
                            with wave.open(filename, "wb") as wf:
                                wf.setnchannels(CHANNELS)
                                wf.setsampwidth(p.get_sample_size(FORMAT))
                                wf.setframerate(RATE)
                                wf.writeframes(b"".join(frames))
                            print(f"Speech segment stored at: {filename}")

                            # Clear frames for next detection
                        frames = []

                        # Return filename for processing (or directly pass to STT)
                        return filename

            else:
                silent_chunks = 0

    except KeyboardInterrupt:
        print("Stopped listening.")

    finally:
        stream.stop_stream()
        stream.close()
        p.terminate()


    # Speech-to-Text (STT)
def speech_to_text(audio):
    with open(audio, "rb") as f:
        audio_data = f.read()
    result = client.asr(audio_data, "wav", 16000, {"dev_pid": 1537})  # 1537 for Mandarin
    if "result" in result:
        return result["result"][0]
    else:
        print("Error in STT:", result)
        return None


# Text-to-Speech (TTS)
def text_to_speech_chinese(text):
    try:
        engine = pyttsx3.init()
        voices = engine.getProperty("voices")

        # Print available voices to find a Chinese-compatible one
        for voice in voices:
            print(f"Voice: {voice.name}, ID: {voice.id}, Lang: {voice.languages}")

        # Set a Chinese-compatible voice (replace with the correct ID for your system)
        chinese_voice_id = "Huihui"  # Example: Replace with the actual voice ID
        for voice in voices:
            if chinese_voice_id in voice.name:
                engine.setProperty("voice", voice.id)
                break
        else:
            raise RuntimeError("No Chinese-compatible voice found.")

        # Set speech rate (optional)
        engine.setProperty("rate", 150)

        # Speak the text
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print("Error in TTS:", e)


# Example usage
if __name__ == "__main__":
    audio_file = record_audio_until_silence()
    recognized_text = speech_to_text(audio_file)
    if recognized_text:
        print("Recognized Text:", recognized_text)
        text_to_speech_chinese(f"你说的是: {recognized_text}")
