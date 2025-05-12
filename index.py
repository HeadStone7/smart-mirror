# from kivy.app import App
# from kivy.uix.boxlayout import BoxLayout
# from kivy.uix.label import Label
# from kivy.clock import Clock
import requests
import webview

class SmartMirrorApp(App):
    def build(self):
        self.main_layout = BoxLayout(orientation='vertical')
        self.content_label = Label(text="Loading...", markup=True)
        self.main_layout.add_widget(self.content_label)
        Clock.schedule_interval(self.update_content, 5) # Update every 5 seconds
        return self.main_layout

    def update_content(self, dt):
        try:
            # url = "http://localhost:8080"
            url = "https://www.bing.com"
            response = requests.get(url)
            response.raise_for_status()
            self.content_label.text = response.text # Or process and format the data
        except requests.exceptions.RequestException as e:
            self.content_label.text = f"[color=ff0000]Error loading data:[/color] {e}"

if __name__ == '__main__':
    webview.create_window("SmartMirror Display", "http://localhost:8080")
    webview.start()
