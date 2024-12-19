import { ServerStatusUpdate, WebSocketError } from "@/types";

type WebSocketCallback = (data: ServerStatusUpdate) => void;
type ErrorCallback = (error: WebSocketError) => void;
type StateCallback = (state: string) => void;

class WebSocketManager {
    private ws: WebSocket | null = null;
    private callbacks: Set<WebSocketCallback> = new Set();
    private errorCallbacks: Set<ErrorCallback> = new Set();
    private stateCallbacks: Set<StateCallback> = new Set();
    private reconnectAttempts = 0;
    private maxReconnectAttempts = 10;
    private reconnectDelay = 1000;
    private pingInterval: NodeJS.Timeout | null = null;
    private retryTimeout: NodeJS.Timeout | null = null;
    private lastPongTime: number = 0;
    private isReconnecting = false;
    private autoReconnect = true;

    constructor() {
        if (typeof window !== 'undefined') {
            this.connect();
        }
    }

    private connect() {
        if (this.isReconnecting || this.ws?.readyState === WebSocket.OPEN) return;
        
        const wsUrl = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000/ws';
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupEventHandlers();
            this.updateState('CONNECTING');
        } catch (error) {
            console.error('WebSocket connection error:', error);
            this.handleError({
                code: 1006,
                reason: 'Connection failed'
            });
            this.attemptReconnect();
        }
    }

    private setupEventHandlers() {
        if (!this.ws) return;

        this.ws.onopen = this.handleOpen.bind(this);
        this.ws.onclose = this.handleClose.bind(this);
        this.ws.onerror = this.handleError.bind(this);
        this.ws.onmessage = this.handleMessage.bind(this);
    }

    private handleOpen() {
        console.log('WebSocket connected');
        this.isReconnecting = false;
        this.reconnectAttempts = 0;
        this.lastPongTime = Date.now();
        this.startPing();
        this.updateState('OPEN');
        
        // 连接成功后立即请求初始状态
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'get_initial_status' }));
        }
    }

    private handleClose(event: CloseEvent) {
        console.log('WebSocket disconnected:', event.code, event.reason);
        this.stopPing();
        this.clearRetryTimeout();
        this.updateState('CLOSED');
        
        if (this.autoReconnect && !this.isReconnecting && event.code !== 1000) {
            this.attemptReconnect();
        }
    }

    private handleError(event: Event | WebSocketError) {
        const error = event instanceof Event 
            ? { code: 1006, reason: 'Unknown error' }
            : event;
            
        console.error('WebSocket error:', error);
        this.errorCallbacks.forEach(callback => callback(error));
        this.updateState('ERROR');
        
        if (error.code === 1006 && this.autoReconnect) {
            this.attemptReconnect();
        }
    }

    private handleMessage(event: MessageEvent) {
        try {
            if (event.data === 'pong') {
                this.lastPongTime = Date.now();
                return;
            }
            
            const data = JSON.parse(event.data) as ServerStatusUpdate;
            this.notifyCallbacks(data);
        } catch (error) {
            console.error('Error parsing WebSocket message:', error);
            this.handleError({
                code: 1007,
                reason: 'Invalid message format'
            });
            this.retryHandler();
        }
    }

    private startPing() {
        this.stopPing();
        this.pingInterval = setInterval(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                const now = Date.now();
                if (now - this.lastPongTime > 20000) { // 20秒没有pong就重连
                    console.log('No pong received, reconnecting...');
                    this.reconnect();
                    return;
                }
                
                try {
                    this.ws.send('ping');
                } catch (error) {
                    console.error('Error sending ping:', error);
                    this.reconnect();
                }
            } else {
                this.reconnect();
            }
        }, 15000); // 每15秒ping一次
    }

    private stopPing() {
        if (this.pingInterval) {
            clearInterval(this.pingInterval);
            this.pingInterval = null;
        }
    }

    private clearRetryTimeout() {
        if (this.retryTimeout) {
            clearTimeout(this.retryTimeout);
            this.retryTimeout = null;
        }
    }

    private reconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        this.attemptReconnect();
    }

    private attemptReconnect() {
        if (this.isReconnecting || !this.autoReconnect) return;
        
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.isReconnecting = true;
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(1.5, this.reconnectAttempts - 1), 30000); // 最大30秒
            console.log(`Attempting to reconnect (${this.reconnectAttempts}/${this.maxReconnectAttempts}) in ${delay}ms...`);
            
            this.updateState('RECONNECTING');
            this.retryTimeout = setTimeout(() => {
                this.connect();
            }, delay);
        } else {
            console.log('Max reconnection attempts reached');
            this.handleError({
                code: 1000,
                reason: 'Max reconnection attempts reached'
            });
            this.autoReconnect = false; // 停止自动重连
        }
    }

    private retryHandler() {
        this.clearRetryTimeout();
        this.retryTimeout = setTimeout(() => {
            if (this.ws?.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({ type: 'get_initial_status' }));
            }
        }, 1000);
    }

    private updateState(state: string) {
        this.stateCallbacks.forEach(callback => {
            try {
                callback(state);
            } catch (error) {
                console.error('Error in state callback:', error);
            }
        });
    }

    subscribe(callback: WebSocketCallback) {
        this.callbacks.add(callback);
        return () => this.callbacks.delete(callback);
    }

    onError(callback: ErrorCallback) {
        this.errorCallbacks.add(callback);
        return () => this.errorCallbacks.delete(callback);
    }

    onStateChange(callback: StateCallback) {
        this.stateCallbacks.add(callback);
        return () => this.stateCallbacks.delete(callback);
    }

    private notifyCallbacks(data: ServerStatusUpdate) {
        this.callbacks.forEach(callback => {
            try {
                callback(data);
            } catch (error) {
                console.error('Error in callback:', error);
            }
        });
    }

    getState(): string {
        if (!this.ws) return 'CLOSED';
        switch (this.ws.readyState) {
            case WebSocket.CONNECTING:
                return 'CONNECTING';
            case WebSocket.OPEN:
                return 'OPEN';
            case WebSocket.CLOSING:
                return 'CLOSING';
            case WebSocket.CLOSED:
                return 'CLOSED';
            default:
                return 'UNKNOWN';
        }
    }

    close() {
        this.autoReconnect = false; // 禁用自动重连
        this.isReconnecting = false;
        this.stopPing();
        this.clearRetryTimeout();
        if (this.ws) {
            this.ws.close(1000);
            this.ws = null;
        }
    }
}

// 创建单例实例
export const wsManager = typeof window !== 'undefined' ? new WebSocketManager() : null; 