import React from 'react';
import { UserPersona } from '../types';
import { 
  CodeBracketIcon,
  ShoppingBagIcon 
} from '@heroicons/react/24/outline';

interface HeaderProps {
  user: UserPersona;
  onUserChange: (persona: UserPersona) => void;
  showTechnical: boolean;
  onToggleTechnical: () => void;
}

const personas: Record<UserPersona, { name: string; description: string }> = {
  demo_user: { name: 'Demo User', description: 'Default profile' },
  health_conscious: { name: 'Health Conscious', description: 'Gluten-free, organic preferences' },
  budget_shopper: { name: 'Budget Shopper', description: 'Value-focused shopping' },
  family_shopper: { name: 'Family Shopper', description: 'Bulk quantities for family' },
};

export const Header: React.FC<HeaderProps> = ({ 
  user, 
  onUserChange, 
  showTechnical, 
  onToggleTechnical 
}) => {
  return (
    <header className="bg-white shadow-sm border-b border-gray-200">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center">
              <ShoppingBagIcon className="h-8 w-8 text-primary-600" />
              <h1 className="ml-2 text-2xl font-bold text-gray-900">LeafLoaf</h1>
            </div>
            <div className="hidden sm:block">
              <span className="px-3 py-1 text-xs font-medium bg-primary-100 text-primary-800 rounded-full">
                Production Demo
              </span>
            </div>
          </div>

          {/* Right side */}
          <div className="flex items-center space-x-4">
            {/* Technical Toggle */}
            <button
              onClick={onToggleTechnical}
              className={`flex items-center space-x-2 px-3 py-2 rounded-lg transition-colors ${
                showTechnical 
                  ? 'bg-primary-100 text-primary-700' 
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              <CodeBracketIcon className="h-5 w-5" />
              <span className="text-sm font-medium">Technical View</span>
            </button>

            {/* User Selector */}
            <div className="relative">
              <select
                value={user}
                onChange={(e) => onUserChange(e.target.value as UserPersona)}
                className="appearance-none bg-white border border-gray-300 rounded-lg px-4 py-2 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-primary-500"
              >
                {Object.entries(personas).map(([key, persona]) => (
                  <option key={key} value={key}>
                    {persona.name}
                  </option>
                ))}
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-gray-700">
                <svg className="fill-current h-4 w-4" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20">
                  <path d="M5.293 7.293a1 1 0 011.414 0L10 10.586l3.293-3.293a1 1 0 111.414 1.414l-4 4a1 1 0 01-1.414 0l-4-4a1 1 0 010-1.414z" />
                </svg>
              </div>
            </div>

            {/* Status Indicator */}
            <div className="flex items-center space-x-2">
              <div className="flex items-center space-x-1">
                <div className="h-2 w-2 bg-green-400 rounded-full animate-pulse"></div>
                <span className="text-xs text-gray-600">Live</span>
              </div>
            </div>
          </div>
        </div>

        {/* User Description */}
        <div className="pb-2">
          <p className="text-xs text-gray-500">
            {personas[user].description}
          </p>
        </div>
      </div>
    </header>
  );
};