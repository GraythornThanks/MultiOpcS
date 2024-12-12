'use client';

import { getServers } from '@/lib/api';
import { DataTable } from './data-table';
import { columns } from './columns';
import { Button } from '@/components/ui/button';
import { Plus } from 'lucide-react';
import Link from 'next/link';
import { useEffect, useState } from 'react';
import { OPCUAServer } from '@/types';
import { wsManager } from '@/lib/websocket';

export default function ServersPage() {
    const [servers, setServers] = useState<OPCUAServer[]>([]);

    useEffect(() => {
        // 初始加载
        getServers().then(setServers);

        // 订阅 WebSocket 更新
        const unsubscribe = wsManager?.subscribe((data) => {
            if (data.type === 'initial_status') {
                // 更新所有服务器状态
                const updates = Array.isArray(data.data) ? data.data : [data.data];
                setServers(prev => prev.map(server => {
                    const update = updates.find(u => u.id === server.id);
                    if (update) {
                        return {
                            ...server,
                            status: update.status as any,
                            last_started: update.last_started,
                        };
                    }
                    return server;
                }));
            } else if (data.type === 'server_status') {
                // 更新单个服务器状态
                const update = data.data as { id: number; status: string; last_started: string | null };
                setServers(prev => prev.map(server => 
                    server.id === update.id
                        ? { ...server, status: update.status as any, last_started: update.last_started }
                        : server
                ));
            }
        });

        return () => {
            unsubscribe?.();
        };
    }, []);

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

            <DataTable columns={columns} data={servers} />
        </div>
    );
} 