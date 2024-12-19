'use client';

import { Button } from '@/components/ui/button';
import {
    Form,
    FormControl,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
    FormDescription,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { CreateServerDto, Node, OPCUAServer } from '@/types';
import { createServer, getNodes, updateServer, getServer } from '@/lib/api';
import { useRouter } from 'next/navigation';
import { useEffect, useState } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const serverSchema = z.object({
    name: z.string().min(1, '请输入服务器名称'),
    port: z.number().min(1024).max(65535),
    endpoint: z.string().optional(),
    nodeIds: z.array(z.string()),
});

type ServerFormValues = z.infer<typeof serverSchema>;

interface ServerFormProps {
    serverId?: number;
}

export function ServerForm({ serverId }: ServerFormProps) {
    const router = useRouter();
    const [nodes, setNodes] = useState<Node[]>([]);
    const [loading, setLoading] = useState(true);
    const [server, setServer] = useState<OPCUAServer | null>(null);
    const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
    const [initialLoad, setInitialLoad] = useState(true);

    const form = useForm<ServerFormValues>({
        resolver: zodResolver(serverSchema),
        defaultValues: {
            name: '',
            port: 4840,
            endpoint: '',
            nodeIds: [],
        },
    });

    useEffect(() => {
        async function loadData() {
            try {
                const nodesData = await getNodes(1, 100);
                setNodes(nodesData.items || []);

                if (serverId && initialLoad) {
                    const serverData = await getServer(serverId);
                    if (serverData) {
                        setServer(serverData);
                        const nodeIds = serverData.nodes.map(node => node.id.toString());
                        setSelectedNodes(new Set(nodeIds));
                        form.reset({
                            name: serverData.name,
                            port: serverData.port,
                            endpoint: serverData.endpoint || '',
                            nodeIds: nodeIds,
                        });
                    }
                    setInitialLoad(false);
                }
            } catch (error) {
                console.error('加载数据失败:', error);
                setNodes([]);
            } finally {
                setLoading(false);
            }
        }
        loadData();
    }, [serverId, form, initialLoad]);

    const handleNodeSelection = (nodeId: string, checked: boolean) => {
        const newSelection = new Set(selectedNodes);
        if (checked) {
            newSelection.add(nodeId);
        } else {
            newSelection.delete(nodeId);
        }
        setSelectedNodes(newSelection);
        const nodeIdsArray = Array.from(newSelection);
        form.setValue('nodeIds', nodeIdsArray, { shouldDirty: true });
    };

    const handleSelectAll = (checked: boolean) => {
        if (checked) {
            const allNodeIds = nodes.map(node => node.id.toString());
            setSelectedNodes(new Set(allNodeIds));
            form.setValue('nodeIds', allNodeIds, { shouldDirty: true });
        } else {
            setSelectedNodes(new Set());
            form.setValue('nodeIds', [], { shouldDirty: true });
        }
    };

    const isAllSelected = nodes.length > 0 && selectedNodes.size === nodes.length;
    const isIndeterminate = selectedNodes.size > 0 && selectedNodes.size < nodes.length;

    const onSubmit = async (values: ServerFormValues) => {
        try {
            const serverData = {
                ...values,
                endpoint: values.endpoint || `opc.tcp://0.0.0.0:${values.port}`,
                nodeIds: Array.from(selectedNodes).map(id => parseInt(id)),
            };

            if (serverId) {
                await updateServer(serverId, serverData);
            } else {
                await createServer(serverData);
            }
            router.push('/servers');
            router.refresh();
        } catch (error) {
            console.error('保存服务器失败:', error);
        }
    };

    if (loading) {
        return <div>加载中...</div>;
    }

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>服务器名称</FormLabel>
                            <FormControl>
                                <Input placeholder="生产线1号服务器" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="port"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>监听端口</FormLabel>
                            <FormControl>
                                <Input 
                                    type="number" 
                                    placeholder="4840" 
                                    {...field} 
                                    onChange={e => field.onChange(parseInt(e.target.value))}
                                />
                            </FormControl>
                            <FormDescription>
                                请输入 1024-65535 之间的端口号
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="endpoint"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>服务器地址 (可选)</FormLabel>
                            <FormControl>
                                <Input 
                                    placeholder="opc.tcp://0.0.0.0:4840" 
                                    {...field} 
                                />
                            </FormControl>
                            <FormDescription>
                                如果不填写，将使用默认格式：opc.tcp://0.0.0.0:端口号
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="nodeIds"
                    render={() => (
                        <FormItem>
                            <FormLabel>节点列表</FormLabel>
                            <Card>
                                <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
                                    <CardTitle>选择要发布的节点</CardTitle>
                                    <div className="flex items-center space-x-2">
                                        <Checkbox
                                            id="select-all"
                                            checked={isAllSelected}
                                            ref={(input: HTMLInputElement | null) => {
                                                if (input) {
                                                    input.indeterminate = isIndeterminate;
                                                }
                                            }}
                                            onCheckedChange={handleSelectAll}
                                        />
                                        <label
                                            htmlFor="select-all"
                                            className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                        >
                                            全选
                                        </label>
                                    </div>
                                </CardHeader>
                                <CardContent>
                                    <ScrollArea className="h-72 rounded-md border p-4">
                                        <div className="space-y-4">
                                            {nodes.map((node) => (
                                                <div key={node.id} className="flex items-center space-x-2">
                                                    <Checkbox
                                                        id={`node-${node.id}`}
                                                        checked={selectedNodes.has(node.id.toString())}
                                                        onCheckedChange={(checked) => {
                                                            handleNodeSelection(node.id.toString(), checked as boolean);
                                                        }}
                                                    />
                                                    <label
                                                        htmlFor={`node-${node.id}`}
                                                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                                    >
                                                        {node.name} ({node.node_id})
                                                    </label>
                                                </div>
                                            ))}
                                        </div>
                                    </ScrollArea>
                                </CardContent>
                            </Card>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <div className="flex justify-end gap-4">
                    <Button type="button" variant="outline" onClick={() => router.back()}>
                        取消
                    </Button>
                    <Button type="submit">
                        {serverId ? '保存修改' : '创建服务器'}
                    </Button>
                </div>
            </form>
        </Form>
    );
} 