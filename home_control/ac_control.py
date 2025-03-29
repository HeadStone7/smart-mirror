import os
from pathlib import Path
import RPi.GPIO as GPIO
import requests
import time
from voice_feat.voice_feat_system import VoiceAssistant

class ACController:
    """空调控制器类，支持语音控制空调。
    提供两种控制方式：
    1. 通过涂鸦API控制红外发射模块
    2. 通过MQTT协议控制WiFi空调（暂未实现）
    """

    def __init__(self, tuya_api_key=None, tuya_api_secret=None, ir_gpio_pin=18):
        """初始化空调控制器

        Args:
            tuya_api_key (str): 涂鸦API密钥
            tuya_api_secret (str): 涂鸦API密钥
            ir_gpio_pin (int): 红外发射模块连接的GPIO引脚号
        """
        # 初始化语音助手
        self.voice_assistant = VoiceAssistant()
        
        # 涂鸦API配置
        self.tuya_api_id =  os.getenv('TUYA_API_ID')
        self.tuya_api_secret =  os.getenv('TUYA_API_SECRET')
        self.tuya_api_endpoint = 'https://openapi.tuyacn.com/v1.0/infrareds'
        
        # GPIO配置
        self.ir_gpio_pin = ir_gpio_pin
        self._setup_gpio()
        
        # 空调状态
        self.ac_status = {
            'power': False,
            'temperature': 25,
            'mode': 'cool',  # cool, heat, auto, dry, fan
            'fan_speed': 'auto'  # auto, low, medium, high
        }

    def _setup_gpio(self):
        """设置GPIO引脚"""
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(self.ir_gpio_pin, GPIO.OUT)

    def _get_tuya_token(self):
        """获取涂鸦API访问令牌"""
        try:
            response = requests.get(
                f'{self.tuya_api_endpoint}/token',
                headers={
                    'client_id': self.tuya_api_id,
                    'secret': self.tuya_api_secret
                }
            )
            return response.json()['result']['access_token']
        except Exception as e:
            print(f'获取涂鸦token失败: {e}')
            return None

    def _send_ir_command(self, command):
        """发送红外命令

        Args:
            command (dict): 包含命令类型和参数的字典
        """
        try:
            token = self._get_tuya_token()
            if not token:
                return False

            # 调用涂鸦API获取红外编码
            response = requests.post(
                f'{self.tuya_api_endpoint}/codes',
                headers={'Authorization': f'Bearer {token}'},
                json={
                    'device_type': 'air_conditioner',
                    'brand': 'universal',
                    'command': command
                }
            )

            if response.status_code == 200:
                ir_code = response.json()['result']['code']
                # 通过GPIO发送红外编码
                self._transmit_ir_code(ir_code)
                return True
            return False
        except Exception as e:
            print(f'发送红外命令失败: {e}')
            return False

    def _transmit_ir_code(self, ir_code):
        """通过GPIO发送红外编码

        Args:
            ir_code (str): 红外编码
        """
        pwm = None
        try:
            # 将16进制字符串转换为整数
            ir_int = int(ir_code, 16)
            # 将整数转换为二进制字符串，并去除'0b'前缀
            ir_binary = bin(ir_int)[2:]
            # 确保二进制序列长度为8的倍数，不足则在前面补0
            ir_binary = ir_binary.zfill((len(ir_binary) + 7) // 8 * 8)
            
            # 设置GPIO为输出模式
            GPIO.setup(self.ir_gpio_pin, GPIO.OUT)
            
            # 设置PWM频率为38KHz，这是大多数红外设备的标准载波频率
            pwm = GPIO.PWM(self.ir_gpio_pin, 38000)
            # 设置占空比为50%以获得最佳信号质量
            pwm.start(50)
            
            # 发送引导码（9ms载波 + 4.5ms空闲）
            pwm.ChangeDutyCycle(50)
            time.sleep(0.009)  # 9ms载波
            pwm.ChangeDutyCycle(0)
            time.sleep(0.0045)  # 4.5ms空闲
            
            # 根据二进制序列发送信号
            for bit in ir_binary:
                if bit == '1':
                    # 发送载波信号（600微秒载波 + 600微秒空闲）
                    pwm.ChangeDutyCycle(50)
                    time.sleep(0.0006)  # 600微秒载波
                    pwm.ChangeDutyCycle(0)
                    time.sleep(0.0006)  # 600微秒空闲
                else:
                    # 发送空闲信号（600微秒载波 + 1800微秒空闲）
                    pwm.ChangeDutyCycle(50)
                    time.sleep(0.0006)  # 600微秒载波
                    pwm.ChangeDutyCycle(0)
                    time.sleep(0.0018)  # 1800微秒空闲
            
            # 发送结束码（600微秒载波）
            pwm.ChangeDutyCycle(50)
            time.sleep(0.0006)
            pwm.ChangeDutyCycle(0)
            
            return True
        except Exception as e:
            print(f'发送红外信号失败: {e}')
            return False
        finally:
            # 确保PWM输出被正确停止并清理GPIO资源
            if pwm:
                try:
                    pwm.stop()
                    GPIO.cleanup(self.ir_gpio_pin)
                except:
                    pass

    def _parse_voice_command(self, text):
        """解析语音命令

        Args:
            text (str): 语音识别结果

        Returns:
            dict: 解析后的命令
        """
        command = {}

        # 解析开关命令
        if '空调' in text:
            if '开' in text:
                command['power'] = 'on'
            elif '关' in text:
                command['power'] = 'off'

            # 解析温度命令
            if '温度' in text:
                import re
                temp_match = re.search(r'(\d+)', text)
                if temp_match:
                    temp = int(temp_match.group(1))
                    if 16 <= temp <= 30:
                        command['temperature'] = temp
                    elif '高' in text:
                        command['temperature'] = min(30, self.ac_status['temperature'] + temp)
                    elif '低' in text:
                        command['temperature'] = max(16, self.ac_status['temperature'] - temp)
            # 解析模式命令
            if '制冷' in text:
                command['mode'] = 'cool'
            elif '制热' in text:
                command['mode'] = 'heat'
            elif '自动' in text and '风速' not in text:
                command['mode'] = 'auto'
            elif '除湿' in text:
                command['mode'] = 'dry'
            elif '送风' in text:
                command['mode'] = 'fan'

            # 解析风速命令
            if '风速' in text:
                if '自动' in text :
                    command['fan_speed'] = 'auto'
                elif '低' in text :
                    command['fan_speed'] = 'low'
                elif '中' in text :
                    command['fan_speed'] = 'medium'
                elif '高' in text :
                    command['fan_speed'] = 'high'

        return command

    def control_by_voice(self, text):
        """通过语音控制空调"""

        # 解析语音命令
        command = self._parse_voice_command(text)
        if not command:
            print('无法解析语音指令')
            return False

        # 发送红外命令
        success = self._send_ir_command(command)
        if success:
            # 更新空调状态
            self.ac_status.update(command)
            print(f'执行命令成功: {command}')
        else:
            print('执行命令失败')

        return success

if __name__ == '__main__':
    ac = ACController()
    text = '空调开，温度25度，风速自动'
    # text = '空调关'
    ac.control_by_voice(text)

    # def control_by_mqtt(self):
    #     """通过MQTT协议控制WiFi空调（待实现）"""
    #     pass