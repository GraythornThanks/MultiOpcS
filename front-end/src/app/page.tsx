'use client';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Server, Activity, GitBranch } from 'lucide-react';
import { useEffect, useState } from 'react';

interface DashboardStats {
    total_servers: number;
    running_servers: number;
    total_nodes: number;
}

export default function DashboardPage() {
    const [stats, setStats] = useState<DashboardStats>({
        total_servers: 0,
        running_servers: 0,
        total_nodes: 0,
    });

    useEffect(() => {
        const fetchStats = async () => {
            try {
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/dashboard`);
                const data = await response.json();
                setStats(data);
            } catch (error) {
                console.error('获取仪表盘数据失败:', error);
            }
        };

        fetchStats();
        // 每30秒刷新一次数据
        const interval = setInterval(fetchStats, 30000);
        return () => clearInterval(interval);
    }, []);

    return (
        <div className="space-y-6">
            <h1 className="text-3xl font-bold tracking-tight">仪表盘</h1>

            <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">服务器总数</CardTitle>
                        <Server className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.total_servers}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">运行中的服务器</CardTitle>
                        <Activity className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.running_servers}</div>
                    </CardContent>
                </Card>

                <Card>
                    <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                        <CardTitle className="text-sm font-medium">节点总数</CardTitle>
                        <GitBranch className="h-4 w-4 text-muted-foreground" />
                    </CardHeader>
                    <CardContent>
                        <div className="text-2xl font-bold">{stats.total_nodes}</div>
                    </CardContent>
                </Card>
            </div>
        </div>
    );
}
