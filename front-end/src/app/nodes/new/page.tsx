import { Metadata } from 'next';
import { NodeForm } from '../node-form';

export const metadata: Metadata = {
    title: '新建节点',
    description: '创建新的OPC UA节点',
};

export default function NewNodePage() {
    return (
        <div>
            <h1 className="text-3xl font-bold tracking-tight mb-6">新建节点</h1>
            <div className="max-w-2xl">
                <NodeForm />
            </div>
        </div>
    );
} 