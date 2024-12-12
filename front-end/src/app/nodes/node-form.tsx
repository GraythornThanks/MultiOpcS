'use client';

import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import * as z from 'zod';
import { useRouter } from 'next/navigation';
import { toast } from 'sonner';
import {
    Form,
    FormControl,
    FormDescription,
    FormField,
    FormItem,
    FormLabel,
    FormMessage,
} from '@/components/ui/form';
import { Input } from '@/components/ui/input';
import { Button } from '@/components/ui/button';
import {
    Select,
    SelectContent,
    SelectItem,
    SelectTrigger,
    SelectValue,
} from '@/components/ui/select';
import { createNode, updateNode, getNode, getNodes } from '@/lib/api';
import { useEffect, useState } from 'react';
import { Node } from '@/types';
import { Checkbox } from '@/components/ui/checkbox';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Switch } from '@/components/ui/switch';

interface Server {
    id: number;
    name: string;
}

const dataTypes = [
    // 数值类型
    { value: "BOOL", label: "布尔值 (Boolean)" },
    { value: "CHAR", label: "字符 (Char)" },
    { value: "INT32", label: "32���整数 (Int32)" },
    { value: "INT64", label: "64位整数 (Int64)" },
    { value: "UINT16", label: "无符号16位整数 (UInt16)" },
    { value: "UINT32", label: "无符号32位整数 (UInt32)" },
    { value: "UINT64", label: "无符号64位整数 (UInt64)" },
    { value: "FLOAT", label: "32位浮点数 (Float)" },
    { value: "DOUBLE", label: "64位浮点数 (Double)" },
    
    // 字符串类型
    { value: "STRING", label: "字符串 (String)" },
    { value: "DATETIME", label: "日期时间 (DateTime)" },
    { value: "BYTESTRING", label: "字节字符串 (ByteString)" },
] as const;

type DataType = typeof dataTypes[number]['value'];

const accessLevels = [
    { value: "READ", label: "只读" },
    { value: "WRITE", label: "只写" },
    { value: "READWRITE", label: "读写" },
] as const;

type AccessLevel = typeof accessLevels[number]['value'];

interface NodeFormProps {
    nodeId?: number;
}

// 解析占位符模式
const parsePlaceholderPattern = (name: string): { hasPlaceholder: boolean; pattern?: string } => {
    // 修改正则表达式以匹配字符串中任何位置的 {n} 或 {数字} 占位符
    const match = name.match(/\{(\d*n?)\}/);
    if (match) {
        return { hasPlaceholder: true, pattern: match[1] || 'n' };
    }
    return { hasPlaceholder: false };
};

// 生成批量节点名称
const generateBatchNames = (baseName: string, count: number): string[] => {
    const names: string[] = [];
    for (let i = 1; i <= count; i++) {
        // 支持替换所有出现的 {n} 或 {数字} 占位符
        names.push(baseName.replace(/\{(\d*n?)\}/g, i.toString()));
    }
    return names;
};

// NodeId 格式验证函数
const isValidNodeId = (value: string) => {
    // NodeId 格式: ns=<namespaceIndex>;<identifiertype>=<identifier>
    // 例如: ns=2;i=1234 或 ns=2;s=MyNode
    const nodeIdPattern = /^(ns=\d+;)?[isb]=.+$/;
    return nodeIdPattern.test(value);
};

