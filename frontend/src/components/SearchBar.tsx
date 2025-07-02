import React, { useState } from 'react';
import { MagnifyingGlassIcon, AdjustmentsHorizontalIcon } from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';

interface SearchBarProps {
  onSearch: (query: string) => void;
  loading: boolean;
  features: Record<string, boolean>;
  onFeaturesChange: (features: Record<string, boolean>) => void;
}

const quickSearches = [
  { label: '🥛 Milk', query: 'milk' },
  { label: '🥬 Organic', query: 'organic vegetables' },
  { label: '🍞 Gluten Free', query: 'gluten free bread' },
  { label: '⭐ My Usual', query: 'my usual items' },
  { label: '🔄 Reorders', query: 'what needs reordering' },
  { label: '💰 Budget', query: 'budget meals' },
  { label: '🍛 Indian', query: 'sambar ingredients' },
  { label: '👨‍👩‍👧‍👦 Family', query: 'family pack chicken' },
];

export const SearchBar: React.FC<SearchBarProps> = ({ 
  onSearch, 
  loading, 
  features, 
  onFeaturesChange 
}) => {
  const [query, setQuery] = useState('');
  const [showFeatures, setShowFeatures] = useState(false);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      onSearch(query);
    }
  };

  const handleQuickSearch = (searchQuery: string) => {
    setQuery(searchQuery);
    onSearch(searchQuery);
  };

  const toggleFeature = (feature: string) => {
    onFeaturesChange({
      ...features,
      [feature]: !features[feature],
    });
  };

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-6">
      {/* Search Input */}
      <form onSubmit={handleSubmit} className="relative">
        <div className="flex gap-2">
          <div className="relative flex-1">
            <MagnifyingGlassIcon className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-gray-400" />
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Search for groceries..."
              className="w-full pl-10 pr-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              disabled={loading}
            />
          </div>
          <button
            type="submit"
            disabled={loading}
            className="px-6 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            {loading ? (
              <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              'Search'
            )}
          </button>
          <button
            type="button"
            onClick={() => setShowFeatures(!showFeatures)}
            className={`px-4 py-3 rounded-lg border transition-colors ${
              showFeatures 
                ? 'bg-primary-50 border-primary-300 text-primary-700' 
                : 'bg-white border-gray-300 text-gray-700 hover:bg-gray-50'
            }`}
          >
            <AdjustmentsHorizontalIcon className="h-5 w-5" />
          </button>
        </div>
      </form>

      {/* Quick Searches */}
      <div className="mt-4 flex flex-wrap gap-2">
        {quickSearches.map((item) => (
          <button
            key={item.query}
            onClick={() => handleQuickSearch(item.query)}
            className="px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-700 text-sm rounded-full transition-colors"
          >
            {item.label}
          </button>
        ))}
      </div>

      {/* Features Panel */}
      <AnimatePresence>
        {showFeatures && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="mt-4 pt-4 border-t border-gray-200"
          >
            <h3 className="text-sm font-medium text-gray-700 mb-3">Personalization Features</h3>
            <div className="grid grid-cols-2 md:grid-cols-3 gap-3">
              {Object.entries({
                smart_ranking: 'Smart Ranking',
                dietary_filter: 'Dietary Filters',
                budget_aware: 'Budget Awareness',
                quantity_memory: 'Quantity Memory',
                my_usual: 'My Usual Items',
                reorder_intelligence: 'Reorder Intelligence',
              }).map(([key, label]) => (
                <label key={key} className="flex items-center space-x-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={features[key]}
                    onChange={() => toggleFeature(key)}
                    className="rounded text-primary-600 focus:ring-primary-500"
                  />
                  <span className="text-sm text-gray-700">{label}</span>
                </label>
              ))}
            </div>
            <div className="mt-3 text-xs text-gray-500">
              ✨ All features use Pure Graphiti Learning - no hardcoded rules!
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
};