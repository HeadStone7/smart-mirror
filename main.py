import os
import sys
from flask import Flask, render_template
import geocoder
from features.face_recognition.face_recognition_system import FaceRecognition
from features.common.utils import read_text_baidu, user_speech_recognition
from features.audio.voice_feat_system import VoiceAssistant
from features.weather import WeatherService
import time
import threading

# Initialize Flask app
app = Flask(__name__)
app.config['TEMPLATES_AUTO_RELOAD'] = True

# Global flags and variables
running = True
face_detected = False
wake_words = ["小", "小朋友", "朋友"]
WAKE_WORD_THRESHOLD = 0.7
assistant = None

@app.route('/')
def index():
    """Serve the main interface"""
    return render_template('index.html')

@app.route('/test')
def test():
    """Test endpoint to verify Flask is running"""
    return "Flask server is working!"

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
    """Get the user's location using geocoder"""
    try:
        return geocoder.ip("me")
    except Exception as e:
        print(f"Error getting location: {e}")
        return None

def assistant_mode():
    global running, face_detected, assistant
    if assistant is None:
        print("Error: Assistant not initialized.")
        return

    location = get_user_location()
    weather = WeatherService()
    
    if location:
        longitude = location.lng
        latitude = location.lat
        weather_response = weather.get_weather_info(longitude, latitude)
    else:
        weather_response = None
        print("Could not get location for weather")

    listening_duration = 60
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
            last_interaction_time = time.time()

            if '天气' in text and weather_response:
                print("Weather query detected")
                read_text_baidu(f"今天的天气状况如下, 位置:{location.city if location else '当前位置'}")
                read_text_baidu(f"天气：{weather_response['weather_condition']}")
                read_text_baidu(f"温度：{weather_response['temperature']}")

            elif '几点' in text:
                print("Time query detected")
                read_text_baidu(f"现在是 {time.strftime('%H:%M')}")
            elif '空调' in text:
                print("AC query detected")
                read_text_baidu("好的，正在处理空调指令。")
            elif '拜拜' in text or '再见' in text:
                read_text_baidu("拜拜，下次再见！")
                face_detected = False
                break
            else:
                print("Deepseek request")
                response = assistant.chat(text)
                print(f"DeepSeek response: {response}")
                read_text_baidu(response)
        else:
            print("Listening for command...")
            time.sleep(1)

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
                        if detect_face(timeout=60):
                            face_detected = True
                            assistant_thread = threading.Thread(target=assistant_mode)
                            assistant_thread.start()
                            triggered = True
                            break
                        else:
                            read_text_baidu("我无法识别您的面部。如果需要我，请随时叫我。")
                            triggered = True
                            break
                if not triggered:
                    print("Wake word not detected.")
            else:
                print("No speech detected.")
            time.sleep(1)
        else:
            time.sleep(2)

def run_flask():
    """Run the Flask server in a separate thread"""
    app.run(host='0.0.0.0', port=8080, threaded=True)
    
def run_gui():
    """Try Kivy first, fall back to console mode"""
    try:
        # PyQt5 implementation
        from PyQt5.QtWebEngineWidgets import QWebEngineView
        from PyQt5.QtWidgets import QApplication
        from PyQt5.QtCore import QUrl
        import sys
        
        app = QApplication(sys.argv)
        web = QWebEngineView()
        web.load(QUrl("http://localhost:8080"))
        web.show()
        sys.exit(app.exec_())

    except ImportError:
        try:
            # Fallback to Kivy implementation
            from kivy.app import App
            from kivy.uix.label import Label
            
            class SimpleApp(App):
                def build(self):
                    return Label(text='Smart Mirror Running\nhttp://localhost:8080')
            
            SimpleApp().run()
            
        except ImportError:
            # Final fallback to console mode
            print("GUI frameworks not available - running in console mode")
            print("Access the mirror at http://localhost:8080")
            import time
            while True:
                time.sleep(1)

def main() -> None:
    global running, assistant
    
    print("Smart Mirror starting...")

    # Initialize assistant
    assistant = VoiceAssistant(
        baidu_app_id=os.getenv("BAIDU_APP_ID"),
        baidu_api_key=os.getenv("BAIDU_API_KEY"),
        baidu_secret_key=os.getenv("BAIDU_SECRET_KEY"),
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY"),
    )

    # Start Flask server
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()

    # Start voice processing
    voice_thread = threading.Thread(target=wake_word_detection_loop, daemon=True)
    voice_thread.start()

    # Start GUI (will fall back to console if Kivy not available)
    run_gui()
    
    running = False
    print("Smart Mirror stopped.")

if __name__ == "__main__":
    main()
