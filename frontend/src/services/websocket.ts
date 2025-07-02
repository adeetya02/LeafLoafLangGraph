import { AgentFlowEvent } from '../types';

export class WebSocketService {
  private ws: WebSocket | null = null;
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;
  private listeners: Set<(event: AgentFlowEvent) => void> = new Set();
  private url: string;

  constructor() {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = (import.meta as any).env?.VITE_WS_URL || `${wsProtocol}//${window.location.host}`;
    this.url = `${wsHost}/ws/agent-flow`;
  }

  connect() {
    try {
      console.log('[WebSocket] Connecting to:', this.url);
      this.ws = new WebSocket(this.url);

      this.ws.onopen = () => {
        console.log('[WebSocket] Connected');
        this.reconnectAttempts = 0;
      };

      this.ws.onmessage = (event) => {
        try {
          const flowEvent: AgentFlowEvent = JSON.parse(event.data);
          console.log('[WebSocket] Received event:', flowEvent);
          
          // Notify all listeners
          this.listeners.forEach(listener => listener(flowEvent));
        } catch (error) {
          console.error('[WebSocket] Error parsing message:', error);
        }
      };

      this.ws.onerror = (error) => {
        console.error('[WebSocket] Error:', error);
      };

      this.ws.onclose = () => {
        console.log('[WebSocket] Disconnected');
        this.reconnect();
      };
    } catch (error) {
      console.error('[WebSocket] Connection error:', error);
      this.reconnect();
    }
  }

  private reconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      console.log(`[WebSocket] Reconnecting... (attempt ${this.reconnectAttempts})`);
      
      setTimeout(() => {
        this.connect();
      }, this.reconnectDelay * this.reconnectAttempts);
    } else {
      console.error('[WebSocket] Max reconnection attempts reached');
    }
  }

  subscribe(listener: (event: AgentFlowEvent) => void) {
    this.listeners.add(listener);
    
    // Return unsubscribe function
    return () => {
      this.listeners.delete(listener);
    };
  }

  disconnect() {
    if (this.ws) {
      this.ws.close();
      this.ws = null;
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN;
  }
}

// Create singleton instance
export const wsService = new WebSocketService();