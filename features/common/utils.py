import os
from dotenv import load_dotenv
import shutil
from aip import AipSpeech
from datetime import datetime
from pathlib import Path
import playsound
import cv2
import speech_recognition as sr
from features.audio.speech_recognizer import RecognizeSpeech

load_dotenv()


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
