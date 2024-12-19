'use client';

import { getServers } from '@/lib/api';
import { DataTable } from './data-table';
import { columns } from './columns';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState, useCallback } from 'react';
import { OPCUAServer, ServerStatusUpdate, WebSocketError } from '@/types';
import { wsManager } from '@/lib/websocket';
import { toast } from 'sonner';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { AlertCircle } from 'lucide-react';

export default function ServersPage() {
    const [servers, setServers] = useState<OPCUAServer[]>([]);
    const [connectionState, setConnectionState] = useState<string>('UNKNOWN');
    const [error, setError] = useState<string | null>(null);

    const handleWebSocketMessage = useCallback((data: ServerStatusUpdate) => {
        try {
            if (data.type === 'initial_status') {
                // 更新所有服务器状态
                const updates = Array.isArray(data.data) ? data.data : [data.data];
                setServers(prev => prev.map(server => {
                    const update = updates.find(u => u.id === server.id);
                    if (update) {
                        return {
                            ...server,
                            status: update.status,
                            last_started: update.last_started,
                        };
                    }
                    return server;
                }));
            } else if (data.type === 'server_status') {
                // 更新单个服务器状态
                const update = Array.isArray(data.data) ? data.data[0] : data.data;
                setServers(prev => prev.map(server => 
                    server.id === update.id
                        ? { ...server, status: update.status, last_started: update.last_started }
                        : server
                ));
            }
        } catch (err) {
            const message = err instanceof Error ? err.message : '处理WebSocket消息时发生错误';
            console.error(message, err);
            toast.error(message);
        }
    }, []);

    const handleWebSocketError = useCallback((error: WebSocketError) => {
        const message = `WebSocket错误: ${error.reason} (代码: ${error.code})`;
        setError(message);
        toast.error(message);
    }, []);

    useEffect(() => {
        // 初始加载
        getServers().then(setServers).catch(err => {
            const message = err instanceof Error ? err.message : '加载服务器列表失败';
            toast.error(message);
        });

        // 订阅 WebSocket 更新
        const unsubscribe = wsManager?.subscribe(handleWebSocketMessage);
        const unsubscribeError = wsManager?.onError(handleWebSocketError);

        // 更新连接状态
        const interval = setInterval(() => {
            if (wsManager) {
                const state = wsManager.getState();
                setConnectionState(state);
                if (state === 'OPEN') {
                    setError(null);
                }
            }
        }, 1000);

        return () => {
            unsubscribe?.();
            unsubscribeError?.();
            clearInterval(interval);
        };
    }, [handleWebSocketMessage, handleWebSocketError]);

    return (
        <div className="space-y-6">
            <div className="flex justify-between items-center">
                <h1 className="text-3xl font-bold tracking-tight">服务器管理</h1>
                <Button asChild>
                    <Link href="/servers/new">
                        <Plus className="mr-2 h-4 w-4" />
                        添加服务器
                    </Link>
                </Button>
            </div>

            {connectionState !== 'OPEN' && (
                <Alert variant="warning">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>
                        WebSocket连接状态: {connectionState}
                    </AlertDescription>
                </Alert>
            )}

            {error && (
                <Alert variant="destructive">
                    <AlertCircle className="h-4 w-4" />
                    <AlertDescription>{error}</AlertDescription>
                </Alert>
            )}

            <DataTable columns={columns} data={servers} />
        </div>
    );
} 