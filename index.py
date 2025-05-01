import os
from flask import Flask
from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen
# from kivy.uix.webview import WebView  # Commented out the WebView import
from kivy.uix.label import Label  # Added a basic UI element for now
import geocoder
from features.face_recognition.face_recognition_system import FaceRecognition
from features.common.utils import read_text_baidu, user_speech_recognition
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

class MirrorScreen(Screen):
 # webview_source = StringProperty("http://localhost:8080") # Removed webview_source

 def __init__(self, **kwargs):
     super().__init__(**kwargs)
     # self.webview = WebView(source=self.webview_source) # Removed WebView
     # self.add_widget(self.webview) # Removed adding WebView
     self.label = Label(text="Smart Mirror Application") # Basic UI element
     self.add_widget(self.label)

class MirrorApp(App):
 def build(self):
     sm = ScreenManager()
     sm.add_widget(MirrorScreen(name='mirror'))
     return sm

def detect_face(timeout=30) -> bool:
 """Detect a face within the given timeout period."""
 face_system = FaceRecognition()
 image_paths = [r"C:\Users\Josh\Pictures\Saved Pictures\id.jpg"]
 image_paths1 = []
 face_system.add_new_person("Joseph", image_paths)
 face_system.add_new_person("Atigo", image_paths1)
 start_time = time.time()

 while time.time() - start_time < timeout and running:
     try:
         recognized: bool = face_system.start_recognition()
         if recognized:
             print("Face detected")
             return True
         else:
             print("No face detected (during activation)")
             time.sleep(0.2)
     except Exception as e:
         print(f"Error during recognition: {e}")
         time.sleep(0.2)
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

         elif '几点' in text:
             print("Time query detected")
             read_text_baidu(f"现在是 {time.strftime('%H:%M')}")
         elif '空调' in text:
             print("AC query detected")
             # Add your AC control logic here
             read_text_baidu("好的，正在处理空调指令。")
         elif '拜拜' in text or '再见' in text:
             read_text_baidu("拜拜，下次再见！")
             face_detected = False
             break
         else:
             print("Deepseek request")
             print(f"Heard: {text}, processing with DeepSeek...")
             response = assistant.chat(text)
             print(f"DeepSeek response: {response}")
             read_text_baidu(response)
     else:
         print("Listening for command...")
         time.sleep(1)  # Small delay while actively listening

 if face_detected:
     read_text_baidu("等待唤醒...")
     face_detected = False

def wake_word_detection_loop():
 global running, face_detected, assistant
 if assistant is None:
     print("Error: Assistant not initialized.")
     return

 while running:
     if not face_detected:
         print("Listening for wake word...")
         audio = user_speech_recognition()
         if audio:
             triggered = False
             for wake_word in wake_words:
                 if wake_word in audio:
                     read_text_baidu("唤醒成功，请靠近并扫描您的面部以继续互动。这是为了您的安全。")
                     if detect_face(timeout=60):  # Try face detection for 1 minute
                         face_detected = True
                         assistant_thread = threading.Thread(target=assistant_mode)
                         assistant_thread.start()
                         triggered = True
                         break  # Exit wake word loop after activation
                     else:
                         read_text_baidu("我无法识别您的面部。如果需要我，请随时叫我。")
                         triggered = True
                         break  # Exit wake word check after failed face detection
             if not triggered:
                 print("Wake word not detected.")
         else:
             print("No speech detected.")
         time.sleep(1)  # Small delay
     else:
         time.sleep(2)  # Small delay if assistant is active

def launch_gui():
 MirrorApp().run()

def main() -> None:
 global running, assistant
 print("Smart Mirror started.")

 assistant = VoiceAssistant(
     baidu_app_id=os.getenv("BAIDU_APP_ID"),
     baidu_api_key=os.getenv("BAIDU_API_KEY"),
     baidu_secret_key=os.getenv("BAIDU_SECRET_KEY"),
     deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
 )

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
     # GUI thread will exit when the Kivy application is closed

if __name__ == "__main__":
 main()