import geocoder
from face_recognition_system import FaceRecognition
from services.speech_recognizer import RecognizeSpeech
from utils import read_text_baidu
from weather_api.weather_service import WeatherService
import time


def detect_face() -> bool:
    """Detect a face within the given timeout period."""
    face_system = FaceRecognition()
    image_paths = [r"C:\Users\Josh\Pictures\Saved Pictures\id.jpg"]
    image_paths1 = []
    face_system.add_new_person("Joseph", image_paths)
    face_system.add_new_person("Atigo", image_paths1)

    try:
        recognized: bool = face_system.start_recognition()
        if recognized:
            print("Recognition done")
            return True
        else:
            print("Recognition failed, trying again...")
            time.sleep(0.1)  # Small delay to prevent CPU overload
    except Exception as e:
        print(f"Error during recognition: {e}")
    return False


def user_speech_recognition() -> str:
    speech_recognition = RecognizeSpeech()
    recognized_text = speech_recognition.recognize_from_microphone()
    return recognized_text


def get_user_location():
    localization = geocoder.ip("me")

    return localization


if __name__ == "__main__":
    print(f"{get_user_location()}")
    location = get_user_location()
    weather = WeatherService()
    response = weather.get_weather_info(get_user_location().lng, get_user_location().lat)

    while True:
        if detect_face():
            time.sleep(2)
            read_text_baidu(f"我能为您做些什么？")

            #while listening condition
            text = user_speech_recognition()
            if '天气' in text:
                print("weather query detected")

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
            elif '拜拜' in text:
                read_text_baidu("拜拜下次再见")
                break
            else:
                print("Deepseek request")

        else:
            print("Recognition failed")
