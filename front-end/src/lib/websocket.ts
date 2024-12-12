import { OPCUAServer } from "@/types";

type ServerStatusUpdate = {
    type: 'server_status' | 'initial_status';
    data: {
        id: number;
        status: string;
        last_started: string | null;
    }[] | {
        id: number;
        status: string;
        last_started: string | null;
    };
};

type WebSocketCallback = (data: ServerStatusUpdate) => void;

class WebSocketManager {
    private ws: WebSocket | null = null;
    private callbacks: Set<WebSocketCallback> = new Set();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 5;
    private reconnectDelay = 1000;
    private pingInterval: NodeJS.Timeout | null = null;

    constructor() {
        if (typeof window !== 'undefined') {
            this.connect();
        }
    }

    private connect() {
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
        this.ws = new WebSocket(wsUrl);

        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.reconnectAttempts = 0;
            this.startPing();
        };

        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.stopPing();
            this.attemptReconnect();
        };

        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.ws.onmessage = (event) => {
            try {
                if (event.data === 'pong') {
                    return;
                }
                
                const data = JSON.parse(event.data) as ServerStatusUpdate;
                this.notifyCallbacks(data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };
    }

    private startPing() {
        this.pingInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send('ping');
            }
        }, 30000); // 每30秒发送一次ping
    }

    private stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private attemptReconnect() {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts})...`);
            setTimeout(() => this.connect(), this.reconnectDelay * this.reconnectAttempts);
        } else {
            console.log('Max reconnection attempts reached');
        }
    }

    subscribe(callback: WebSocketCallback) {
        this.callbacks.add(callback);
        return () => this.callbacks.delete(callback);
    }

    private notifyCallbacks(data: ServerStatusUpdate) {
        this.callbacks.forEach(callback => callback(data));
    }

    close() {
        this.stopPing();
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
    }
}

// 创建单例实例
export const wsManager = typeof window !== 'undefined' ? new WebSocketManager() : null; 