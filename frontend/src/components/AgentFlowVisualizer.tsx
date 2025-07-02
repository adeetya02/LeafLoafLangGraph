import React, { useEffect, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { AgentFlowEvent } from '../types';
import { wsService } from '../services/websocket';
import { 
  CpuChipIcon, 
  MagnifyingGlassIcon, 
  ShoppingCartIcon,
  BoltIcon,
  ChartBarIcon,
  ExclamationTriangleIcon
} from '@heroicons/react/24/outline';

const agentIcons: Record<string, React.ReactNode> = {
  'Supervisor (Gemma 2 9B)': <CpuChipIcon className="w-5 h-5" />,
  'Product Search Agent': <MagnifyingGlassIcon className="w-5 h-5" />,
  'Order Agent': <ShoppingCartIcon className="w-5 h-5" />,
  'Response Compiler': <BoltIcon className="w-5 h-5" />,
  'Graphiti Entity Extraction': <ChartBarIcon className="w-5 h-5" />,
  'Error Handler': <ExclamationTriangleIcon className="w-5 h-5" />,
};

const agentColors: Record<string, string> = {
  'Supervisor (Gemma 2 9B)': 'bg-blue-100 border-blue-300 text-blue-800',
  'Product Search Agent': 'bg-green-100 border-green-300 text-green-800',
  'Order Agent': 'bg-purple-100 border-purple-300 text-purple-800',
  'Response Compiler': 'bg-yellow-100 border-yellow-300 text-yellow-800',
  'Graphiti Entity Extraction': 'bg-indigo-100 border-indigo-300 text-indigo-800',
  'Error Handler': 'bg-red-100 border-red-300 text-red-800',
};

export const AgentFlowVisualizer: React.FC = () => {
  const [events, setEvents] = useState<AgentFlowEvent[]>([]);
  const [isExpanded, setIsExpanded] = useState(true);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);

  useEffect(() => {
    // Connect to WebSocket
    wsService.connect();

    // Subscribe to events
    const unsubscribe = wsService.subscribe((event) => {
      setEvents(prev => {
        const newEvents = [...prev, event];
        // Keep only last 20 events
        return newEvents.slice(-20);
      });
    });

    return () => {
      unsubscribe();
    };
  }, []);

  const formatLatency = (ms: number) => {
    if (ms < 100) return `${ms.toFixed(0)}ms ⚡`;
    if (ms < 300) return `${ms.toFixed(0)}ms ✓`;
    return `${ms.toFixed(0)}ms ⚠️`;
  };

  const formatDetails = (details: Record<string, any>) => {
    if (!showTechnicalDetails) {
      // Show simplified version
      if (details.intent) return `Intent: ${details.intent}`;
      if (details.query) return `Query: "${details.query}"`;
      if (details.total_results !== undefined) return `Found ${details.total_results} products`;
      if (details.action) return `Action: ${details.action}`;
    }
    
    // Show full technical details
    return (
      <pre className="text-xs mt-1 bg-gray-50 p-2 rounded overflow-x-auto">
        {JSON.stringify(details, null, 2)}
      </pre>
    );
  };

  return (
    <div className="fixed bottom-4 right-4 w-96 max-h-[600px] bg-white rounded-lg shadow-2xl border border-gray-200 overflow-hidden z-50">
      {/* Header */}
      <div 
        className="bg-gradient-to-r from-primary-600 to-primary-700 text-white p-4 cursor-pointer flex items-center justify-between"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-center space-x-2">
          <BoltIcon className="w-6 h-6" />
          <h3 className="font-semibold">Agent Flow Monitor</h3>
        </div>
        <div className="flex items-center space-x-2">
          <span className="text-xs bg-white/20 px-2 py-1 rounded">
            {events.length} events
          </span>
          <button className="text-white hover:text-gray-200">
            {isExpanded ? '−' : '+'}
          </button>
        </div>
      </div>

      {/* Controls */}
      {isExpanded && (
        <div className="p-2 bg-gray-50 border-b flex items-center justify-between">
          <label className="flex items-center space-x-2 text-sm">
            <input
              type="checkbox"
              checked={showTechnicalDetails}
              onChange={(e) => setShowTechnicalDetails(e.target.checked)}
              className="rounded text-primary-600"
            />
            <span>Show Technical Details</span>
          </label>
          <button
            onClick={() => setEvents([])}
            className="text-xs text-gray-500 hover:text-gray-700"
          >
            Clear
          </button>
        </div>
      )}

      {/* Events */}
      {isExpanded && (
        <div className="overflow-y-auto max-h-[400px] p-2 space-y-2">
          <AnimatePresence>
            {events.map((event, index) => (
              <motion.div
                key={`${event.timestamp}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, x: -20 }}
                className={`p-3 rounded-lg border ${agentColors[event.agent] || 'bg-gray-100 border-gray-300'}`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-start space-x-2">
                    <div className="mt-0.5">
                      {agentIcons[event.agent] || <CpuChipIcon className="w-5 h-5" />}
                    </div>
                    <div className="flex-1">
                      <div className="font-medium text-sm">{event.agent}</div>
                      <div className="text-xs text-gray-600 mt-1">{event.action}</div>
                      <div className="text-xs text-gray-500 mt-1">
                        {formatDetails(event.details)}
                      </div>
                    </div>
                  </div>
                  <div className="text-xs font-mono whitespace-nowrap ml-2">
                    {formatLatency(event.latency_ms)}
                  </div>
                </div>
                <div className="text-xs text-gray-400 mt-1">
                  {new Date(event.timestamp).toLocaleTimeString()}
                </div>
              </motion.div>
            ))}
          </AnimatePresence>

          {events.length === 0 && (
            <div className="text-center text-gray-500 py-8">
              <BoltIcon className="w-12 h-12 mx-auto mb-2 text-gray-300" />
              <p className="text-sm">Waiting for agent activity...</p>
              <p className="text-xs mt-1">Perform a search to see the flow</p>
            </div>
          )}
        </div>
      )}

      {/* Summary */}
      {isExpanded && events.length > 0 && (
        <div className="p-3 bg-gray-50 border-t text-xs">
          <div className="flex justify-between">
            <span className="text-gray-600">Total Latency:</span>
            <span className="font-mono font-medium">
              {events.reduce((sum, e) => sum + e.latency_ms, 0).toFixed(0)}ms
            </span>
          </div>
        </div>
      )}
    </div>
  );
};