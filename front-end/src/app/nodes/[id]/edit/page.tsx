'use client';

import { NodeForm } from "../../node-form";
import { getNode } from "@/lib/api";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Node } from "@/types";
import { toast } from "sonner";

function LoadingUI() {
    return (
        <div className="container mx-auto py-10">
            <div className="space-y-6">
                <h1 className="text-3xl font-bold tracking-tight">加载中...</h1>
                <div className="max-w-2xl animate-pulse">
                    <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
                    <div className="h-4 bg-gray-200 rounded w-1/2 mb-2"></div>
                    <div className="h-4 bg-gray-200 rounded w-2/3"></div>
                </div>
            </div>
        </div>
    );
}

export default function EditNodePage() {
    const params = useParams();
    const id = params?.id as string;
    const [node, setNode] = useState<Node | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        async function loadNode() {
            if (!id) return;
            
            try {
                const nodeData = await getNode(parseInt(id));
                if (!nodeData) {
                    notFound();
                }
                setNode(nodeData);
            } catch (err) {
                const message = err instanceof Error ? err.message : '加载节点数据失败';
                setError(message);
                toast.error(message);
            } finally {
                setLoading(false);
            }
        }

        loadNode();
    }, [id]);

    if (!id) {
        return notFound();
    }

    if (loading) {
        return <LoadingUI />;
    }

    if (error) {
        return (
            <div className="container mx-auto py-10">
                <div className="space-y-6">
                    <h1 className="text-3xl font-bold tracking-tight">加载失败</h1>
                    <div className="max-w-2xl">
                        <p className="text-red-500">{error}</p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="container mx-auto py-10">
            <div className="space-y-6">
                <h1 className="text-3xl font-bold tracking-tight">
                    编辑节点 {node?.name ? `- ${node.name}` : ''}
                </h1>
                <div className="max-w-2xl">
                    <Suspense fallback={<LoadingUI />}>
                        <NodeForm nodeId={parseInt(id)} />
                    </Suspense>
                </div>
            </div>
        </div>
    );
} 