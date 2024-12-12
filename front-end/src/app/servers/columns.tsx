'use client';

import { ColumnDef, Row } from '@tanstack/react-table';
import { OPCUAServer } from '@/types';
import { Button } from '@/components/ui/button';
import { MoreHorizontal, Pencil, Trash2, Play, Square, RotateCw } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuTrigger,
    DropdownMenuLabel,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';
import { deleteServer, startServer, stopServer, restartServer } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';

export const columns: ColumnDef<OPCUAServer>[] = [
    {
        accessorKey: 'name',
        header: '名称',
    },
    {
        accessorKey: 'endpoint',
        header: '服务器地址',
        cell: ({ row }: { row: Row<OPCUAServer> }) => {
            const server = row.original;
            return server.endpoint || `opc.tcp://0.0.0.0:${server.port}`;
        },
    },
    {
        accessorKey: 'port',
        header: '端口',
    },
    {
        accessorKey: 'status',
        header: '状态',
        cell: ({ row }: { row: Row<OPCUAServer> }) => {
            const status = row.getValue('status') as string;
            let variant: 'default' | 'success' | 'destructive' | 'secondary' = 'secondary';
            let label = '未知';

            switch (status) {
                case 'running':
                    variant = 'success';
                    label = '运行中';
                    break;
                case 'starting':
                    variant = 'default';
                    label = '启动中';
                    break;
                case 'stopped':
                    variant = 'secondary';
                    label = '已停止';
                    break;
                case 'error':
                    variant = 'destructive';
                    label = '错误';
                    break;
            }

            return <Badge variant={variant}>{label}</Badge>;
        },
    },
    {
        accessorKey: 'nodes',
        header: '节点数',
        cell: ({ row }: { row: Row<OPCUAServer> }) => {
            const nodes = row.getValue('nodes') as any[];
            return nodes.length;
        },
    },
    {
        id: 'actions',
        cell: ({ row }) => {
            const server = row.original;
            const router = useRouter();

            const handleDelete = async () => {
                if (confirm('确定要删除这个服务器吗？')) {
                    await deleteServer(server.id);
                    router.refresh();
                }
            };

            const handleStart = async () => {
                try {
                    await startServer(server.id);
                    router.refresh();
                } catch (error) {
                    console.error('启动服务器失败:', error);
                }
            };

            const handleStop = async () => {
                try {
                    await stopServer(server.id);
                    router.refresh();
                } catch (error) {
                    console.error('停止服务器失败:', error);
                }
            };

            const handleRestart = async () => {
                try {
                    await restartServer(server.id);
                    router.refresh();
                } catch (error) {
                    console.error('重启服务器失败:', error);
                }
            };

            return (
                <DropdownMenu>
                    <DropdownMenuTrigger asChild>
                        <Button variant="ghost" className="h-8 w-8 p-0">
                            <span className="sr-only">打开菜单</span>
                            <MoreHorizontal className="h-4 w-4" />
                        </Button>
                    </DropdownMenuTrigger>
                    <DropdownMenuContent align="end">
                        <DropdownMenuLabel>操作</DropdownMenuLabel>
                        <DropdownMenuItem asChild>
                            <Link href={`/servers/${server.id}/edit`}>
                                <Pencil className="mr-2 h-4 w-4" />
                                编辑
                            </Link>
                        </DropdownMenuItem>
                        {server.status === 'stopped' && (
                            <DropdownMenuItem onClick={handleStart}>
                                <Play className="mr-2 h-4 w-4" />
                                启动
                            </DropdownMenuItem>
                        )}
                        {server.status === 'running' && (
                            <>
                                <DropdownMenuItem onClick={handleStop}>
                                    <Square className="mr-2 h-4 w-4" />
                                    停止
                                </DropdownMenuItem>
                                <DropdownMenuItem onClick={handleRestart}>
                                    <RotateCw className="mr-2 h-4 w-4" />
                                    重启
                                </DropdownMenuItem>
                            </>
                        )}
                        <DropdownMenuItem onClick={handleDelete}>
                            <Trash2 className="mr-2 h-4 w-4" />
                            删除
                        </DropdownMenuItem>
                    </DropdownMenuContent>
                </DropdownMenu>
            );
        },
    },
]; 