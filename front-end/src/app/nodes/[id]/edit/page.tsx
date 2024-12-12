import { Metadata } from "next";
import { NodeForm } from "../../node-form";
import { getNode } from "@/lib/api";
import { notFound } from "next/navigation";

type Props = {
    params: Promise<{ id: string }>;
};

async function getNodeData(id: string) {
    const node = await getNode(parseInt(id));
    if (!node) {
        return null;
    }
    return node;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { id } = await params;
    const node = await getNodeData(id);
    
    if (!node) {
        return {
            title: '节点不存在',
            description: '找不到请求的 OPC UA 节点',
        };
    }

    return {
        title: `编辑节点 - ${node.name}`,
        description: `编辑 OPC UA 节点: ${node.name} (${node.node_id})`,
    };
}

export default async function EditNodePage({ params }: Props) {
    const { id } = await params;
    const node = await getNodeData(id);

    if (!node) {
        notFound();
    }

    return (
        <div>
            <div className="space-y-6">
                <h1 className="text-3xl font-bold tracking-tight">编辑节点 - {node.name}</h1>
                <div className="max-w-2xl">
                    <NodeForm nodeId={node.id} />
                </div>
            </div>
        </div>
    );
} 