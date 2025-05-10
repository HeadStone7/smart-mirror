import os
from collections import defaultdict

from flask import Flask
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView
from PySide6.QtCore import QUrl
import sys
import geocoder
from features.face_recognition.face_recognition_system import FaceRecognition
from features.common.utils import read_text_baidu, user_speech_recognition, record_audio_until_silence, audio_to_text, \
    text_to_speech_chinese, load_known_faces_from_folder
from features.voice_feat_system import VoiceAssistant
from features.weather import WeatherService
import time
import threading

app = Flask(__name__)

# Global flags and variables
running = True
face_detected = False
wake_words = ["小", "小朋友", "朋友"]  # Example wake words in Chinese (adjust as needed)
WAKE_WORD_THRESHOLD = 0.7  # Adjust based on your speech recognition sensitivity
assistant = None  # Initialize VoiceAssistant globally
face_detection_running = False
face_detection_success = False


class MMWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SmartMirror Display")
        self.setGeometry(100, 300, 1024, 768)
        # Create web view widget
        self.web = QWebEngineView(self)
        self.web.setUrl(QUrl("http://localhost:8080"))
        # self.web.setContextMenuPolicy(Qt.NoContextMenu) // disable right click
        self.setCentralWidget(self.web)


# Global variable to store preloaded face data
preloaded_face_data = None


def preload_face_data():
    """Preload face data into memory."""
    face_system = FaceRecognition()
    image_paths_by_person = load_known_faces_from_folder("known_faces")
    for person_name, image_paths in image_paths_by_person.items():
        face_system.add_new_person(person_name, image_paths)
    return face_system


def detect_face(timeout=60) -> bool:
    """Detect a face using preloaded face data."""
    global preloaded_face_data
    if preloaded_face_data is None:
        print("Error: Face data not preloaded.")
        return False

    start_time = time.time()
    while time.time() - start_time < timeout and running:
        try:
            recognized = preloaded_face_data.start_recognition()
            if recognized:
                print("Face detected")
                return True
            else:
                print("No face detected (during activation)")
                time.sleep(0.5)
        except Exception as e:
            print(f"Error during recognition: {e}")
            time.sleep(0.5)

    return False


def get_user_location():
    localization = geocoder.ip("me")
    return localization


def assistant_mode():
    global running, face_detected, assistant
    if assistant is None:
        print("Error: Assistant not initialized.")
        return

    location = get_user_location()
    weather = WeatherService()
    longitude = get_user_location().lng
    latitude = get_user_location().lat
    response = weather.get_weather_info(longitude, latitude)
    listening_duration = 60  # 1 minute in seconds
    last_interaction_time = time.time()

    read_text_baidu("你好！有什么我可以帮您？")
    while running and face_detected:
        if time.time() - last_interaction_time > listening_duration:
            read_text_baidu("等待唤醒...")
            face_detected = False
            break

        text = user_speech_recognition()
        if text:
            print(f"User said: {text}")
            last_interaction_time = time.time()  # Reset the timer

            if '天气' in text:
                print("Weather query detected")
                print("Response: " + response['weather_condition'])
                read_text_baidu(f"今天的天气状况如下,  位置:{location.city}")
                read_text_baidu(f"天气：{response['weather_condition']}")
                read_text_baidu(f"温度：{response['temperature']}")
                read_text_baidu(f"体感温度：{response['feels_like']}")
                read_text_baidu(f"湿度：{response['humidity']}")
                read_text_baidu(f"风向：{response['wind_direction']}")
                read_text_baidu(f"风速：{response['wind_speed']}")
                read_text_baidu(f"气压：{response['pressure']}")
                read_text_baidu(f"能见度：{response['visibility']}")
                read_text_baidu(f"云量：{response['cloud_coverage']}")
                continue
            elif '几点' in text:
                print("Time query detected")
                read_text_baidu(f"现在是 {time.strftime('%H:%M')}")
                continue
            elif '空调' in text:
                print("AC query detected")
                # Add your AC control logic here
                read_text_baidu("好的，正在处理空调指令。")
                continue
            elif '拜拜' in text or '再见' in text:
                read_text_baidu("拜拜，下次再见！")
                face_detected = False
                continue
            else:
                print("Deepseek request")
                print(f"Heard: {text}, processing with DeepSeek...")
                response = assistant.chat(text)
                print(f"DeepSeek response: {response}")
                read_text_baidu(response)
                continue
        else:
            print("Listening for command...")
            time.sleep(1)  # Small delay while actively listening

    if face_detected:
        read_text_baidu("等待唤醒...")
        face_detected = False


def run_face_detection():
    global face_detection_running, face_detection_success
    face_detection_running = True
    if detect_face(timeout=60):
        face_detection_success = True
    else:
        text_to_speech_chinese("我无法识别您的面部。如果需要我，请随时叫我。")
    face_detection_running = False


def wake_word_detection_loop():
    global running, face_detected, assistant
    global face_detection_running, face_detection_success

    if assistant is None:
        print("Error: Assistant not initialized.")
        return

    while running:
        if face_detected:
            time.sleep(2)
            continue

        if face_detection_success:
            face_detected = True
            face_detection_success = False  # Reset
            assistant_thread = threading.Thread(target=assistant_mode)
            assistant_thread.start()
            continue

        if not face_detection_running:
            print("Listening for wake word...")
            script = audio_to_text()
            if script:
                for wake_word in wake_words:
                    if wake_word in script:
                        text_to_speech_chinese("唤醒成功，请靠近并扫描您的面部以继续互动。这是为了您的安全。")
                        threading.Thread(target=run_face_detection).start()
                        break
                else:
                    print("Wake word not detected.")
            else:
                print("No speech detected.")

        time.sleep(1)  # Small delay to avoid busy loop


def launch_gui():
    qt_app = QApplication(sys.argv)
    window = MMWindow()
    window.show()
    sys.exit(qt_app.exec())


def main() -> None:
    global running, assistant, preloaded_face_data
    print("Smart Mirror started.")

    # Initialize the voice assistant
    assistant = VoiceAssistant(
        baidu_app_id=os.getenv("BAIDU_APP_ID"),
        baidu_api_key=os.getenv("BAIDU_API_KEY"),
        baidu_secret_key=os.getenv("BAIDU_SECRET_KEY"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
    )

    # Preload face data
    preloaded_face_data = preload_face_data()
    gui_thread = threading.Thread(target=launch_gui)
    voice_thread = threading.Thread(target=wake_word_detection_loop)

    voice_thread.start()
    gui_thread.start()

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Exiting...")
        running = False
        voice_thread.join()
        # GUI thread will exit when the Qt application is closed


if __name__ == "__main__":
    main()
