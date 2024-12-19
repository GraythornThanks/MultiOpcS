import { useEffect, useCallback, useRef, useState } from 'react';
import { getWsManager } from '@/lib/websocket';
import type { ServerStatusUpdate } from '@/types';

export type WebSocketState = 'CONNECTING' | 'OPEN' | 'CLOSING' | 'CLOSED' | 'UNKNOWN';

interface WebSocketOptions {
    onMessage?: (data: ServerStatusUpdate) => void;
    onConnect?: () => void;
    onDisconnect?: () => void;
    onError?: (error: Error) => void;
    autoConnect?: boolean;
    reconnectOnError?: boolean;
}

export const useWebSocket = ({
    onMessage,
    onConnect,
    onDisconnect,
    onError,
    autoConnect = true,
    reconnectOnError = true
}: WebSocketOptions = {}) => {
    const wsRef = useRef(getWsManager());
    const unsubscribeRef = useRef<(() => void) | null>(null);
    const [connectionState, setConnectionState] = useState<WebSocketState>('CLOSED');
    const [error, setError] = useState<Error | null>(null);
    const mountedRef = useRef(true);

    const updateConnectionState = useCallback(() => {
        if (!mountedRef.current) return;
        
        const ws = wsRef.current;
        if (ws) {
            const state = ws.getState();
            setConnectionState(state as WebSocketState);
        }
    }, []);

    const connect = useCallback(() => {
        if (!mountedRef.current) return;

        const ws = wsRef.current;
        if (!ws) {
            setError(new Error('WebSocket实例不可用'));
            return;
        }

        try {
            setError(null);
            ws.initialize();
            
            // 订阅消息
            unsubscribeRef.current = ws.subscribe((data) => {
                if (!mountedRef.current) return;
                
                try {
                    updateConnectionState();
                    onMessage?.(data);
                } catch (error) {
                    if (!mountedRef.current) return;
                    console.error('处理WebSocket消息时发生错误:', error);
                    setError(error as Error);
                    onError?.(error as Error);
                }
            });

            updateConnectionState();
            onConnect?.();
        } catch (error) {
            if (!mountedRef.current) return;
            console.error('WebSocket连接失败:', error);
            setError(error as Error);
            onError?.(error as Error);
        }
    }, [onMessage, onConnect, onError, updateConnectionState]);

    const disconnect = useCallback(() => {
        if (unsubscribeRef.current) {
            unsubscribeRef.current();
            unsubscribeRef.current = null;
            if (mountedRef.current) {
                updateConnectionState();
                onDisconnect?.();
            }
        }
    }, [onDisconnect, updateConnectionState]);

    // 自动重连逻辑
    useEffect(() => {
        let reconnectTimer: NodeJS.Timeout | null = null;
        
        if (connectionState === 'CLOSED' && autoConnect && reconnectOnError && mountedRef.current) {
            reconnectTimer = setTimeout(connect, 3000);
        }

        return () => {
            if (reconnectTimer) {
                clearTimeout(reconnectTimer);
            }
        };
    }, [connectionState, autoConnect, reconnectOnError, connect]);

    // 初始连接
    useEffect(() => {
        mountedRef.current = true;

        if (autoConnect) {
            connect();
        }

        return () => {
            mountedRef.current = false;
            disconnect();
            // 确保清理所有状态
            setConnectionState('CLOSED');
            setError(null);
        };
    }, [autoConnect, connect, disconnect]);

    // 定期更新连接状态
    useEffect(() => {
        const interval = setInterval(() => {
            if (mountedRef.current) {
                updateConnectionState();
            }
        }, 1000);
        
        return () => {
            clearInterval(interval);
        };
    }, [updateConnectionState]);

    return {
        connect,
        disconnect,
        connectionState,
        isConnected: connectionState === 'OPEN',
        error
    };
}; 