// 根据数据类型验证初始值
const validateInitialValue = (value: string, dataType: string): { isValid: boolean; message?: string } => {
    if (!value) return { isValid: true };

    try {
        switch (dataType) {
            case 'BOOL':
                if (!['true', 'false'].includes(value.toLowerCase())) {
                    return { isValid: false, message: "布尔值必须是 true 或 false" };
                }
                break;

            case 'CHAR':
                if (value.length !== 1) {
                    return { isValid: false, message: "字符类型必须是单个字符" };
                }
                break;

            case 'INT32':
                const int32Val = parseInt(value);
                if (isNaN(int32Val)) {
                    return { isValid: false, message: "请输入有效的整数" };
                }
                if (int32Val < -2147483648 || int32Val > 2147483647) {
                    return { isValid: false, message: "INT32 的值必须在 -2147483648 到 2147483647 之间" };
                }
                break;

            case 'INT64':
                const int64Val = BigInt(value);
                if (int64Val < BigInt('-9223372036854775808') || int64Val > BigInt('9223372036854775807')) {
                    return { isValid: false, message: "INT64 的值超出范围" };
                }
                break;

            case 'UINT16':
                const uint16Val = parseInt(value);
                if (isNaN(uint16Val)) {
                    return { isValid: false, message: "请输入有效的整数" };
                }
                if (uint16Val < 0 || uint16Val > 65535) {
                    return { isValid: false, message: "UINT16 的值必须在 0 到 65535 之间" };
                }
                break;

            case 'UINT32':
                const uint32Val = parseInt(value);
                if (isNaN(uint32Val)) {
                    return { isValid: false, message: "请输��有效的整数" };
                }
                if (uint32Val < 0 || uint32Val > 4294967295) {
                    return { isValid: false, message: "UINT32 的值必须在 0 到 4294967295 之间" };
                }
                break;

            case 'UINT64':
                const uint64Val = BigInt(value);
                if (uint64Val < BigInt(0) || uint64Val > BigInt('18446744073709551615')) {
                    return { isValid: false, message: "UINT64 的值超出范围" };
                }
                break;

            case 'FLOAT':
            case 'DOUBLE':
                const floatVal = parseFloat(value);
                if (isNaN(floatVal)) {
                    return { isValid: false, message: "请输入有效的浮点数" };
                }
                break;

            case 'DATETIME':
                // 验证ISO 8601格式
                const datePattern = /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{3})?Z$/;
                if (!datePattern.test(value)) {
                    return { 
                        isValid: false, 
                        message: "日期时间必须符合 ISO 8601 格式 (YYYY-MM-DDThh:mm:ss.sssZ)" 
                    };
                }
                // 尝试解析日期
                try {
                    new Date(value);
                } catch {
                    return { isValid: false, message: "无效的日期时间" };
                }
                break;
        }
        return { isValid: true };
    } catch (error) {
        return { isValid: false, message: "无效的值" };
    }
};

