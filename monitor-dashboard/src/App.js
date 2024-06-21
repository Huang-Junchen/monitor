import React, { useEffect, useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Link, useParams } from 'react-router-dom';
import io from 'socket.io-client';
import { Line, Bar } from 'react-chartjs-2';
import {
    Chart as ChartJS,
    CategoryScale,
    LinearScale,
    PointElement,
    BarElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    TimeScale,
} from 'chart.js';
import 'chartjs-adapter-date-fns';
import './App.css';

ChartJS.register(
    CategoryScale,
    LinearScale,
    PointElement,
    BarElement,
    LineElement,
    Title,
    Tooltip,
    Legend,
    TimeScale
);

const socket = io('http://192.168.10.78:5000');  // 修改为你的 Flask 服务器地址

const App = () => {
    const [cpuData, setCpuData] = useState({});
    const [gpuData, setGpuData] = useState({});
    const [agents, setAgents] = useState({});

    useEffect(() => {
        socket.on('connect', () => {
            console.log('Connected to server');
        });

        socket.on('disconnect', () => {
            console.log('Disconnected from server');
        });

        socket.on('system_data', (data) => {
            const timestamp = new Date(data.timestamp);
            setCpuData(prevData => ({
                ...prevData,
                [data.agent_id]: (prevData[data.agent_id] || []).concat({ time: timestamp, data: data.cpu.temperatures })
            }));
            setGpuData(prevData => ({
                ...prevData,
                [data.agent_id]: (prevData[data.agent_id] || []).concat({ time: timestamp, data: data.gpu.map(gpu => gpu.temperature) })
            }));
            setAgents(prevAgents => ({ ...prevAgents, [data.agent_id]: { online: true, last_seen: timestamp } }));
        });

        return () => {
            socket.off('connect');
            socket.off('disconnect');
            socket.off('system_data');
        };
    }, []);

    const checkAgentStatus = () => {
        const now = new Date();
        const timeout = 30000; // 设置30秒超时
        const updatedAgents = { ...agents };
        Object.keys(updatedAgents).forEach(agentId => {
            if (now - updatedAgents[agentId].last_seen > timeout) {
                updatedAgents[agentId].online = false;
            }
        });
        setAgents(updatedAgents);
    };

    useEffect(() => {
        const interval = setInterval(checkAgentStatus, 10000); // 每10秒检查一次agent状态
        return () => clearInterval(interval);
    }, [agents]);

    return (
        <Router>
            <div>
                <h1>Agent Monitor Dashboard</h1>
                <Routes>
                    <Route path="/" element={<AgentsOnline agents={agents} />} />
                    <Route path="/agent/:agentId" element={<AgentCharts cpuData={cpuData} gpuData={gpuData} />} />
                </Routes>
            </div>
        </Router>
    );
};

const AgentsOnline = ({ agents }) => {

    return (
        <div>
            <h2>Agents Online</h2>
            <ul>
                {Object.keys(agents).map(agentId => (
                    <li key={agentId} style={{ color: agents[agentId].online ? 'green' : 'red' }}>
                        {agents[agentId].online ? <Link to={`/agent/${agentId}`}>{agentId}</Link> : agentId}
                    </li>
                ))}
            </ul>
        </div>
    );
};

