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
    isLoading?: boolean;
}

export function DataTable<TData, TValue>({
    columns,
    data,
    isLoading = false,
}: DataTableProps<TData, TValue>) {
    const [sorting, setSorting] = useState<SortingState>([]);
    const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
    const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
    const [mounted, setMounted] = useState(false);
    const [isInitialized, setIsInitialized] = useState(false);
    const router = useRouter();

    // 客户端挂载检测
    useEffect(() => {
        setMounted(true);
        return () => {
            setMounted(false);
            setIsInitialized(false);
        };
    }, []);

    // 数据初始化检测
    useEffect(() => {
        if (mounted && data) {
            console.log('数据初始化检查:', { data, isArray: Array.isArray(data), length: data.length });
            setIsInitialized(true);
        }
    }, [mounted, data]);

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

    console.log('表格数据状态:', {
        mounted,
        isInitialized,
        dataLength: data?.length,
        rowsLength: table.getRowModel().rows?.length,
    });

    const handleBatchDelete = async () => {
        if (!isInitialized || !table) return;
        
        try {
            const selectedModel = table.getFilteredSelectedRowModel();
            if (!selectedModel?.rows?.length) {
                toast.error('请选择要删除的节点');
                return;
            }

            const selectedRows = selectedModel.rows;
            if (confirm(`确定要删除选中的 ${selectedRows.length} 个节点吗？`)) {
                try {
                    const deletePromises = selectedRows.map(async (row) => {
                        const node = row.original as any;
                        if (!node?.id) {
                            throw new Error('节点数据无效');
                        }
                        await deleteNode(node.id);
                    });

                    await Promise.all(deletePromises);
                    toast.success(`成功删除 ${selectedRows.length} 个节点`);
                    setRowSelection({});
                    router.refresh();
                } catch (error) {
                    console.error('批量删除节点失败:', error);
                    toast.error('批量删除节点失败');
                }
            }
        } catch (error) {
            console.error('获取选中行数据失败:', error);
            toast.error('获取选中行数据失败');
        }
    };

    // 渲染删除按钮到指定容器
    const renderDeleteButton = () => {
        if (!mounted || !isInitialized || !table) return null;
        
        try {
            const container = document.getElementById('batch-delete-container');
            if (!container) return null;

            const selectedCount = Object.keys(rowSelection).length;
            if (selectedCount === 0) return null;

            return createPortal(
                <Button
                    variant="destructive"
                    size="sm"
                    onClick={handleBatchDelete}
                    className="h-9"
                >
                    <Trash2 className="mr-2 h-4 w-4" />
                    删除所选 ({selectedCount})
                </Button>,
                container
            );
        } catch (error) {
            console.error('渲染删除按钮失败:', error);
            return null;
        }
    };

    if (isLoading) {
        return (
            <div className="w-full h-24 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
        );
    }

    if (!mounted || !isInitialized) {
        return (
            <div className="w-full h-24 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-gray-900"></div>
            </div>
        );
    }

    return (
        <div>
            {renderDeleteButton()}
            <div className="rounded-md border">
                <Table>
                    <TableHeader>
                        {table.getHeaderGroups().map((headerGroup) => (
                            <TableRow key={headerGroup.id}>
                                {headerGroup.headers.map((header) => (
                                    <TableHead key={header.id}>
                                        {header.isPlaceholder
                                            ? null
                                            : flexRender(
                                                  header.column.columnDef.header,
                                                  header.getContext()
                                              )}
                                    </TableHead>
                                ))}
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