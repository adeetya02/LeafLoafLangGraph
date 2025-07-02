import React, { useState } from 'react';
import { Product, UserPersona } from '../types';
import { ProductCard } from './ProductCard';
import { motion, AnimatePresence } from 'framer-motion';
import { FunnelIcon } from '@heroicons/react/24/outline';

interface ProductGridProps {
  products: Product[];
  loading: boolean;
  onAddToCart: (product: Product, quantity: number) => void;
  userPersona: UserPersona;
}

export const ProductGrid: React.FC<ProductGridProps> = ({ 
  products, 
  loading, 
  onAddToCart,
  userPersona 
}) => {
  const [sortBy, setSortBy] = useState<'relevance' | 'price_low' | 'price_high'>('relevance');

  const sortedProducts = [...products].sort((a, b) => {
    switch (sortBy) {
      case 'price_low':
        return a.price - b.price;
      case 'price_high':
        return b.price - a.price;
      default:
        return (b.personalization_score || 0) - (a.personalization_score || 0);
    }
  });

  if (loading) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-8">
        <div className="flex items-center justify-center">
          <div className="animate-spin h-8 w-8 border-4 border-primary-600 border-t-transparent rounded-full" />
          <span className="ml-3 text-gray-600">Searching with AI assistance...</span>
        </div>
      </div>
    );
  }

  if (products.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-12 text-center">
        <div className="max-w-sm mx-auto">
          <FunnelIcon className="h-12 w-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No products found</h3>
          <p className="text-gray-600">Try searching for something else or adjust your filters.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200 flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold text-gray-900">
            Search Results
          </h2>
          <p className="text-sm text-gray-600 mt-1">
            {products.length} products found
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <label className="text-sm text-gray-600">Sort by:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as any)}
            className="text-sm border border-gray-300 rounded-md px-3 py-1 focus:outline-none focus:ring-2 focus:ring-primary-500"
          >
            <option value="relevance">Relevance</option>
            <option value="price_low">Price: Low to High</option>
            <option value="price_high">Price: High to Low</option>
          </select>
        </div>
      </div>

      {/* Product Grid */}
      <div className="p-6">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          <AnimatePresence>
            {sortedProducts.map((product, index) => (
              <motion.div
                key={product.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.9 }}
                transition={{ delay: index * 0.05 }}
              >
                <ProductCard
                  product={product}
                  onAddToCart={onAddToCart}
                  userPersona={userPersona}
                />
              </motion.div>
            ))}
          </AnimatePresence>
        </div>
      </div>
    </div>
  );
};