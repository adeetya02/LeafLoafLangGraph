import axios from 'axios';
import { 
  SearchRequest, 
  SearchResponse,
  Product,
  CartItem 
} from '../types';

const API_BASE = (import.meta as any).env?.VITE_API_URL || 'http://localhost:8000';

// Create axios instance with interceptors
const api = axios.create({
  baseURL: API_BASE,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Request interceptor for logging
api.interceptors.request.use(
  (config) => {
    console.log(`[API] ${config.method?.toUpperCase()} ${config.url}`, config.data);
    return config;
  },
  (error) => {
    console.error('[API] Request error:', error);
    return Promise.reject(error);
  }
);

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    console.log(`[API] Response from ${response.config.url}:`, response.data);
    return response;
  },
  (error) => {
    console.error('[API] Response error:', error);
    return Promise.reject(error);
  }
);

// API methods
export const searchAPI = {
  search: async (request: SearchRequest): Promise<SearchResponse> => {
    const response = await api.post<SearchResponse>('/api/v1/search', request);
    return response.data;
  },
};

export const cartAPI = {
  add: async (product: Product, quantity: number, userId: string = 'demo_user'): Promise<any> => {
    const response = await api.post('/api/v1/order', {
      query: `add ${quantity} ${product.name} to cart`,
      user_id: userId,
      product_id: product.id,
    });
    return response.data;
  },

  update: async (productId: string, quantity: number, userId: string = 'demo_user'): Promise<any> => {
    const response = await api.post('/api/v1/order', {
      query: `update cart quantity to ${quantity}`,
      user_id: userId,
      product_id: productId,
    });
    return response.data;
  },

  remove: async (productId: string, userId: string = 'demo_user'): Promise<any> => {
    const response = await api.post('/api/v1/order', {
      query: `remove item from cart`,
      user_id: userId,
      product_id: productId,
    });
    return response.data;
  },

  list: async (userId: string = 'demo_user'): Promise<CartItem[]> => {
    const response = await api.post('/api/v1/order', {
      query: 'show cart',
      user_id: userId,
    });
    return response.data.order?.cart || [];
  },

  confirm: async (userId: string = 'demo_user'): Promise<any> => {
    const response = await api.post('/api/v1/order', {
      query: 'confirm order',
      user_id: userId,
    });
    return response.data;
  },
};

export const metricsAPI = {
  getMetrics: async (userId: string = 'demo_user'): Promise<any> => {
    const response = await api.get('/api/personalization/metrics', {
      params: { user_id: userId },
    });
    return response.data;
  },
};

export default api;