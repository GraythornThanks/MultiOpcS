'use client';

import { columns } from './columns';
import { DataTable } from './data-table';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { getNodes } from '@/lib/api';
import { Plus } from 'lucide-react';
import { useEffect, useState } from 'react';
import { Node } from '@/types';
import {
    Pagination,
    PaginationContent,
    PaginationEllipsis,
    PaginationItem,
    PaginationLink,
    PaginationNext,
    PaginationPrevious,
} from "@/components/ui/pagination";
import { toast } from 'sonner';

export default function NodesPage() {
    const [nodes, setNodes] = useState<Node[]>([]);
    const [currentPage, setCurrentPage] = useState(1);
    const [totalPages, setTotalPages] = useState(1);
    const [isLoading, setIsLoading] = useState(true);
    const pageSize = 10;

    useEffect(() => {
        const fetchNodes = async () => {
            setIsLoading(true);
            try {
                const response = await getNodes(currentPage, pageSize);
                console.log('获取到的节点数据:', response);
                
                if (response && Array.isArray(response.items)) {
                    setNodes(response.items);
                    setTotalPages(response.pages);
                    
                    // 如果当前页超出总页数，自动跳转到最后一页
                    if (currentPage > response.pages) {
                        setCurrentPage(response.pages);
                    }
                } else {
                    console.error('返回的数据格式不正确:', response);
                    setNodes([]);
                    setTotalPages(1);
                }
            } catch (error) {
                console.error('加载节点失败:', error);
                toast.error('加载节点失败');
                setNodes([]);
                setTotalPages(1);
            } finally {
                setIsLoading(false);
            }
        };

        fetchNodes();
    }, [currentPage, pageSize]);

    const handlePageChange = (page: number) => {
        if (page >= 1 && page <= totalPages) {
            setCurrentPage(page);
        }
    };

    // 生成页码数组
    const getPageNumbers = () => {
        const pages = [];
        const maxVisiblePages = 5; // 最多显示的页码数
        
        if (totalPages <= maxVisiblePages) {
            // 如果总页数小于等于最大显示数，显示所有页码
            for (let i = 1; i <= totalPages; i++) {
                pages.push(i);
            }
        } else {
            // 否则显示部分页码
            if (currentPage <= 3) {
                // 当前页靠近开始
                for (let i = 1; i <= 4; i++) {
                    pages.push(i);
                }
                pages.push(-1); // 表示省略号
                pages.push(totalPages);
            } else if (currentPage >= totalPages - 2) {
                // 当前页靠近结束
                pages.push(1);
                pages.push(-1);
                for (let i = totalPages - 3; i <= totalPages; i++) {
                    pages.push(i);
                }
            } else {
                // 当前页在中间
                pages.push(1);
                pages.push(-1);
                for (let i = currentPage - 1; i <= currentPage + 1; i++) {
                    pages.push(i);
                }
                pages.push(-1);
                pages.push(totalPages);
            }
        }
        
        return pages;
    };

    return (
        <div>
            <div className="flex justify-between items-center mb-6">
                <h1 className="text-3xl font-bold tracking-tight">节点管理</h1>
                <div className="flex items-center space-x-2">
                    <div id="batch-delete-container" />
                    <Button asChild>
                        <Link href="/nodes/new">
                            <Plus className="mr-2 h-4 w-4" />
                            添加节点
                        </Link>
                    </Button>
                </div>
            </div>
            
            <DataTable columns={columns} data={nodes} isLoading={isLoading} />
            
            {!isLoading && totalPages > 1 && (
                <div className="mt-4 flex justify-center">
                    <Pagination>
                        <PaginationContent>
                            <PaginationItem>
                                <PaginationPrevious 
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        handlePageChange(currentPage - 1);
                                    }}
                                    className={currentPage === 1 ? 'pointer-events-none opacity-50' : ''}
                                />
                            </PaginationItem>
                            
                            {getPageNumbers().map((pageNum, index) => (
                                pageNum === -1 ? (
                                    <PaginationItem key={`ellipsis-${index}`}>
                                        <PaginationEllipsis />
                                    </PaginationItem>
                                ) : (
                                    <PaginationItem key={pageNum}>
                                        <PaginationLink
                                            href="#"
                                            onClick={(e) => {
                                                e.preventDefault();
                                                handlePageChange(pageNum);
                                            }}
                                            isActive={pageNum === currentPage}
                                        >
                                            {pageNum}
                                        </PaginationLink>
                                    </PaginationItem>
                                )
                            ))}
                            
                            <PaginationItem>
                                <PaginationNext 
                                    href="#"
                                    onClick={(e) => {
                                        e.preventDefault();
                                        handlePageChange(currentPage + 1);
                                    }}
                                    className={currentPage === totalPages ? 'pointer-events-none opacity-50' : ''}
                                />
                            </PaginationItem>
                        </PaginationContent>
                    </Pagination>
                </div>
            )}
        </div>
    );
} 