'use client';

import { Row } from '@tanstack/react-table';
import { Button } from '@/components/ui/button';
import { MoreHorizontal, Pencil, Trash2 } from 'lucide-react';
import {
    DropdownMenu,
    DropdownMenuContent,
    DropdownMenuItem,
    DropdownMenuLabel,
    DropdownMenuSeparator,
    DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import Link from 'next/link';
import { deleteNode } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';

interface DataTableRowActionsProps<TData> {
    row: Row<TData>;
}

export function DataTableRowActions<TData>({
    row,
}: DataTableRowActionsProps<TData>) {
    const router = useRouter();
    const node = row.original as any;

    const handleDelete = async () => {
        if (confirm('确定要删除这个节点吗？')) {
            try {
                await deleteNode(node.id);
                toast.success('节点删除成功');
                router.refresh();
            } catch (error) {
                console.error('删除节点失败:', error);
                toast.error('删除节点失败');
            }
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
                    <Link href={`/nodes/${node.id}/edit`} className="flex items-center">
                        <Pencil className="mr-2 h-4 w-4" />
                        编辑
                    </Link>
                </DropdownMenuItem>
                <DropdownMenuSeparator />
                <DropdownMenuItem onClick={handleDelete} className="text-red-600">
                    <Trash2 className="mr-2 h-4 w-4" />
                    删除
                </DropdownMenuItem>
            </DropdownMenuContent>
        </DropdownMenu>
    );
} 