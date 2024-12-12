'use client';

import {
    ColumnDef,
    flexRender,
    getCoreRowModel,
    useReactTable,
    getPaginationRowModel,
    SortingState,
    getSortedRowModel,
    ColumnFiltersState,
    getFilteredRowModel,
    RowSelectionState,
} from '@tanstack/react-table';

import {
    Table,
    TableBody,
    TableCell,
    TableHead,
    TableHeader,
    TableRow,
} from '@/components/ui/table';
import { useState, useEffect } from 'react';
import { Button } from '@/components/ui/button';
import { Trash2 } from 'lucide-react';
import { deleteNode } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import { createPortal } from 'react-dom';

interface DataTableProps<TData, TValue> {
    columns: ColumnDef<TData, TValue>[];
    data: TData[];
}

export function DataTable<TData, TValue>({
    columns,
    data,
}: DataTableProps<TData, TValue>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
    const router = useRouter();

    // 重置选择状态
    useEffect(() => {
        setRowSelection({});
    }, [data]);

    const table = useReactTable({
        data,
        columns,
        getCoreRowModel: getCoreRowModel(),
        getPaginationRowModel: getPaginationRowModel(),
        onSortingChange: setSorting,
        getSortedRowModel: getSortedRowModel(),
        onColumnFiltersChange: setColumnFilters,
        getFilteredRowModel: getFilteredRowModel(),
        onRowSelectionChange: setRowSelection,
        enableRowSelection: true,
        state: {
            sorting,
            columnFilters,
            rowSelection,
        },
    });

    const handleBatchDelete = async () => {
        const selectedRows = table.getFilteredSelectedRowModel().rows;
        if (selectedRows.length === 0) {
            toast.error('请选择要删除的节点');
            return;
        }

        if (confirm(`确定要删除选中的 ${selectedRows.length} 个节点吗？`)) {
            try {
                const deletePromises = selectedRows.map(async (row) => {
                    const node = row.original as any;
                    await deleteNode(node.id);
                });

                await Promise.all(deletePromises);
                toast.success(`成功删除 ${selectedRows.length} 个节点`);
                setRowSelection({}); // 清空选择状态
                router.refresh();
            } catch (error) {
                console.error('批量删除节点失败:', error);
                toast.error('批量删除节点失败');
            }
        }
    };

    // 渲染删除按钮到指定容器
    const renderDeleteButton = () => {
        const container = document.getElementById('batch-delete-container');
        if (!container) return null;

        return createPortal(
            table.getFilteredSelectedRowModel().rows.length > 0 && (
                <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBatchDelete}
                    className="h-9"
                >
                    <Trash2 className="mr-2 h-4 w-4" />
                    删除所选 ({table.getFilteredSelectedRowModel().rows.length})
                </Button>
            ),
            container
        );
    };

    return (
        <div>
            {renderDeleteButton()}
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => {
                                    return (
                                        <TableHead key={header.id}>
                                            {header.isPlaceholder
                                                ? null
                                                : flexRender(
                                                      header.column.columnDef.header,
                                                      header.getContext()
                                                  )}
                                        </TableHead>
                                    );
                                })}
                            </TableRow>
                        ))}
                    </TableHeader>
                    <TableBody>
                        {table.getRowModel().rows?.length ? (
                            table.getRowModel().rows.map((row) => (
                                <TableRow
                                    key={row.id}
                                    data-state={row.getIsSelected() && 'selected'}
                                >
                                    {row.getVisibleCells().map((cell) => (
                                        <TableCell key={cell.id}>
                                            {flexRender(
                                                cell.column.columnDef.cell,
                                                cell.getContext()
                                            )}
                                        </TableCell>
                                    ))}
                                </TableRow>
                            ))
                        ) : (
                            <TableRow>
                                <TableCell
                                    colSpan={columns.length}
                                    className="h-24 text-center"
                                >
                                    暂无数据
                                </TableCell>
                            </TableRow>
                        )}
                    </TableBody>
                </Table>
            </div>
        </div>
    );
} 