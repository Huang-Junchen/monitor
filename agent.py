import socketio
import time
import json
from datetime import datetime
from utils import *

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

# 初始化日志目录和文件
start_time = datetime.now()
logs_dir = create_directory('.', 'logs')
date_dir = create_directory(logs_dir, start_time.strftime('%Y-%m-%d'))
hourly_filename = os.path.join(date_dir, f"{start_time.strftime('%Y-%m-%d_%H')}.csv")
summary_dir = create_directory(logs_dir, 'summary')
summary_dir = create_directory(summary_dir, f'{AGENT_ID}')
summary_filename = os.path.join(summary_dir, f"{start_time.strftime('%Y-%m-%d_%H-%M-%S')}.csv")

# 初始化当前小时
current_hour = start_time.hour

def collect_and_send_data():
    global current_hour, hourly_filename
    while True:
        now = datetime.now()
        cpu_info = get_cpu_info()
        gpu_info = get_gpu_info()

        data = {
            'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'),
            'agent_id': AGENT_ID,
            'cpu': cpu_info,
            'gpu': gpu_info
        }
        
        print(json.dumps(data, indent=4))
        flattened_data = flatten_data([data])

        save_to_csv(flattened_data, hourly_filename, mode='a') # 追加到每小时文件
        save_to_csv(flattened_data, summary_filename, mode='a') # 追加到总结文件
        
        sio.emit('system_data', data)
        sio.emit('heartbeat', {'agent_id': AGENT_ID})

        # 检查是否跨小时
        if now.hour != current_hour:
            hourly_filename = os.path.join(date_dir, f"{now.strftime('%Y-%m-%d_%H')}.csv")
            current_hour = now.hour

        time.sleep(2)

if __name__ == '__main__':
    try:
        sio.connect(SERVER_URL)
        collect_and_send_data()
    except KeyboardInterrupt:
        save_final_csv()
        print("Monitoring stopped and data saved.")

