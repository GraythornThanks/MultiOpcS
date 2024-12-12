import { Metadata } from "next";
import { ServerForm } from "../../server-form";
import { getServer } from "@/lib/api";
import { notFound } from "next/navigation";

type Props = {
    params: Promise<{ id: string }>;
};

async function getServerData(id: string) {
    const server = await getServer(parseInt(id));
    if (!server) {
        return null;
    }
    return server;
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
    const { id } = await params;
    const server = await getServerData(id);
    
    if (!server) {
        return {
            title: '服务器不存在',
            description: '找不到请求的 OPC UA 服务器',
        };
    }

    return {
        title: `编辑服务器 - ${server.name}`,
        description: `编辑 OPC UA 服务器: ${server.name}`,
    };
}

export default async function EditServerPage({ params }: Props) {
    const { id } = await params;
    const server = await getServerData(id);

    if (!server) {
        notFound();
    }

    return (
        <div className="container mx-auto py-10">
            <div className="space-y-6">
                <h1 className="text-3xl font-bold tracking-tight">编辑服务器 - {server.name}</h1>
                <div className="max-w-2xl">
                    <ServerForm serverId={server.id} />
                </div>
            </div>
        </div>
    );
} 