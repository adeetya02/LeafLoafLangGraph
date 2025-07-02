import React, { useState } from 'react';
import { Product, UserPersona } from '../types';
import { 
  PlusIcon, 
  MinusIcon, 
  ShoppingCartIcon,
  SparklesIcon,
  ClockIcon,
  ArrowPathIcon
} from '@heroicons/react/24/outline';

interface ProductCardProps {
  product: Product;
  onAddToCart: (product: Product, quantity: number) => void;
  userPersona: UserPersona;
}

export const ProductCard: React.FC<ProductCardProps> = ({ 
  product, 
  onAddToCart
}) => {
  const [quantity, setQuantity] = useState(product.typical_quantity || 1);
  const [isAdding, setIsAdding] = useState(false);

  const handleAddToCart = async () => {
    setIsAdding(true);
    await onAddToCart(product, quantity);
    setIsAdding(false);
  };

  const getBadges = () => {
    const badges = [];
    
    if (product.personalization_score && product.personalization_score > 0.8) {
      badges.push({ 
        label: 'For You', 
        icon: SparklesIcon, 
        color: 'bg-purple-100 text-purple-800 border-purple-200' 
      });
    }
    
    if (product.is_usual) {
      badges.push({ 
        label: 'My Usual', 
        icon: ClockIcon, 
        color: 'bg-blue-100 text-blue-800 border-blue-200' 
      });
    }
    
    if (product.needs_reorder) {
      badges.push({ 
        label: 'Time to Reorder', 
        icon: ArrowPathIcon, 
        color: 'bg-orange-100 text-orange-800 border-orange-200' 
      });
    }
    
    return badges;
  };

  const badges = getBadges();

  return (
    <div className="bg-white rounded-lg border border-gray-200 hover:shadow-lg transition-shadow duration-200 overflow-hidden">
      {/* Badges */}
      {badges.length > 0 && (
        <div className="px-4 pt-3 flex flex-wrap gap-2">
          {badges.map((badge, index) => (
            <span
              key={index}
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${badge.color}`}
            >
              <badge.icon className="w-3 h-3 mr-1" />
              {badge.label}
            </span>
          ))}
        </div>
      )}

      {/* Product Image */}
      <div className="p-4">
        <div className="w-full h-48 bg-gray-100 rounded-lg flex items-center justify-center">
          {product.image_url ? (
            <img
              src={product.image_url}
              alt={product.name}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <div className="text-gray-400">
              <ShoppingCartIcon className="w-16 h-16" />
            </div>
          )}
        </div>
      </div>

      {/* Product Info */}
      <div className="px-4 pb-4 space-y-3">
        <div>
          <h3 className="text-lg font-semibold text-gray-900 line-clamp-2">
            {product.name}
          </h3>
          {product.brand && (
            <p className="text-sm text-gray-600">{product.brand}</p>
          )}
          {product.size && (
            <p className="text-sm text-gray-500">{product.size}</p>
          )}
        </div>

        {/* Price */}
        <div className="flex items-baseline">
          <span className="text-2xl font-bold text-gray-900">
            ${product.price.toFixed(2)}
          </span>
          {product.typical_quantity && product.typical_quantity > 1 && (
            <span className="ml-2 text-sm text-gray-500">
              Usually buy: {product.typical_quantity}
            </span>
          )}
        </div>

        {/* Quantity Selector */}
        <div className="flex items-center space-x-3">
          <div className="flex items-center border border-gray-300 rounded-lg">
            <button
              onClick={() => setQuantity(Math.max(1, quantity - 1))}
              className="p-2 hover:bg-gray-100 transition-colors"
              disabled={quantity <= 1}
            >
              <MinusIcon className="w-4 h-4 text-gray-600" />
            </button>
            <input
              type="number"
              value={quantity}
              onChange={(e) => setQuantity(Math.max(1, parseInt(e.target.value) || 1))}
              className="w-16 text-center border-x border-gray-300 py-2 focus:outline-none"
              min="1"
              max="99"
            />
            <button
              onClick={() => setQuantity(Math.min(99, quantity + 1))}
              className="p-2 hover:bg-gray-100 transition-colors"
              disabled={quantity >= 99}
            >
              <PlusIcon className="w-4 h-4 text-gray-600" />
            </button>
          </div>

          {/* Add to Cart Button */}
          <button
            onClick={handleAddToCart}
            disabled={isAdding}
            className="flex-1 bg-primary-600 text-white py-2 px-4 rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center space-x-2"
          >
            {isAdding ? (
              <div className="animate-spin h-5 w-5 border-2 border-white border-t-transparent rounded-full" />
            ) : (
              <>
                <ShoppingCartIcon className="w-5 h-5" />
                <span>Add to Cart</span>
              </>
            )}
          </button>
        </div>

        {/* Complementary Products */}
        {product.complementary_products && product.complementary_products.length > 0 && (
          <div className="pt-3 border-t border-gray-200">
            <p className="text-xs text-gray-600">
              Often bought with: {product.complementary_products.join(', ')}
            </p>
          </div>
        )}
      </div>
    </div>
  );
};