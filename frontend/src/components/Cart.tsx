import React from 'react';
import { CartItem } from '../types';
import { 
  ShoppingCartIcon, 
  TrashIcon, 
  PlusIcon, 
  MinusIcon,
  CheckCircleIcon 
} from '@heroicons/react/24/outline';
import { motion, AnimatePresence } from 'framer-motion';

interface CartProps {
  items: CartItem[];
  onUpdateQuantity: (productId: string, quantity: number) => void;
  onRemove: (productId: string) => void;
  onCheckout: () => void;
}

export const Cart: React.FC<CartProps> = ({ 
  items, 
  onUpdateQuantity, 
  onRemove, 
  onCheckout 
}) => {
  const subtotal = items.reduce((sum, item) => sum + item.total_price, 0);
  const tax = subtotal * 0.08; // 8% tax
  const total = subtotal + tax;

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200">
      {/* Header */}
      <div className="px-6 py-4 border-b border-gray-200">
        <div className="flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <ShoppingCartIcon className="h-6 w-6 text-gray-700" />
            <h2 className="text-lg font-semibold text-gray-900">Shopping Cart</h2>
          </div>
          <span className="text-sm text-gray-600">
            {items.length} {items.length === 1 ? 'item' : 'items'}
          </span>
        </div>
      </div>

      {/* Cart Items */}
      <div className="max-h-96 overflow-y-auto">
        <AnimatePresence>
          {items.length === 0 ? (
            <div className="p-8 text-center">
              <ShoppingCartIcon className="h-12 w-12 text-gray-300 mx-auto mb-3" />
              <p className="text-gray-500">Your cart is empty</p>
              <p className="text-sm text-gray-400 mt-1">Start shopping to add items</p>
            </div>
          ) : (
            items.map((item) => (
              <motion.div
                key={item.id}
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: 20 }}
                className="px-6 py-4 border-b border-gray-100 hover:bg-gray-50 transition-colors"
              >
                <div className="flex items-start space-x-4">
                  {/* Product Image */}
                  <div className="w-16 h-16 bg-gray-100 rounded-lg flex-shrink-0 flex items-center justify-center">
                    <ShoppingCartIcon className="w-8 h-8 text-gray-400" />
                  </div>

                  {/* Product Details */}
                  <div className="flex-1 min-w-0">
                    <h4 className="text-sm font-medium text-gray-900 truncate">
                      {item.name}
                    </h4>
                    {item.brand && (
                      <p className="text-xs text-gray-500">{item.brand}</p>
                    )}
                    <p className="text-sm text-gray-600 mt-1">
                      ${item.price.toFixed(2)} each
                    </p>

                    {/* Quantity Controls */}
                    <div className="flex items-center space-x-2 mt-2">
                      <div className="flex items-center border border-gray-300 rounded">
                        <button
                          onClick={() => onUpdateQuantity(item.id, item.quantity - 1)}
                          className="p-1 hover:bg-gray-100 transition-colors"
                          disabled={item.quantity <= 1}
                        >
                          <MinusIcon className="w-3 h-3 text-gray-600" />
                        </button>
                        <span className="px-3 py-1 text-sm font-medium">
                          {item.quantity}
                        </span>
                        <button
                          onClick={() => onUpdateQuantity(item.id, item.quantity + 1)}
                          className="p-1 hover:bg-gray-100 transition-colors"
                          disabled={item.quantity >= 99}
                        >
                          <PlusIcon className="w-3 h-3 text-gray-600" />
                        </button>
                      </div>
                      
                      <button
                        onClick={() => onRemove(item.id)}
                        className="p-1 text-red-600 hover:text-red-700 transition-colors"
                      >
                        <TrashIcon className="w-4 h-4" />
                      </button>

                      {item.typical_quantity && item.typical_quantity !== item.quantity && (
                        <span className="text-xs text-gray-500 ml-2">
                          Usually: {item.typical_quantity}
                        </span>
                      )}
                    </div>
                  </div>

                  {/* Price */}
                  <div className="text-right">
                    <p className="text-sm font-semibold text-gray-900">
                      ${item.total_price.toFixed(2)}
                    </p>
                  </div>
                </div>
              </motion.div>
            ))
          )}
        </AnimatePresence>
      </div>

      {/* Summary */}
      {items.length > 0 && (
        <div className="px-6 py-4 space-y-3">
          <div className="space-y-2 text-sm">
            <div className="flex justify-between">
              <span className="text-gray-600">Subtotal</span>
              <span className="font-medium">${subtotal.toFixed(2)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-600">Tax</span>
              <span className="font-medium">${tax.toFixed(2)}</span>
            </div>
            <div className="pt-2 border-t border-gray-200">
              <div className="flex justify-between text-base font-semibold">
                <span>Total</span>
                <span className="text-primary-600">${total.toFixed(2)}</span>
              </div>
            </div>
          </div>

          {/* Checkout Button */}
          <button
            onClick={onCheckout}
            className="w-full bg-primary-600 text-white py-3 px-4 rounded-lg hover:bg-primary-700 focus:outline-none focus:ring-2 focus:ring-primary-500 transition-colors flex items-center justify-center space-x-2 font-medium"
          >
            <CheckCircleIcon className="w-5 h-5" />
            <span>Confirm Order</span>
          </button>

          {/* Graphiti Note */}
          <p className="text-xs text-center text-gray-500">
            🧠 Your preferences are being learned by Graphiti
          </p>
        </div>
      )}
    </div>
  );
};