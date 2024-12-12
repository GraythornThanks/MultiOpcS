import { Metadata } from 'next';
import { columns } from './columns';
import { DataTable } from './data-table';
import { Button } from '@/components/ui/button';
import Link from 'next/link';
import { getNodes } from '@/lib/api';
import { Plus } from 'lucide-react';

export const metadata: Metadata = {
    title: '节点管理',
    description: 'OPC UA节点管理界面',
};

export default async function NodesPage() {
    const nodes = await getNodes();

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
            <DataTable columns={columns} data={nodes} />
        </div>
    );
} 