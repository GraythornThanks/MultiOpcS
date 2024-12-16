'use client';

import { ColumnDef } from '@tanstack/react-table';
import { Node } from '@/types';
import { Checkbox } from '@/components/ui/checkbox';
import { DataTableColumnHeader } from './data-table-column-header';
import { DataTableRowActions } from './data-table-row-actions';
import { Badge } from '@/components/ui/badge';
import { format } from 'date-fns';

export const columns: ColumnDef<Node>[] = [
    {
        id: 'select',
        header: ({ table }) => (
            <Checkbox
                checked={table.getIsAllPageRowsSelected()}
                onCheckedChange={(value) => table.toggleAllPageRowsSelected(!!value)}
                aria-label="全选"
            />
        ),
        cell: ({ row }) => (
            <Checkbox
                checked={row.getIsSelected()}
                onCheckedChange={(value) => row.toggleSelected(!!value)}
                aria-label="选择行"
            />
        ),
        enableSorting: false,
        enableHiding: false,
    },
    {
        accessorKey: 'name',
        header: ({ column }) => (
            <DataTableColumnHeader column={column} title="节点名称" />
        ),
    },
    {
        accessorKey: 'node_id',
        header: ({ column }) => (
            <DataTableColumnHeader column={column} title="节点ID" />
        ),
    },
    {
        accessorKey: 'data_type',
        header: ({ column }) => (
            <DataTableColumnHeader column={column} title="数据类型" />
        ),
    },
    {
        accessorKey: 'access_level',
        header: ({ column }) => (
            <DataTableColumnHeader column={column} title="访问级别" />
        ),
        cell: ({ row }) => {
            const level = row.getValue('access_level') as string;
            const levelMap: { [key: string]: { label: string; variant: 'default' | 'secondary' | 'destructive' } } = {
                READ: { label: '只读', variant: 'secondary' },
                WRITE: { label: '只写', variant: 'destructive' },
                READWRITE: { label: '读写', variant: 'default' },
            };
            const { label, variant } = levelMap[level] || { label: level, variant: 'default' };
            return <Badge variant={variant}>{label}</Badge>;
        },
    },
    {
        accessorKey: 'value_change_type',
        header: ({ column }) => (
            <DataTableColumnHeader column={column} title="值变化类型" />
        ),
        cell: ({ row }) => {
            const type = (row.getValue('value_change_type') as string)?.toLowerCase();
            const typeMap: { [key: string]: string } = {
                none: '不自动变化',
                linear: '线性变化',
                discrete: '离散值变化',
                random: '随机变化',
                conditional: '条件变化',
            };
            return typeMap[type] || type;
        },
    },
    {
        accessorKey: 'created_at',
        header: ({ column }) => (
            <DataTableColumnHeader column={column} title="创建时间" />
        ),
        cell: ({ row }) => {
            const date = row.getValue('created_at') as string;
            if (!date) return null;
            return format(new Date(date), 'yyyy-MM-dd HH:mm:ss');
        },
    },
    {
        id: 'actions',
        cell: ({ row }) => <DataTableRowActions row={row} />,
    },
]; 