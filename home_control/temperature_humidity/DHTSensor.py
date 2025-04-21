#!/usr/bin/python
# -*- coding: utf-8 -*-

import time
import Adafruit_DHT

# 定义DHT11传感器类型和GPIO引脚号（BCM编号方式）
DHT_SENSOR = Adafruit_DHT.DHT11
DHT_PIN = 4  # GPIO4，对应物理引脚7

def read_dht11():
    """
    读取DHT11传感器数据
    返回：温度值（摄氏度）和湿度值（百分比）
    """
    try:
        # 使用read()方法替代read_retry()，避免潜在的驱动问题
        humidity, temperature = Adafruit_DHT.read(DHT_SENSOR, DHT_PIN)
        
        if humidity is not None and temperature is not None:
            # 确保返回的数据在合理范围内
            if 0 <= humidity <= 100 and -40 <= temperature <= 80:
                return temperature, humidity
        
        print("无法读取传感器数据，将在下次循环重试")
        return None, None
            
    except Exception as e:
        print(f"读取传感器数据时发生错误，请确保硬件连接正确")
        return None, None

def main():
    """
    主函数：循环读取并显示温湿度数据
    """
    print("DHT11温湿度传感器测试程序")
    print(f"使用GPIO引脚: {DHT_PIN}")
    print("按Ctrl+C退出程序\n")
    
    try:
        while True:
            temp, humidity = read_dht11()
            
            if temp is not None and humidity is not None:
                print(f"温度: {temp:.1f}°C")
                print(f"湿度: {humidity:.1f}%")
            
            # 等待2秒后再次读取
            time.sleep(2)
            
    except KeyboardInterrupt:
        print("\n程序已退出")

if __name__ == "__main__":
    main()