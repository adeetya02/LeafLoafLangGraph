import React, { useEffect, useState } from 'react';
import { metricsAPI } from '../services/api';
import { 
  ChartBarIcon, 
  BoltIcon,
  ServerIcon
} from '@heroicons/react/24/outline';
import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export const PerformanceMetrics: React.FC = () => {
  const [metrics, setMetrics] = useState<any>(null);
  const [latencyHistory, setLatencyHistory] = useState<number[]>([]);
  const [timeLabels, setTimeLabels] = useState<string[]>([]);

  useEffect(() => {
    // Fetch metrics initially
    fetchMetrics();

    // Update every 5 seconds
    const interval = setInterval(fetchMetrics, 5000);

    return () => clearInterval(interval);
  }, []);

  const fetchMetrics = async () => {
    try {
      const data = await metricsAPI.getMetrics();
      setMetrics(data);

      // Update latency history from recent events
      if (data.recent_events && data.recent_events.length > 0) {
        const latencies = data.recent_events.map((e: any) => e.latency_ms);
        const times = data.recent_events.map((e: any) => 
          new Date(e.timestamp).toLocaleTimeString()
        );
        
        setLatencyHistory(prev => [...prev, ...latencies].slice(-20));
        setTimeLabels(prev => [...prev, ...times].slice(-20));
      }
    } catch (error) {
      console.error('Failed to fetch metrics:', error);
    }
  };

  const chartData = {
    labels: timeLabels,
    datasets: [
      {
        label: 'Response Time (ms)',
        data: latencyHistory,
        borderColor: 'rgb(34, 197, 94)',
        backgroundColor: 'rgba(34, 197, 94, 0.1)',
        tension: 0.4,
        fill: true,
      }
    ]
  };

  const chartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        display: false,
      },
      tooltip: {
        mode: 'index' as const,
        intersect: false,
      },
    },
    scales: {
      x: {
        display: false,
      },
      y: {
        beginAtZero: true,
        max: 500,
        ticks: {
          callback: function(value: any) {
            return value + 'ms';
          }
        }
      }
    }
  };

  if (!metrics) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
        <div className="animate-pulse space-y-4">
          <div className="h-4 bg-gray-200 rounded w-1/2"></div>
          <div className="h-20 bg-gray-200 rounded"></div>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <h3 className="text-lg font-semibold text-gray-900 flex items-center">
          <ChartBarIcon className="w-6 h-6 mr-2 text-gray-700" />
          Performance Metrics
        </h3>
      </div>

      {/* Metrics Grid */}
      <div className="p-6 space-y-4">
        <div className="grid grid-cols-2 gap-4">
          {/* Uptime */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <ServerIcon className="w-5 h-5 text-gray-600" />
              <span className="text-2xl font-bold text-gray-900">
                {Math.floor((metrics.uptime_seconds || 0) / 60)}m
              </span>
            </div>
            <p className="text-sm text-gray-600">Uptime</p>
          </div>

          {/* Active Connections */}
          <div className="bg-gray-50 rounded-lg p-4">
            <div className="flex items-center justify-between mb-2">
              <BoltIcon className="w-5 h-5 text-gray-600" />
              <span className="text-2xl font-bold text-gray-900">
                {metrics.active_websocket_connections || 0}
              </span>
            </div>
            <p className="text-sm text-gray-600">Connections</p>
          </div>
        </div>

        {/* Latency Chart */}
        {latencyHistory.length > 0 && (
          <div>
            <h4 className="text-sm font-medium text-gray-700 mb-2">
              Response Time Trend
            </h4>
            <div className="h-32">
              <Line data={chartData} options={chartOptions} />
            </div>
            <p className="text-xs text-gray-500 mt-2 text-center">
              Target: &lt;300ms (Production SLA)
            </p>
          </div>
        )}

        {/* System Status */}
        <div>
          <h4 className="text-sm font-medium text-gray-700 mb-2">System Status</h4>
          <div className="space-y-2">
            {Object.entries(metrics.system_status || {}).map(([component, status]) => (
              <div key={component} className="flex items-center justify-between text-sm">
                <span className="text-gray-600">{component}</span>
                <span className={`font-medium ${
                  status === 'active' ? 'text-green-600' : 'text-gray-500'
                }`}>
                  {String(status)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Features */}
        <div className="pt-4 border-t border-gray-200">
          <div className="text-xs text-gray-500 space-y-1">
            <p>✅ Gemma 2 9B for intent analysis</p>
            <p>✅ Gemini Pro for entity extraction</p>
            <p>✅ Graphiti + Spanner GraphRAG</p>
            <p>✅ Production vector search (768D)</p>
          </div>
        </div>
      </div>
    </div>
  );
};