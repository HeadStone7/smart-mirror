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
import speech_recognition as sr

recognizer = sr.Recognizer()
with sr.Microphone() as source:
    print("Say something...")
    audio = recognizer.listen(source, timeout=10)
    print("Audio captured.")