export function NodeForm({ nodeId }: NodeFormProps) {
    const router = useRouter();
    const [existingNodeIds, setExistingNodeIds] = useState<Set<string>>(new Set());
    const [existingNames, setExistingNames] = useState<Set<string>>(new Set());
    const [initialNodeId, setInitialNodeId] = useState<string>('');
    const [initialName, setInitialName] = useState<string>('');
    const [isSubmitting, setIsSubmitting] = useState(false);
    const [initialValueError, setInitialValueError] = useState<string | null>(null);
    const [selectedServers, setSelectedServers] = useState<Set<number>>(new Set());
    const [tempSelectedServers, setTempSelectedServers] = useState<Set<number>>(new Set());
    const [servers, setServers] = useState<Server[]>([]);
    const [isBatchMode, setIsBatchMode] = useState(false);
    const [batchCount, setBatchCount] = useState(1);

    // 获取所有现有节点的信息
    useEffect(() => {
        const fetchExistingNodes = async () => {
            try {
                const nodes = await getNodes();
                const nodeIds = new Set(nodes.map(node => node.node_id));
                const names = new Set(nodes.map(node => node.name));
                setExistingNodeIds(nodeIds);
                setExistingNames(names);
            } catch (error) {
                console.error('获取节点列表失败:', error);
                toast.error('获取节点列表失败');
            }
        };
        fetchExistingNodes();
    }, []);

    // 加载服务器列表
    useEffect(() => {
        const fetchServers = async () => {
            try {
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/servers`);
                if (!response.ok) throw new Error('加载服务器列表失败');
                const data = await response.json();
                setServers(data);
            } catch (error) {
                console.error('加载服务器列表失败:', error);
                toast.error('加载服务器列表失败');
            }
        };
        fetchServers();
    }, []);

    const formSchema = z.object({
        name: z.string()
            .min(1, "节点名称不能为空")
            .refine(
                (name) => {
                    if (!nodeId) { // 创建新节点时检查
                        return !existingNames.has(name);
                    }
                    return name === initialName || !existingNames.has(name);
                },
                {
                    message: "此节点名称已被使用"
                }
            ),
        node_id: z.string()
            .min(1, "节点ID不能为空")
            .refine(
                (value) => isValidNodeId(value),
                {
                    message: "节点ID格式无效，正确格式示例：ns=2;i=1234 或 ns=2;s=MyNode"
                }
            )
            .refine(
                (value) => {
                    if (!nodeId) { // 创建新节点时检查
                        return !existingNodeIds.has(value);
                    }
                    return value === initialNodeId || !existingNodeIds.has(value);
                },
                {
                    message: "此节点ID已被使用"
                }
            ),
        data_type: z.enum(["UINT16", "UINT32", "UINT64", "INT32", "INT64", "FLOAT", "DOUBLE", "STRING", "BYTESTRING", "CHAR", "BOOL", "DATETIME"]),
        access_level: z.enum(["READ", "WRITE", "READWRITE"]),
        description: z.string().optional(),
        initial_value: z.string().optional(),
        serverIds: z.array(z.number()).optional()
    }).refine((data) => {
        if (!data.initial_value) return true;
        const result = validateInitialValue(data.initial_value, data.data_type);
        if (!result.isValid) {
            throw new Error(result.message);
        }
        return true;
    }, {
        message: "初始值无效",
        path: ["initial_value"]
    });

    type FormValues = z.infer<typeof formSchema>;

    const form = useForm<FormValues>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: '',
            node_id: 'ns=2;s=',
            data_type: 'INT32',
            access_level: 'READWRITE',
            description: '',
            initial_value: '',
            serverIds: [],
        },
    });

    // 如果是编辑模式，加载现有节点数据
    useEffect(() => {
        if (nodeId) {
            const loadNode = async () => {
                try {
                    const nodeData = await getNode(nodeId);
                    if (!nodeData) {
                        toast.error('节点不存在');
                        router.push('/nodes');
                        return;
                    }
                    
                    // 只在首次加载时设置初始值
                    if (!initialNodeId) {
                        setInitialNodeId(nodeData.node_id);
                        setInitialName(nodeData.name);
                        
                        // 设置表单初始值，包括服务器关联
                        const formData = {
                            name: nodeData.name,
                            node_id: nodeData.node_id,
                            data_type: nodeData.data_type as DataType,
                            access_level: nodeData.access_level,
                            description: nodeData.description,
                            initial_value: nodeData.initial_value,
                            serverIds: nodeData.servers?.map(server => server.id) || [],
                        };
                        
                        form.reset(formData);

                        // 设置选中的服务器
                        if (nodeData.servers && Array.isArray(nodeData.servers)) {
                            const serverIds = nodeData.servers.map(server => server.id);
                            const serverIdSet = new Set(serverIds);
                            setSelectedServers(serverIdSet);
                            setTempSelectedServers(serverIdSet);
                        }
                    }
                } catch (error) {
                    console.error('加载节点数据失败:', error);
                    toast.error('加载节点数据失败');
                }
            };
            loadNode();
        }
    }, [nodeId, form, router, initialNodeId]);

    // 处理服务器选择变化
    const handleServerChange = (serverId: number, checked: boolean) => {
        setTempSelectedServers(prev => {
            const newSet = new Set(prev);
            if (checked) {
                newSet.add(serverId);
            } else {
                newSet.delete(serverId);
            }
            return newSet;
        });
    };

    // 渲染服务器选择列表
    const renderServerSelection = () => {
        return (
            <FormItem>
                <FormLabel>关联服务器</FormLabel>
                <ScrollArea className="h-[200px] w-full rounded-md border">
                    <div className="p-4">
                        {servers.map((server) => (
                            <div key={server.id} className="flex items-center space-x-2 mb-2">
                                <Checkbox
                                    id={`server-${server.id}`}
                                    checked={tempSelectedServers.has(server.id)}
                                    onCheckedChange={(checked) => handleServerChange(server.id, checked as boolean)}
                                />
                                <label
                                    htmlFor={`server-${server.id}`}
                                    className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70"
                                >
                                    {server.name}
                                </label>
                            </div>
                        ))}
                    </div>
                </ScrollArea>
            </FormItem>
        );
    };

    const onSubmit = async (data: FormValues) => {
        try {
            setIsSubmitting(true);
            
            // 最后一次验证初始值
            if (data.initial_value) {
                const result = validateInitialValue(data.initial_value, data.data_type);
                if (!result.isValid) {
                    toast.error(result.message);
                    return;
                }
            }

            // 确保 serverIds 字段存在，使用临时选择的服务器
            const submitData = {
                ...data,
                serverIds: Array.from(tempSelectedServers),
            };

            if (nodeId) {
                await updateNode(nodeId, submitData);
                // 更新成功后，更新实际选中的服务器
                setSelectedServers(tempSelectedServers);
                toast.success('节点更新成功');
            } else {
                if (isBatchMode) {
                    const namePattern = parsePlaceholderPattern(data.name);
                    const nodeIdPattern = parsePlaceholderPattern(data.node_id);
                    
                    if (!namePattern.hasPlaceholder && !nodeIdPattern.hasPlaceholder) {
                        toast.error('批量创建模式需要在节点名称或节点ID中至少使用一个 {n} 占位符');
                        return;
                    }
                    
                    try {
                        const batchNames = namePattern.hasPlaceholder 
                            ? generateBatchNames(data.name, batchCount)
                            : Array(batchCount).fill(data.name);
                            
                        const batchNodeIds = nodeIdPattern.hasPlaceholder
                            ? generateBatchNames(data.node_id, batchCount)
                            : Array(batchCount).fill(data.node_id);
                        
                        for (let i = 0; i < batchCount; i++) {
                            const batchData = {
                                ...submitData,
                                name: batchNames[i],
                                node_id: batchNodeIds[i],
                            };
                            await createNode(batchData);
                        }
                        toast.success(`成功创建 ${batchCount} 个节点`);
                    } catch (error) {
                        console.error('批量创建节点失败:', error);
                        toast.error('批量创建节点失败，请检查占位符格式是否正确');
                        return;
                    }
                } else {
                    await createNode(submitData);
                    toast.success('节点创建成功');
                }
            }
            router.push('/nodes');
            router.refresh();
        } catch (error: any) {
            console.error('保存节点失败:', error);
            toast.error(error.message || '保存节点失败');
        } finally {
            setIsSubmitting(false);
        }
    };

    // 获取数据类型的示例值
    const getInitialValuePlaceholder = (dataType: string): string => {
        switch (dataType) {
            case 'BOOL': return '请选择 true 或 false';
            case 'CHAR': return '单个字符';
            case 'INT32': return '-2147483648 到 2147483647';
            case 'INT64': return '-9223372036854775808 到 9223372036854775807';
            case 'UINT16': return '0 到 65535';
            case 'UINT32': return '0 到 4294967295';
            case 'UINT64': return '0 到 18446744073709551615';
            case 'FLOAT': return '单精度浮点数，如: 3.14';
            case 'DOUBLE': return '双精度浮点数，如: 3.14159';
            case 'STRING': return '文本字符串';
            case 'DATETIME': return '格式: YYYY-MM-DDThh:mm:ss.sssZ (例如: 2024-01-01T12:00:00.000Z)';
            case 'BYTESTRING': return '字节字符串';
            default: return '';
        }
    };

    // 检查表单是否有效
    const isFormValid = () => {
        const values = form.getValues();
        const formState = form.getFieldState('name');
        const nodeIdState = form.getFieldState('node_id');
        
        // 检查必填字段
        if (!values.name || !values.node_id) {
            return false;
        }

        // 检查字段是否有错误
        if (formState.error || nodeIdState.error) {
            return false;
        }

        // 检查初始值
        if (values.initial_value) {
            const result = validateInitialValue(values.initial_value, values.data_type);
            if (!result.isValid) {
                return false;
            }
        }

        return true;
    };

    // 渲染初始值��入控件
    const renderInitialValueInput = (dataType: string, field: any) => {
        const validateInput = (value: string) => {
            if (!value) {
                setInitialValueError(null);
                return;
            }
            const result = validateInitialValue(value, dataType);
            if (!result.isValid) {
                setInitialValueError(result.message || "无效的值");
            } else {
                setInitialValueError(null);
            }
        };

        if (dataType === 'BOOL') {
            return (
                <Select 
                    onValueChange={field.onChange} 
                    value={field.value}
                >
                    <FormControl>
                        <SelectTrigger>
                            <SelectValue placeholder="请选择布尔值" />
                        </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                        <SelectItem value="true">true</SelectItem>
                        <SelectItem value="false">false</SelectItem>
                    </SelectContent>
                </Select>
            );
        }
        
        return (
            <div className="space-y-2">
                <Input
                    placeholder={getInitialValuePlaceholder(dataType)}
                    value={field.value || ''}
                    onChange={(e) => {
                        field.onChange(e);
                        validateInput(e.target.value);
                    }}
                />
                {initialValueError && (
                    <div className="text-sm text-yellow-600 dark:text-yellow-500 flex items-center gap-2">
                        <svg xmlns="http://www.w3.org/2000/svg" className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                            <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                        </svg>
                        {initialValueError}
                    </div>
                )}
            </div>
        );
    };

    return (
        <Form {...form}>
            <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-8">
                {!nodeId && (
                    <div className="flex items-center space-x-4">
                        <FormItem className="flex flex-row items-center space-x-4">
                            <FormLabel>批量创建</FormLabel>
                            <FormControl>
                                <Switch
                                    checked={isBatchMode}
                                    onCheckedChange={setIsBatchMode}
                                />
                            </FormControl>
                        </FormItem>
                        {isBatchMode && (
                            <FormItem className="flex flex-row items-center space-x-4">
                                <FormLabel>创建数量</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        min="1"
                                        max="100"
                                        value={batchCount}
                                        onChange={(e) => setBatchCount(parseInt(e.target.value) || 1)}
                                        className="w-24"
                                    />
                                </FormControl>
                            </FormItem>
                        )}
                    </div>
                )}

                <FormField
                    control={form.control}
                    name="name"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>节点名称</FormLabel>
                            <FormControl>
                                <Input placeholder={isBatchMode ? "使用 {n} 作为占位符，例如: Tube{n}.No" : "请输入节点名称"} {...field} />
                            </FormControl>
                            {isBatchMode && (
                                <FormDescription>
                                    使用 {'{n}'} 作为占位符，例如：Tube{'{n}'}.No 将生成 Tube1.No, Tube2.No, Tube3.No...
                                </FormDescription>
                            )}
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="node_id"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>节点ID</FormLabel>
                            <FormControl>
                                <Input 
                                    placeholder={isBatchMode ? "使用 {n} 作为占位符，例如: ns=2;s=Tube{n}.No" : "例如: ns=2;s=Channel1.Device1.Tag1"} 
                                    {...field} 
                                />
                            </FormControl>
                            <div className="text-sm text-muted-foreground">
                                示例：
                                <ul className="list-disc list-inside text-sm mt-1">
                                    <li><code>ns=2;s=Tube{'{n}'}.No</code> - 批量字符串标识符</li>
                                    <li><code>ns=2;i={'{n}'}</code> - 批量数字标识符</li>
                                </ul>
                            </div>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="data_type"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>数据类型</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="请选择数据类型" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {dataTypes.map(dataType => (
                                        <SelectItem key={dataType.value} value={dataType.value}>
                                            {dataType.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="access_level"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>访问级别</FormLabel>
                            <Select onValueChange={field.onChange} defaultValue={field.value}>
                                <FormControl>
                                    <SelectTrigger>
                                        <SelectValue placeholder="请选择访问级别" />
                                    </SelectTrigger>
                                </FormControl>
                                <SelectContent>
                                    {accessLevels.map(level => (
                                        <SelectItem key={level.value} value={level.value}>
                                            {level.label}
                                        </SelectItem>
                                    ))}
                                </SelectContent>
                            </Select>
                            <FormDescription>
                                选择节点的访问权限
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="initial_value"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>初始值</FormLabel>
                            <FormControl>
                                {renderInitialValueInput(form.watch('data_type'), field)}
                            </FormControl>
                            <FormDescription>
                                请输入与所选数据类型匹配的初始值
                            </FormDescription>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                <FormField
                    control={form.control}
                    name="description"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>描述</FormLabel>
                            <FormControl>
                                <Input placeholder="请输入节点描述" {...field} />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />

                {renderServerSelection()}

                <div className="flex justify-end gap-4">
                    <Button
                        type="button"
                        variant="outline"
                        onClick={() => router.back()}
                    >
                        取消
                    </Button>
                    <Button 
                        type="submit" 
                        disabled={isSubmitting || !isFormValid() || !!initialValueError}
                    >
                        {isSubmitting ? '保存中...' : (nodeId ? '更新' : '创建')}
                    </Button>
                </div>
            </form>
        </Form>
    );
} 