const AgentCharts = ({ cpuData, gpuData }) => {
    const { agentId } = useParams();
    const agentCpuData = cpuData[agentId] || [];
    const agentGpuData = gpuData[agentId] || [];
    const [timeUnit, setTimeUnit] = useState('minute');

    const getCpuChartData = () => {
        if (agentCpuData.length === 0 || !agentCpuData[0]) return { labels: [], datasets: [] };
        return {
            labels: agentCpuData.map(entry => entry.time),
            datasets: agentCpuData[0].data.map((_, index) => ({
                label: `CPU ${index} Temperature`,
                data: agentCpuData.map(entry => ({ x: entry.time, y: entry.data[index] })),
                borderColor: `rgba(${index * 50}, 99, 132, 1)`,
                fill: false,
                pointRadius: 3,
                pointHoverRadius: 6,
                showLine: true,
            }))
        };
    };

    const getGpuChartData = (gpuIndex) => {
        if (agentGpuData.length === 0) return { labels: [], datasets: [] };
        return {
            labels: agentGpuData.map(entry => entry.time),
            datasets: [{
                label: `GPU ${gpuIndex} Temperature`,
                data: agentGpuData.map(entry => ({ x: entry.time, y: entry.data[gpuIndex] || 0 })),
                borderColor: 'rgba(255, 99, 132, 1)',
                fill: false,
                pointRadius: 3,
                pointHoverRadius: 6,
                showLine: true,
            }]
        };
    };

    const getGpuBarChartData = () => {
      const labels = Object.keys(gpuData);
      const data = labels.map(agentId => {
          const agentGpuData = gpuData[agentId];
          if (agentGpuData && agentGpuData.length > 0) {
              const latestData = agentGpuData[agentGpuData.length - 1];
              return latestData.data;
          }
          return [];
      });

      const flattenedData = data.flat();
      const agentsList = labels.flatMap(agentId => {
          const agentGpuData = gpuData[agentId];
          if (agentGpuData && agentGpuData.length > 0) {
              const latestData = agentGpuData[agentGpuData.length - 1];
              return latestData.data.map((_, index) => `GPU ${index}`);
          }
          return [];
      });

      return {
          labels: agentsList,
          datasets: [{
              label: 'GPU Temperatures',
              data: flattenedData,
              backgroundColor: 'rgba(75, 192, 192, 0.2)',
              borderColor: 'rgba(75, 192, 192, 1)',
              borderWidth: 1,
          }],
      };
  };

    return (
        <div>
            <h2>Agent {agentId}</h2>
            <div>
                <label>Time Unit: </label>
                <select onChange={(e) => setTimeUnit(e.target.value)}>
                    <option value="minute">Minute</option>
                    <option value="quarter">Quarter Hour</option>
                    <option value="half">Half Hour</option>
                    <option value="hour">Hour</option>
                    <option value="day">Day</option>
                </select>
            </div>
            <div className="chart-container">
                <h2>Current GPU Temperatures</h2>
                <Bar
                    data={getGpuBarChartData()}
                    options={{
                        // indexAxis: 'y',
                        scales: {
                            y: {
                                ticks: {
                                    callback: function(value) {
                                        return value + '°C';
                                    }
                                }
                            }
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function(context) {
                                        return `${context.dataset.label}: ${context.raw}°C`;
                                    }
                                }
                            }
                        }
                    }}
                />
            </div>
            <div className="chart-container">
                <h2>CPU Temperatures</h2>
                <Line
                    data={getCpuChartData()}
                    options={{
                        scales: {
                            x: {
                                type: 'time',
                                time: {
                                    unit: timeUnit,
                                }
                            },
                            y: {
                              min: Math.min(agentCpuData.map(entry => entry.data).flat()) - 5,
                              max: Math.max(agentCpuData.map(entry => entry.data).flat()) + 5,
                          },
                        },
                        plugins: {
                            tooltip: {
                                callbacks: {
                                    label: function (context) {
                                        return `${context.dataset.label}: ${context.raw.y}°C`;
                                    }
                                }
                            }
                        }
                    }}
                />
            </div>
            {agentGpuData[0]?.data.map((_, index) => (
                <div key={index} className="chart-container">
                    <h2>GPU {index} Temperatures</h2>
                    <Line
                        data={getGpuChartData(index)}
                        options={{
                            scales: {
                                x: {
                                    type: 'time',
                                    time: {
                                        unit: timeUnit,
                                    }
                                },
                                y: {
                                    ticks: {
                                        callback: function(value) {
                                            return value + '°C';
                                        }
                                    }
                                }
                            },
                            plugins: {
                                tooltip: {
                                    callbacks: {
                                        label: function (context) {
                                            return `${context.dataset.label}: ${context.raw.y}°C`;
                                        }
                                    }
                                }
                            }
                        }}
                    />
                </div>
            ))}
        </div>
    );
};

export default App;
