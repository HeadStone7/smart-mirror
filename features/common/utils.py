from collections import defaultdict
import audioop
import os
import tempfile
import sys
import threading
import wave

import pyaudio
import pyttsx3
from dotenv import load_dotenv
import shutil
from aip import AipSpeech
from datetime import datetime
from pathlib import Path
import playsound
import cv2
from features.speech_recognizer import RecognizeSpeech

load_dotenv()

# Baidu API credentials
APP_ID = os.getenv('BAIDU_APP_ID')
API_KEY = os.getenv('BAIDU_API_KEY')
SECRET_KEY = os.getenv('BAIDU_SECRET_KEY')


def create_directory_if_not_exists(directory: str):
    if not os.path.exists(directory):
        os.makedirs(directory)
        print(f"Created directory: {directory}")


def copy_image_to_directory(image_path: str, target_dir: str):
    try:
        filename = os.path.basename(image_path)
        new_path = os.path.join(target_dir, filename)
        shutil.copy2(image_path, new_path)
        return new_path
    except Exception as e:
        print(f"Error copying {image_path}: {str(e)}")
        return None


def _draw_face_annotations(frame, top, right, bottom, left, display_text):
    """Draw stable bounding box and text for detected faces"""
    # Calculate box thickness based on frame size
    thickness = max(1, min(2, int(frame.shape[1] / 640)))

    # Draw anti-aliased rectangle around the face
    cv2.rectangle(
        frame,
        (left, top),
        (right, bottom),
        (0, 255, 0),
        thickness,
        cv2.LINE_AA
    )

    # Calculate text background rectangle size
    text_size = cv2.getTextSize(
        display_text,
        cv2.FONT_HERSHEY_DUPLEX,
        0.6,
        1
    )[0]

    # Draw semi-transparent background for text
    overlay = frame.copy()
    cv2.rectangle(
        overlay,
        (left, bottom - 35),
        (right, bottom),
        (0, 255, 0),
        cv2.FILLED
    )
    cv2.addWeighted(overlay, 0.7, frame, 0.3, 0, frame)

    # Add name text with anti-aliasing
    cv2.putText(
        frame,
        display_text,
        (left + 6, bottom - 6),
        cv2.FONT_HERSHEY_DUPLEX,
        0.6,
        (255, 255, 255),
        1,
        cv2.LINE_AA
    )


def read_text_baidu(
        text,
        baidu_app_id=os.getenv('BAIDU_APP_ID'),
        baidu_api_key=os.getenv('BAIDU_API_KEY'),
        baidu_secret_key=os.getenv('BAIDU_SECRET_KEY'),
        temp_audio_dir='temp_audio'
):
    """
    Convert text to speech using Baidu TTS and play the audio.

    Args:
        text (str): Text to be converted to speech.
        app_id (str): Baidu APP ID.
        api_key (str): Baidu API Key.
        secret_key (str): Baidu Secret Key.
        temp_audio_dir (str): Directory to save temporary audio files.
        :param temp_audio_dir: temporary audio directory
        :param baidu_secret_key: baidu secret key
        :param baidu_api_key: baidu api key
        :param text: text to be read
        :param baidu_app_id: baidu app id
    """

    # Check if the credentials are not None
    if not all([baidu_app_id, baidu_api_key, baidu_secret_key]):
        raise ValueError("Baidu API credentials are not set properly.")

    # Initialize Baidu Speech Client
    client = AipSpeech(baidu_app_id.strip(), baidu_api_key.strip(), baidu_secret_key.strip())

    # Create temp directory if it doesn't exist
    temp_audio_path = Path(temp_audio_dir)
    temp_audio_path.mkdir(exist_ok=True)

    # Synthesize speech
    result = client.synthesis(text, 'zh', 1, {
        'spd': 5,  # Speed
        'pit': 5,  # Pitch
        'vol': 5,  # Volume
        'per': 4  # Voice type
    })

    # Check if synthesis was successful
    if not isinstance(result, dict):
        # Save the audio to a temporary file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        temp_file = temp_audio_path / f'tts_{timestamp}.mp3'
        with open(temp_file, 'wb') as f:
            f.write(result)

        # Play the audio
        playsound.playsound(str(temp_file), True)

        # Remove the temporary file
        os.remove(temp_file)
    else:
        print("Error in speech synthesis:", result)


def user_speech_recognition() -> str:
    speech_recognition = RecognizeSpeech()
    recognized_text = speech_recognition.recognize_from_microphone()
    return recognized_text


# Update the listening and reading of data

def record_audio_until_silence():
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        SILENCE_THRESHOLD = 500
        SILENCE_DURATION = 2  # seconds
        p = pyaudio.PyAudio()

        stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True, frames_per_buffer=CHUNK)

        print("Listening for voice...")

        # Pre-listening phase: Wait until a voice is detected
        while True:
            data = stream.read(CHUNK)
            rms = audioop.rms(data, 2)
            if rms >= SILENCE_THRESHOLD:
                print("Voice detected, starting recording...")
                break

        print("Recording... Press Ctrl+C to stop.")
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


def speech_to_text(audio):
    client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)

    with open(audio, "rb") as f:
        audio_data = f.read()
    result = client.asr(audio_data, "wav", 16000, {"dev_pid": 1537})  # 1537 for Mandarin
    if "result" in result:
        return result["result"][0]
    else:
        print("Error in STT:", result)
        return None


# Text-to-Speech (TTS)
def speak_text(text):
    engine = pyttsx3.init()
    engine.setProperty("voice", "HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Speech\\Voices\\Tokens\\TTS_MS_ZH-CN_HUIHUI_11.0")
    engine.setProperty("rate", 150)
    engine.say(text)
    engine.runAndWait()
    engine.stop()


def text_to_speech_chinese(text):
    t = threading.Thread(target=speak_text, args=(text,))
    t.start()
    t.join(timeout=10)  # Wait 10 seconds max

    if t.is_alive():
        print("⚠️ Speech timed out. Something went wrong.")
        # Optional: Kill or cleanup logic here
        return True
    else:
        print("✅ Done speaking.")


def audio_to_text():
    audio = record_audio_until_silence()
    text = speech_to_text(audio)
    if text:
        print("Recognized text:", text)
        return text
    else:
        print("Could not convert audio to text.")



def load_known_faces_from_folder(folder_path):
    """
    Scans the given folder and maps each image file to a person name based on the file name.
    Example: Joseph.jpg -> person_name = "Joseph"
    Returns a dictionary: { "Joseph": ["known_faces/Joseph.jpg"], ... }
    """
    folder = Path(folder_path)
    image_paths_by_person = defaultdict(list)

    for image_path in folder.glob("*.jpg"):
        person_name = image_path.stem  # e.g., Joseph from Joseph.jpg
        image_paths_by_person[person_name].append(str(image_path))

    return image_paths_by_person

#
# if __name__ == "__main__":
#     # Example usage
#     text_to_speech_chinese("你好，世界！")
#     audio = record_audio_until_silence()
#     text = speech_to_text(audio)
#     if text:
#         print("Recognized text:", text)
#     else:
#         print("Could not convert audio to text.")