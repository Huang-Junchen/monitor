import psutil
import GPUtil
import subprocess
import socketio
import time
import json
import os
import pandas as pd
from datetime import datetime

# 从配置文件读取配置
with open('config.json') as config_file:
    config = json.load(config_file)

SERVER_URL = config['server_url']
AGENT_ID = config['agent_id']

sio = socketio.Client()

@sio.event
def connect():
    print("Connected to central server")
    sio.emit('heartbeat', {'agent_id': AGENT_ID})

@sio.event
def disconnect():
    print("Disconnected from central server")

# 准备数据存储
data_records = []
start_time = datetime.now()
current_hour = start_time.hour

# 创建目录和文件
def create_directory(base_path, dir_name):
    path = os.path.join(base_path, dir_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def save_to_csv(data, filename):
    df = pd.DataFrame(data)
    df.to_csv(filename, index=False)

def save_hourly_csv():
    global data_records
    logs_dir = create_directory('.', 'logs')
    date_dir = create_directory(logs_dir, start_time.strftime('%Y-%m-%d'))
    filename = os.path.join(date_dir, f"{datetime.now().strftime('%Y-%m-%d_%H')}.csv")
    save_to_csv(data_records, filename)
    data_records = []  # 清空记录以减少内存占用

def save_final_csv():
    logs_dir = create_directory('.', 'logs')
    summary_dir = create_directory(logs_dir, 'summary')
    filename = os.path.join(summary_dir, f"summary_{AGENT_ID}_{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.csv")
    save_to_csv(data_records, filename)

def get_cpu_info():
    cpu_percentages = psutil.cpu_percent(percpu=True)
    cpu_temps = []
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            for entry in temps['coretemp']:
                cpu_temps.append(entry.current)
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")

    return cpu_percentages, cpu_temps

def get_gpu_info():
    gpus = GPUtil.getGPUs()
    gpu_info = []
    for gpu in gpus:
        power_usage = get_gpu_power_usage(gpu.id)
        info = {
            'id': gpu.id,
            'name': gpu.name,
            'load': gpu.load * 100,
            'memoryUsed': gpu.memoryUsed,
            'memoryTotal': gpu.memoryTotal,
            'temperature': gpu.temperature,
            'powerUsage': power_usage
        }
        gpu_info.append(info)
    return gpu_info

def get_gpu_power_usage(gpu_id):
    try:
        result = subprocess.run(['nvidia-smi', '-i', str(gpu_id), '--query-gpu=power.draw', '--format=csv,noheader,nounits'], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        power_usage = float(result.stdout.strip())
    except Exception as e:
        print(f"Error reading GPU power usage: {e}")
        power_usage = None
    return power_usage

def collect_and_send_data():
    global current_hour
    while True:
        now = datetime.now()
        cpu_percentages, cpu_temps = get_cpu_info()
        gpu_info = get_gpu_info()

        data = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'agent_id': AGENT_ID,
            'cpu': {
                'percentages': cpu_percentages,
                'temperatures': cpu_temps
            },
            'gpu': gpu_info
        }
        
        print(data)
        data_records.append(data)
        
        sio.emit('system_data', data)
        sio.emit('heartbeat', {'agent_id': AGENT_ID})

        # 每小时保存一次数据
        if now.hour != current_hour:
            save_hourly_csv()
            current_hour = now.hour

        time.sleep(2)

if __name__ == '__main__':
    try:
        sio.connect(SERVER_URL)
        collect_and_send_data()
    except KeyboardInterrupt:
        save_final_csv()
        print("Monitoring stopped and data saved.")

