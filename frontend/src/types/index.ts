// Product types
export interface Product {
  id: string;
  name: string;
  brand?: string;
  category: string;
  price: number;
  size?: string;
  image_url?: string;
  description?: string;
  typical_quantity?: number;
  personalization_score?: number;
  is_usual?: boolean;
  needs_reorder?: boolean;
  complementary_products?: string[];
}

// Cart types
export interface CartItem extends Product {
  quantity: number;
  total_price: number;
}

// Agent flow types
export interface AgentFlowEvent {
  timestamp: string;
  agent: string;
  action: string;
  details: Record<string, any>;
  latency_ms: number;
}

// Search types
export interface SearchRequest {
  query: string;
  user_id?: string;
  session_id?: string;
  features?: Record<string, boolean>;
}

export interface SearchResponse {
  request_id: string;
  query: string;
  products: Product[];
  metadata: {
    intent: string;
    search_alpha: number;
    total_latency_ms: number;
    agent_latencies: Record<string, number>;
    personalization_applied: boolean;
    session_id: string;
  };
}

// User types
export type UserPersona = 'demo_user' | 'health_conscious' | 'budget_shopper' | 'family_shopper';

export interface UserProfile {
  id: string;
  persona: UserPersona;
  name: string;
  preferences: {
    dietary: string[];
    price_sensitive: boolean;
    typical_quantities: Record<string, number>;
  };
}

// Cart actions
export type CartAction = 'add' | 'update' | 'remove' | 'list' | 'confirm';

export interface CartRequest {
  action: CartAction;
  product_id?: string;
  quantity?: number;
  user_id?: string;
  session_id?: string;
}

export interface CartResponse {
  status: string;
  cart?: CartItem[];
  message?: string;
}

export interface HealthResponse {
  status: string;
  version: string;
}

// Performance metrics
export interface PerformanceMetrics {
  avg_latency_ms: number;
  total_requests: number;
  cache_hit_rate: number;
  personalization_score: number;
  latency_history: number[];
}