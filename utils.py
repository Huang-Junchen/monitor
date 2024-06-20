import os
import psutil
import GPUtil
import subprocess
import pandas as pd

# 创建目录和文件
def create_directory(base_path, dir_name):
    path = os.path.join(base_path, dir_name)
    if not os.path.exists(path):
        os.makedirs(path)
    return path

def save_to_csv(data, filename, mode='w'):
    df = pd.DataFrame(data)
    df.to_csv(filename, mode=mode, header=not os.path.exists(filename), index=False)

def get_cpu_info():
    cpu_info = {
        'percentages': psutil.cpu_percent(percpu=True),
        'temperatures': []
    }
    try:
        temps = psutil.sensors_temperatures()
        if 'coretemp' in temps:
            cpu_info['temperatures'] = [temp.current for temp in temps['coretemp']]
    except Exception as e:
        print(f"Error reading CPU temperature: {e}")
    return cpu_info

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

def flatten_data(data):
    flattened_data = []
    for entry in data:
        base = {
            'timestamp': entry['timestamp'],
            'agent_id': entry['agent_id']
        }
        for i, cpu in enumerate(entry['cpu']['percentages']):
            base[f'cpu_{i}_usage'] = cpu
        for i, temp in enumerate(entry['cpu']['temperatures']):
            base[f'cpu_{i}_temperature'] = temp

        # Create separate entries for each GPU
        for gpu in entry['gpu']:
            base.update({
                f'gpu_{gpu["id"]}_name': gpu['name'],
                f'gpu_{gpu["id"]}_temperature': gpu['temperature'],
                f'gpu_{gpu["id"]}_power_usage': gpu['powerUsage'],
                f'gpu_{gpu["id"]}_load': gpu['load'],
                f'gpu_{gpu["id"]}_memory_used': gpu['memoryUsed'],
                f'gpu_{gpu["id"]}_memory_total': gpu['memoryTotal']
            })

        flattened_data.append(base)  # Append 
    return flattened_data
