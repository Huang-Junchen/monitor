from flask import Flask, render_template, jsonify, send_from_directory, request
from flask_socketio import SocketIO, emit, disconnect
import os
import json
import pandas as pd
import logging
from datetime import datetime, timedelta

# 从配置文件读取配置
with open('config.json') as config_file:
    config = json.load(config_file)

HOST = config['host']
PORT = config['port']

app = Flask(__name__)
socketio = SocketIO(app)

# 配置日志
logging.basicConfig(filename='central_monitor.log', level=logging.INFO, format='%(asctime)s:%(levelname)s:%(message)s')

# 存储 agent 信息
agents = {}
HEARTBEAT_TIMEOUT = 10  # 超时时间（秒）

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/logs')
def list_logs():
    logs = os.listdir('logs')
    return jsonify(logs)

@app.route('/logs/<path:filename>')
def get_log(filename):
    return send_from_directory('logs', filename)

@app.route('/logs/analyze/<path:filename>')
def analyze_log(filename):
    df = pd.read_csv(os.path.join('logs', filename))
    analysis = {
        'summary': df.describe().to_dict()
    }
    return jsonify(analysis)

@socketio.on('connect')
def handle_connect():
    emit('message', {'data': 'Connected to central server'})

@socketio.on('disconnect')
def handle_disconnect():
    for agent_id, info in agents.items():
        if info['sid'] == request.sid:
            del agents[agent_id]
            logging.info(f'Agent {agent_id} disconnected')
            break

@socketio.on('system_data')
def handle_system_data(data):
    agent_id = data['agent_id']
    cpu = data['cpu']
    gpu = data['gpu']
    timestamp = data['timestamp']
    
    if agent_id not in agents:
        agents[agent_id] = {
            'sid': request.sid,
            'last_seen': datetime.now()
        }
    else:
        agents[agent_id]['last_seen'] = datetime.now()
    
    logging.info(f'{agent_id} - CPU: {cpu} | GPU: {gpu} at {timestamp}')
    socketio.emit('system_data', data)  # 将数据转发给所有连接的客户端

@socketio.on('heartbeat')
def handle_heartbeat(data):
    agent_id = data['agent_id']
    agents[agent_id] = {
        'sid': request.sid,
        'last_seen': datetime.now()
    }

def check_agents():
    now = datetime.now()
    to_remove = [agent_id for agent_id, info in agents.items() if (now - info['last_seen']).total_seconds() > HEARTBEAT_TIMEOUT]
    
    for agent_id in to_remove:
        del agents[server_id]
        logging.warning(f'Agent {agent_id} is considered dead')

if __name__ == '__main__':
    if not os.path.exists('logs'):
        os.makedirs('logs')
    
    socketio.start_background_task(check_agents)
    socketio.run(app, host=HOST, port=PORT)

