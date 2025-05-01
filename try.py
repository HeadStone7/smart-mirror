from dotenv import load_dotenv
import os
from aip import AipSpeech

# load_dotenv()
#
# APP_ID = os.getenv("BAIDU_APP_ID")
# API_KEY = os.getenv("BAIDU_API_KEY")
# SECRET_KEY = os.getenv("BAIDU_SECRET_KEY")
#
# client = AipSpeech(APP_ID, API_KEY, SECRET_KEY)
#
# with open("temp_audio/tts_20250331_113129.mp3", "rb") as f:
#     audio_data = f.read()
#
# result = client.asr(audio_data, "pcm", 16000, {"dev_pid": 1537})
# print(result)
# import speech_recognition as sr

#recognizer = sr.Recognizer()
# with sr.Microphone() as source:
#     print("Say something...")
#     audio = recognizer.listen(source, timeout=10)
#     print("Audio captured.")
import pyttsx3

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
text_to_speech_chinese("你好，世界！")