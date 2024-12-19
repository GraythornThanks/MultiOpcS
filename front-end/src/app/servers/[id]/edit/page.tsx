'use client';

import { Metadata } from "next";
import { ServerForm } from "../../server-form";
import { getServer } from "@/lib/api";
import { notFound } from "next/navigation";
import { Suspense } from "react";
import { useParams } from "next/navigation";

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

export default function EditServerPage() {
    const params = useParams();
    const id = params?.id as string;

    if (!id) {
        return notFound();
    }

    return (
        <div className="container mx-auto py-10">
            <div className="space-y-6">
                <h1 className="text-3xl font-bold tracking-tight">编辑服务器</h1>
                <div className="max-w-2xl">
                    <Suspense fallback={<LoadingUI />}>
                        <ServerForm serverId={parseInt(id)} />
                    </Suspense>
                </div>
            </div>
        </div>
    );
} 