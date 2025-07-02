import { useState, useEffect } from 'react';
import { Toaster } from 'react-hot-toast';
import { Header } from './components/Header';
import { SearchBar } from './components/SearchBar';
import { ProductGrid } from './components/ProductGrid';
import { Cart } from './components/Cart';
import { AgentFlowVisualizer } from './components/AgentFlowVisualizer';
import { TechnicalPanel } from './components/TechnicalPanel';
import { PerformanceMetrics } from './components/PerformanceMetrics';
import { UserPersona, Product, CartItem } from './types';
import { searchAPI, cartAPI } from './services/api';
import toast from 'react-hot-toast';

function App() {
  const [user, setUser] = useState<UserPersona>('demo_user');
  const [products, setProducts] = useState<Product[]>([]);
  const [cart, setCart] = useState<CartItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [showTechnical, setShowTechnical] = useState(true);
  const [lastSearchMetadata, setLastSearchMetadata] = useState<any>(null);
  const [sessionId] = useState(`session_${Date.now()}`);

  // Features toggles
  const [features, setFeatures] = useState({
    smart_ranking: true,
    dietary_filter: true,
    budget_aware: true,
    quantity_memory: true,
    my_usual: true,
    reorder_intelligence: true,
  });

  // Load cart on mount
  useEffect(() => {
    loadCart();
  }, [user]);

  const loadCart = async () => {
    try {
      const cartItems = await cartAPI.list(user);
      setCart(cartItems);
    } catch (error) {
      console.error('Failed to load cart:', error);
    }
  };

  const handleSearch = async (query: string) => {
    setLoading(true);
    try {
      const response = await searchAPI.search({
        query,
        user_id: user,
        session_id: sessionId,
        features,
      });
      
      setProducts(response.products);
      setLastSearchMetadata(response.metadata);
      
      if (response.metadata.personalization_applied) {
        toast.success('Personalization applied! 🎯', {
          position: 'top-right',
          duration: 3000,
        });
      }
    } catch (error) {
      console.error('Search failed:', error);
      toast.error('Search failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddToCart = async (product: Product, quantity: number = 1) => {
    try {
      await cartAPI.add(product, quantity, user);
      
      // Update local cart
      setCart(prev => {
        const existing = prev.find(item => item.id === product.id);
        if (existing) {
          return prev.map(item =>
            item.id === product.id
              ? { ...item, quantity: item.quantity + quantity }
              : item
          );
        }
        return [...prev, { ...product, quantity, total_price: product.price * quantity }];
      });
      
      toast.success(`Added ${product.name} to cart! 🛒`, {
        position: 'bottom-center',
        duration: 2000,
      });
    } catch (error) {
      console.error('Failed to add to cart:', error);
      toast.error('Failed to add to cart');
    }
  };

  const handleUpdateQuantity = async (productId: string, quantity: number) => {
    if (quantity === 0) {
      return handleRemoveFromCart(productId);
    }
    
    try {
      await cartAPI.update(productId, quantity, user);
      
      setCart(prev =>
        prev.map(item =>
          item.id === productId
            ? { ...item, quantity, total_price: item.price * quantity }
            : item
        )
      );
    } catch (error) {
      console.error('Failed to update quantity:', error);
      toast.error('Failed to update quantity');
    }
  };

  const handleRemoveFromCart = async (productId: string) => {
    try {
      await cartAPI.remove(productId, user);
      
      setCart(prev => prev.filter(item => item.id !== productId));
      
      toast.success('Removed from cart', {
        position: 'bottom-center',
        duration: 2000,
      });
    } catch (error) {
      console.error('Failed to remove from cart:', error);
      toast.error('Failed to remove from cart');
    }
  };

  const handleCheckout = async () => {
    try {
      await cartAPI.confirm(user);
      setCart([]);
      toast.success('Order confirmed! 🎉', {
        position: 'top-center',
        duration: 4000,
      });
    } catch (error) {
      console.error('Failed to confirm order:', error);
      toast.error('Failed to confirm order');
    }
  };

  const handleFeaturesChange = (newFeatures: Record<string, boolean>) => {
    setFeatures(newFeatures as typeof features);
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Toaster />
      
      <Header 
        user={user} 
        onUserChange={setUser}
        showTechnical={showTechnical}
        onToggleTechnical={() => setShowTechnical(!showTechnical)}
      />
      
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Main Content */}
          <div className="lg:col-span-2 space-y-6">
            <SearchBar 
              onSearch={handleSearch}
              loading={loading}
              features={features}
              onFeaturesChange={handleFeaturesChange}
            />
            
            {lastSearchMetadata && showTechnical && (
              <TechnicalPanel metadata={lastSearchMetadata} />
            )}
            
            <ProductGrid 
              products={products}
              loading={loading}
              onAddToCart={handleAddToCart}
              userPersona={user}
            />
          </div>
          
          {/* Sidebar */}
          <div className="space-y-6">
            <Cart 
              items={cart}
              onUpdateQuantity={handleUpdateQuantity}
              onRemove={handleRemoveFromCart}
              onCheckout={handleCheckout}
            />
            
            {showTechnical && <PerformanceMetrics />}
          </div>
        </div>
      </main>
      
      {/* Agent Flow Visualizer */}
      {showTechnical && <AgentFlowVisualizer />}
    </div>
  );
}

export default App;