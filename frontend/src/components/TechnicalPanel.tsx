import React from 'react';
import { 
  CpuChipIcon, 
  ClockIcon, 
  MagnifyingGlassIcon,
  ChartBarIcon,
  BeakerIcon 
} from '@heroicons/react/24/outline';

interface TechnicalPanelProps {
  metadata: any;
}

export const TechnicalPanel: React.FC<TechnicalPanelProps> = ({ metadata }) => {
  if (!metadata) return null;

  const formatLatency = (ms: number) => {
    if (ms < 100) return { value: `${ms.toFixed(0)}ms`, color: 'text-green-600' };
    if (ms < 300) return { value: `${ms.toFixed(0)}ms`, color: 'text-yellow-600' };
    return { value: `${ms.toFixed(0)}ms`, color: 'text-red-600' };
  };

  const totalLatency = formatLatency(metadata.total_latency_ms);

  return (
    <div className="bg-gray-50 rounded-lg border border-gray-200 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold text-gray-700 flex items-center">
          <BeakerIcon className="w-4 h-4 mr-1" />
          Technical Analysis
        </h3>
        <span className={`text-sm font-mono ${totalLatency.color}`}>
          Total: {totalLatency.value}
        </span>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        {/* Intent Detection */}
        <div className="bg-white rounded p-3 border border-gray-200">
          <div className="flex items-center text-xs text-gray-600 mb-1">
            <CpuChipIcon className="w-3 h-3 mr-1" />
            Gemma 2 9B
          </div>
          <div className="text-sm font-medium text-gray-900">
            Intent: {metadata.intent}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Confidence: {((metadata.confidence || 0.8) * 100).toFixed(0)}%
          </div>
        </div>

        {/* Search Strategy */}
        <div className="bg-white rounded p-3 border border-gray-200">
          <div className="flex items-center text-xs text-gray-600 mb-1">
            <MagnifyingGlassIcon className="w-3 h-3 mr-1" />
            Search Strategy
          </div>
          <div className="text-sm font-medium text-gray-900">
            α = {metadata.search_alpha?.toFixed(2) || '0.50'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {metadata.search_alpha < 0.3 ? 'Keyword' : 
             metadata.search_alpha > 0.7 ? 'Semantic' : 'Hybrid'}
          </div>
        </div>

        {/* Personalization */}
        <div className="bg-white rounded p-3 border border-gray-200">
          <div className="flex items-center text-xs text-gray-600 mb-1">
            <ChartBarIcon className="w-3 h-3 mr-1" />
            Personalization
          </div>
          <div className="text-sm font-medium text-gray-900">
            {metadata.personalization_applied ? 'Applied' : 'None'}
          </div>
          <div className="text-xs text-gray-500 mt-1">
            Graphiti + Spanner
          </div>
        </div>

        {/* Session */}
        <div className="bg-white rounded p-3 border border-gray-200">
          <div className="flex items-center text-xs text-gray-600 mb-1">
            <ClockIcon className="w-3 h-3 mr-1" />
            Session
          </div>
          <div className="text-sm font-medium text-gray-900">
            Active
          </div>
          <div className="text-xs text-gray-500 mt-1 truncate">
            {metadata.session_id?.substring(0, 12)}...
          </div>
        </div>
      </div>

      {/* Agent Latencies */}
      {metadata.agent_latencies && Object.keys(metadata.agent_latencies).length > 0 && (
        <div className="mt-3 pt-3 border-t border-gray-200">
          <h4 className="text-xs font-medium text-gray-700 mb-2">Component Latencies</h4>
          <div className="space-y-1">
            {Object.entries(metadata.agent_latencies).map(([agent, latency]) => {
              const formatted = formatLatency(latency as number);
              return (
                <div key={agent} className="flex justify-between text-xs">
                  <span className="text-gray-600">{agent}</span>
                  <span className={`font-mono ${formatted.color}`}>
                    {formatted.value}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
};