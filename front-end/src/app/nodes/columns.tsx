'use client';

import { ColumnDef, Row } from '@tanstack/react-table';
import { Node } from '@/types';
import { Button } from '@/components/ui/button';
import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';
import { deleteNode } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { Badge } from '@/components/ui/badge';
import { Checkbox } from '@/components/ui/checkbox';

export const columns: ColumnDef<Node>[] = [
    {
        id: 'select',
        header: ({ table }) => (
            <Checkbox
                checked={
                    table.getIsAllPageRowsSelected() ||
                    (table.getIsSomePageRowsSelected() && 'indeterminate')
                }
                onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
                aria-label="全选"
            />
        ),
        cell: ({ row }) => (
            <Checkbox
                checked={row.getIsSelected()}
                onCheckedChange={(value) => row.toggleSelected(!!value)}
                aria-label="选择节点"
            />
        ),
        enableSorting: false,
        enableHiding: false,
    },
    {
        accessorKey: 'name',
        header: '节点名称',
    },
    {
        accessorKey: 'node_id',
        header: '节点ID',
    },
    {
        accessorKey: 'data_type',
        header: '数据类型',
    },
    {
        accessorKey: 'access_level',
        header: '访问级别',
        cell: ({ row }: { row: Row<Node> }) => {
            const access = row.getValue('access_level') as string;
            return (
                <Badge variant="outline">
                    {access === 'read' ? '只读' : access === 'write' ? '只写' : '读写'}
                </Badge>
            );
        },
    },
    {
        id: 'actions',
        cell: ({ row }: { row: Row<Node> }) => {
            const node = row.original;
            const router = useRouter();

            const handleDelete = async () => {
                if (confirm('确定要删除这个节点吗？')) {
                    await deleteNode(node.id);
                    router.refresh();
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
                            <Link href={`/nodes/${node.id}/edit`}>
                                <Pencil className="mr-2 h-4 w-4" />
                                编辑
                            </Link>
                        </DropdownMenuItem>
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