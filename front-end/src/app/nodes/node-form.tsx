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
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import {
    Card,
    CardContent,
    CardDescription,
    CardFooter,
    CardHeader,
    CardTitle,
} from "@/components/ui/card";

interface Server {
    id: number;
    name: string;
}

const dataTypes = [
    // 数值类型
    { value: "UINT16", label: "无符号16位整数 (UInt16)" },
    { value: "UINT32", label: "无符号32位整数 (UInt32)" },
    { value: "UINT64", label: "无符号64位整数 (UInt64)" },
    { value: "INT32", label: "32位整数 (Int32)" },
    { value: "INT64", label: "64位整数 (Int64)" },
    { value: "FLOAT", label: "32位浮点数 (Float)" },
    { value: "DOUBLE", label: "64位浮点数 (Double)" },
    { value: "BOOL", label: "布尔值 (Boolean)" },
    { value: "CHAR", label: "字符 (Char)" },
    
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

const valueChangeOptions = [
    { value: 'none', label: '不自动变化' },
    { value: 'linear', label: '线性变化' },
    { value: 'discrete', label: '离散值变��' },
    { value: 'random', label: '随机变化' },
    { value: 'conditional', label: '条件变化' },
];

type ValueChangeType = typeof valueChangeOptions[number]['value'];

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

// 根据数据类型验证点初始值
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
                    return { isValid: false, message: "INT64 的值超范围" };
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
                    return { isValid: false, message: "请输入有效的整数" };
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
                    return { isValid: false, message: "��输入有效的浮点数" };
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

// 线性变化配置表单
function LinearChangeConfig({ form }: { form: any }) {
    return (
        <Card>
            <CardContent className="pt-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="value_change_config.min_value"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>最小值</FormLabel>
                                <FormControl>
                                    <Input type="number" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="value_change_config.max_value"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>最大值</FormLabel>
                                <FormControl>
                                    <Input type="number" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>
                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="value_change_config.update_interval"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>更新间隔 (毫秒)</FormLabel>
                                <FormControl>
                                    <Input type="number" min="100" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="value_change_config.step_size"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>变化步长</FormLabel>
                                <FormControl>
                                    <Input type="number" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>
                <div className="space-y-4">
                    <FormField
                        control={form.control}
                        name="value_change_config.random_interval"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                                <div className="space-y-0.5">
                                    <FormLabel>随机更新间隔</FormLabel>
                                    <FormDescription>
                                        在更新间隔的基础上随机浮动
                                    </FormDescription>
                                </div>
                                <FormControl>
                                    <Switch
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="value_change_config.random_step"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                                <div className="space-y-0.5">
                                    <FormLabel>随机步长</FormLabel>
                                    <FormDescription>
                                        在步长的基础上随机浮动
                                    </FormDescription>
                                </div>
                                <FormControl>
                                    <Switch
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="value_change_config.reset_on_bounds"
                        render={({ field }) => (
                            <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                                <div className="space-y-0.5">
                                    <FormLabel>到达边界重置</FormLabel>
                                    <FormDescription>
                                        到达最大/最小值时重置到另一端
                                    </FormDescription>
                                </div>
                                <FormControl>
                                    <Switch
                                        checked={field.value}
                                        onCheckedChange={field.onChange}
                                    />
                                </FormControl>
                            </FormItem>
                        )}
                    />
                </div>
            </CardContent>
        </Card>
    );
}

// 离散变化配置表单
function DiscreteChangeConfig({ form }: { form: any }) {
    return (
        <Card>
            <CardContent className="pt-6 space-y-4">
                <FormField
                    control={form.control}
                    name="value_change_config.values"
                    render={({ field }) => (
                        <FormItem>
                            <FormLabel>值列表 (每行一个值)</FormLabel>
                            <FormControl>
                                <Textarea
                                    {...field}
                                    value={Array.isArray(field.value) ? field.value.join('\n') : field.value}
                                    onChange={e => field.onChange(e.target.value.split('\n'))}
                                />
                            </FormControl>
                            <FormMessage />
                        </FormItem>
                    )}
                />
                <div className="grid grid-cols-1 gap-4">
                    <FormField
                        control={form.control}
                        name="value_change_config.update_interval"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>更新间隔 (毫秒)</FormLabel>
                                <FormControl>
                                    <Input type="number" min="100" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>
                <FormField
                    control={form.control}
                    name="value_change_config.random_interval"
                    render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                            <div className="space-y-0.5">
                                <FormLabel>随机更新间隔</FormLabel>
                                <FormDescription>
                                    在更新间隔的基础上随机浮动
                                </FormDescription>
                            </div>
                            <FormControl>
                                <Switch
                                    checked={field.value}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                        </FormItem>
                    )}
                />
            </CardContent>
        </Card>
    );
}

// 随机变化配置表单
function RandomChangeConfig({ form }: { form: any }) {
    return (
        <Card>
            <CardContent className="pt-6 space-y-4">
                <div className="grid grid-cols-2 gap-4">
                    <FormField
                        control={form.control}
                        name="value_change_config.min_value"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>最小值</FormLabel>
                                <FormControl>
                                    <Input type="number" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                    <FormField
                        control={form.control}
                        name="value_change_config.max_value"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>最大值</FormLabel>
                                <FormControl>
                                    <Input type="number" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>
                <div className="grid grid-cols-1 gap-4">
                    <FormField
                        control={form.control}
                        name="value_change_config.update_interval"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>更新间隔 (毫秒)</FormLabel>
                                <FormControl>
                                    <Input type="number" min="100" {...field} />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                </div>
                <FormField
                    control={form.control}
                    name="value_change_config.random_interval"
                    render={({ field }) => (
                        <FormItem className="flex flex-row items-center justify-between rounded-lg border p-3 shadow-sm">
                            <div className="space-y-0.5">
                                <FormLabel>随机更新间隔</FormLabel>
                                <FormDescription>
                                    在更新间隔的基础上随机浮动
                                </FormDescription>
                            </div>
                            <FormControl>
                                <Switch
                                    checked={field.value}
                                    onCheckedChange={field.onChange}
                                />
                            </FormControl>
                        </FormItem>
                    )}
                />
            </CardContent>
        </Card>
    );
}

// 获取默认配置
const getDefaultConfig = (type: string, dataType: string) => {
    switch (type) {
        case 'linear':
            return {
                min_value: 0,
                max_value: 100,
                update_interval: 1000,
                step_size: 1,
                random_interval: false,
                random_step: false,
                reset_on_bounds: true,
            };
            
        case 'discrete':
            return {
                values: [],
                update_interval: 1000,
                random_interval: false,
            };
            
        case 'random':
            return {
                min_value: 0,
                max_value: 100,
                update_interval: 1000,
                random_interval: false,
            };
            
        case 'conditional':
            if (dataType === 'DATETIME') {
                return {
                    trigger_node_id: '',
                    trigger_value: '',
                    change_value: 'CURRENT_TIME', // 使用CURRENT_TIME关键字
                };
            }
            return {
                trigger_node_id: '',
                trigger_value: '',
                change_value: '',
            };
            
        default:
            return null;
    }
};

// 条件变化配置表单
function ConditionalChangeConfig({ form }: { form: any }) {
    const dataType = form.watch('data_type');
    const isDateTime = dataType === 'DATETIME';
    
    useEffect(() => {
        if (isDateTime) {
            form.setValue('value_change_config.change_value', 'CURRENT_TIME');
        }
    }, [isDateTime, form]);

    // 验证触发节点ID的格式
    const validateTriggerNodeId = (value: string) => {
        if (!value) return "触发节点ID不能为空";
        if (!isValidNodeId(value)) {
            return "触发节点ID格式无效，正确格式如：ns=2;s=node1";
        }
        return "";
    };
    
    return (
        <div className="space-y-4 border rounded-lg p-4">
            <FormField
                control={form.control}
                name="value_change_config.trigger_node_id"
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>触发节点ID</FormLabel>
                        <FormControl>
                            <Input 
                                {...field} 
                                placeholder="格式: ns=2;s=node1"
                                onChange={(e) => {
                                    field.onChange(e);
                                    const error = validateTriggerNodeId(e.target.value);
                                    if (error) {
                                        form.setError('value_change_config.trigger_node_id', {
                                            type: 'manual',
                                            message: error
                                        });
                                    } else {
                                        form.clearErrors('value_change_config.trigger_node_id');
                                    }
                                }}
                            />
                        </FormControl>
                        <FormDescription>
                            示例格式：ns=2;s=node1 或 ns=2;i=1234
                        </FormDescription>
                        <FormMessage />
                    </FormItem>
                )}
            />
            <FormField
                control={form.control}
                name="value_change_config.trigger_value"
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>触发值</FormLabel>
                        <FormControl>
                            <Input {...field} placeholder="输入触发条件的值" />
                        </FormControl>
                        <FormMessage />
                    </FormItem>
                )}
            />
            <FormField
                control={form.control}
                name="value_change_config.change_value"
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>变化值</FormLabel>
                        <FormControl>
                            {isDateTime ? (
                                <div className="text-sm text-muted-foreground p-2 bg-gray-50 rounded-md">
                                    将使用发时的当前时间
                                </div>
                            ) : (
                                <Input {...field} placeholder="输入固定值或计算表达式" />
                            )}
                        </FormControl>
                        {!isDateTime && (
                            <div className="text-sm text-muted-foreground mt-2">
                                <div className="mb-2">支持以下计算表达式：</div>
                                <div className="bg-gray-50 p-3 rounded-md space-y-3">
                                    <div>
                                        <div className="font-medium mb-1">可用变量：</div>
                                        <ul className="list-disc list-inside space-y-1">
                                            <li><code className="bg-gray-100 px-1 rounded">trigger_value</code> - 触发节点的值</li>
                                            <li><code className="bg-gray-100 px-1 rounded">current_value</code> - 当前节点的值</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <div className="font-medium mb-1">支持的运算：</div>
                                        <ul className="list-disc list-inside space-y-1">
                                            <li><code className="bg-gray-100 px-1 rounded">+</code> 加法</li>
                                            <li><code className="bg-gray-100 px-1 rounded">-</code> 减法</li>
                                            <li><code className="bg-gray-100 px-1 rounded">*</code> 乘法</li>
                                            <li><code className="bg-gray-100 px-1 rounded">/</code> 除法</li>
                                            <li><code className="bg-gray-100 px-1 rounded">%</code> 取余</li>
                                            <li><code className="bg-gray-100 px-1 rounded">**</code> 幂运算</li>
                                        </ul>
                                    </div>
                                    <div>
                                        <div className="font-medium mb-1">示例：</div>
                                        <ul className="list-disc list-inside space-y-1">
                                            <li><code className="bg-gray-100 px-1 rounded">trigger_value + 10</code> - 触发值加10</li>
                                            <li><code className="bg-gray-100 px-1 rounded">current_value * 2</code> - 当前值乘2</li>
                                            <li><code className="bg-gray-100 px-1 rounded">trigger_value * 0.5 + current_value</code> - 触发值的一半加上当前值</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        )}
                        <FormMessage />
                    </FormItem>
                )}
            />
        </div>
    );
}

// 根据数类型获可用的变化类型选项
const getValueChangeOptions = (dataType: string) => {
    const baseOption = { value: 'none', label: '不自动变化' };
    const conditionalOption = { value: 'conditional', label: '条件变化' };
    const discreteOption = { value: 'discrete', label: '离散值变化' };
    const linearOption = { value: 'linear', label: '线性变化' };
    const randomOption = { value: 'random', label: '随机变化' };

    switch (dataType) {
        case 'BOOL':
        case 'DATETIME':
            return [baseOption, conditionalOption];
            
        case 'CHAR':
        case 'STRING':
        case 'BYTESTRING':
            return [baseOption, discreteOption, conditionalOption];
            
        case 'UINT16':
        case 'UINT32':
        case 'UINT64':
        case 'INT32':
        case 'INT64':
        case 'FLOAT':
        case 'DOUBLE':
            return [baseOption, linearOption, discreteOption, randomOption, conditionalOption];
            
        default:
            return [baseOption];
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

    // 加载服务器表
    useEffect(() => {
        const fetchServers = async () => {
            try {
                const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL}/servers`);
                if (!response.ok) throw new Error('加载服务器列表失败');
                const data = await response.json();
                setServers(data);
            } catch (error) {
                console.error('加载服务器列表失败:', error);
                toast.error('加载服���器列表失败');
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
                (node_id) => {
                    if (!nodeId) { // 创建新节点时检查
                        return !existingNodeIds.has(node_id);
                    }
                    return node_id === initialNodeId || !existingNodeIds.has(node_id);
                },
                {
                    message: "此节点ID已被使用"
                }
            )
            .refine(
                isValidNodeId,
                {
                    message: "节点ID格式无效"
                }
            ),
        data_type: z.enum(dataTypes.map(dt => dt.value) as [string, ...string[]]),
        access_level: z.enum(accessLevels.map(al => al.value) as [string, ...string[]]),
        description: z.string().optional(),
        initial_value: z.string().optional(),
        value_change_type: z.enum(valueChangeOptions.map(vc => vc.value) as [string, ...string[]]),
        value_change_config: z.any().optional(),
        value_precision: z.number().min(0).max(10).optional(),
        serverIds: z.array(z.number()).optional(),
    });

    const form = useForm<z.infer<typeof formSchema>>({
        resolver: zodResolver(formSchema),
        defaultValues: {
            name: "",
            node_id: "",
            data_type: "STRING",
            access_level: "READWRITE",
            description: "",
            initial_value: "",
            value_change_type: "none",
            value_change_config: null,
            value_precision: 2,
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
                        
                        // 将后端返回的值变化类型转换为小写
                        const valueChangeType = nodeData.value_change_type?.toLowerCase() || 'none';
                        console.log('原始值变化类型:', nodeData.value_change_type);
                        console.log('转换后的值变化类型:', valueChangeType);
                        
                        // 设置表单初始值，包括服务器关联
                        const formData = {
                            name: nodeData.name || '',
                            node_id: nodeData.node_id || '',
                            data_type: nodeData.data_type || 'STRING',
                            access_level: nodeData.access_level || 'READWRITE',
                            description: nodeData.description || '',
                            initial_value: nodeData.initial_value || '',
                            value_change_type: valueChangeType,
                            value_change_config: nodeData.value_change_config || null,
                            value_precision: nodeData.value_precision ?? 2,
                            serverIds: nodeData.servers?.map(server => server.id) || [],
                        };
                        
                        console.log('加载节点数据:', formData);
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

    // 监听值变化类型的变化
    useEffect(() => {
        const subscription = form.watch((value, { name }) => {
            if (name === 'value_change_type') {
                console.log('值变化类型改变:', value.value_change_type);
                form.setValue('value_change_config', getDefaultConfig(value.value_change_type, form.watch('data_type')));
            }
        });
        return () => subscription.unsubscribe();
    }, [form]);

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

    // 修改初始值输入控件的渲染逻辑
    const renderInitialValueInput = (dataType: string, field: any) => {
        // 如果是日期时间类型，只显示提示信息
        if (dataType === 'DATETIME') {
            return (
                <div className="text-sm text-muted-foreground p-2 bg-gray-50 rounded-md">
                    将使用当前时间作为初始值
                </div>
            );
        }

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

    // 修改表单中的初始值字段渲染
    const renderInitialValueField = () => {
        const dataType = form.watch('data_type');
        
        return (
            <FormField
                control={form.control}
                name="initial_value"
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>初始值</FormLabel>
                        <FormControl>
                            {renderInitialValueInput(dataType, field)}
                        </FormControl>
                        {dataType !== 'DATETIME' && (
                            <FormDescription>
                                请输入与所选数据类型匹配的初始值
                            </FormDescription>
                        )}
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    };

    // 渲染数据类型选择器
    const renderDataTypeSelect = () => (
        <FormField
            control={form.control}
            name="data_type"
            render={({ field }) => (
                <FormItem>
                    <FormLabel>数据类型</FormLabel>
                    <Select 
                        onValueChange={(value) => {
                            field.onChange(value);
                            // 当数据类型改变时，重置值变化类型为"不自动变化"
                            form.setValue('value_change_type', 'none');
                            form.setValue('value_change_config', null);
                            
                            // 如果是日期时间类型，清空初始值
                            if (value === 'DATETIME') {
                                form.setValue('initial_value', '');
                            }
                        }}
                        defaultValue={field.value}
                        value={field.value}
                    >
                        <FormControl>
                            <SelectTrigger>
                                <SelectValue placeholder="选择数据类型" />
                            </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                            {dataTypes.map((type) => (
                                <SelectItem key={type.value} value={type.value}>
                                    {type.label}
                                </SelectItem>
                            ))}
                        </SelectContent>
                    </Select>
                    <FormMessage />
                </FormItem>
            )}
        />
    );

    // 渲染值变化类型选择器
    const renderValueChangeTypeSelect = () => {
        const dataType = form.watch('data_type');
        const options = getValueChangeOptions(dataType);
        
        return (
            <FormField
                control={form.control}
                name="value_change_type"
                render={({ field }) => (
                    <FormItem>
                        <FormLabel>值变化类型</FormLabel>
                        <Select
                            onValueChange={(value) => {
                                field.onChange(value);
                                // 更新配置时同时传入数据类型
                                form.setValue('value_change_config', getDefaultConfig(value, dataType));
                            }}
                            value={field.value}
                        >
                            <FormControl>
                                <SelectTrigger>
                                    <SelectValue placeholder="选择值变化类型" />
                                </SelectTrigger>
                            </FormControl>
                            <SelectContent>
                                {options.map((option) => (
                                    <SelectItem key={option.value} value={option.value}>
                                        {option.label}
                                    </SelectItem>
                                ))}
                            </SelectContent>
                        </Select>
                        <FormMessage />
                    </FormItem>
                )}
            />
        );
    };

    // 渲值变化配置表单
    const renderValueChangeConfig = () => {
        const type = form.watch('value_change_type');
        const dataType = form.watch('data_type');

        // 只有数值类型才显示精度设置
        const showPrecision = ['FLOAT', 'DOUBLE'].includes(dataType);

        if (type === 'none') {
            return null;
        }

        return (
            <div className="space-y-4">
                {showPrecision && (
                    <FormField
                        control={form.control}
                        name="value_precision"
                        render={({ field }) => (
                            <FormItem>
                                <FormLabel>数值精度 (小数位数)</FormLabel>
                                <FormControl>
                                    <Input
                                        type="number"
                                        min={0}
                                        max={10}
                                        {...field}
                                        onChange={e => field.onChange(parseInt(e.target.value))}
                                    />
                                </FormControl>
                                <FormMessage />
                            </FormItem>
                        )}
                    />
                )}
                {type === 'linear' && <LinearChangeConfig form={form} />}
                {type === 'discrete' && <DiscreteChangeConfig form={form} />}
                {type === 'random' && <RandomChangeConfig form={form} />}
                {type === 'conditional' && <ConditionalChangeConfig form={form} />}
            </div>
        );
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

    const onSubmit = async (data: z.infer<typeof formSchema>) => {
        try {
            setIsSubmitting(true);
            
            // 准备提交数据
            const submitData = {
                name: data.name,
                node_id: data.node_id,
                data_type: data.data_type,
                access_level: data.access_level,
                description: data.description,
                // 对于 DATETIME 类型，完全不提交 initial_value 字段
                ...(data.data_type !== 'DATETIME' && { initial_value: data.initial_value }),
                value_change_type: data.value_change_type.toLowerCase(),
                value_change_config: data.value_change_type === 'none' ? null : {
                    ...data.value_change_config,
                    // 确保数值字段为数值类型
                    ...(data.value_change_type === 'linear' && {
                        min_value: Number(data.value_change_config?.min_value),
                        max_value: Number(data.value_change_config?.max_value),
                        update_interval: Number(data.value_change_config?.update_interval),
                        step_size: Number(data.value_change_config?.step_size),
                    }),
                    ...(data.value_change_type === 'random' && {
                        min_value: Number(data.value_change_config?.min_value),
                        max_value: Number(data.value_change_config?.max_value),
                        update_interval: Number(data.value_change_config?.update_interval),
                    }),
                    ...(data.value_change_type === 'discrete' && {
                        update_interval: Number(data.value_change_config?.update_interval),
                        values: Array.isArray(data.value_change_config?.values) 
                            ? data.value_change_config.values.filter((v: string) => v.trim() !== '')
                            : []
                    }),
                    ...(data.value_change_type === 'conditional' && {
                        trigger_node_id: data.value_change_config?.trigger_node_id,
                        trigger_value: data.value_change_config?.trigger_value,
                        change_value: data.data_type === 'DATETIME' ? 'CURRENT_TIME' : data.value_change_config?.change_value
                    })
                },
                // 如果不是浮点数类型清空精度设置
                value_precision: ['FLOAT', 'DOUBLE'].includes(data.data_type) ? data.value_precision : null,
                // 确保 serverIds 是数组
                serverIds: Array.from(tempSelectedServers)
            };

            console.log('提交数据:', submitData);

            if (nodeId) {
                // 更新节点
                await updateNode(nodeId, submitData);
                toast.success('节点更新成功');
            } else {
                // 创建节点
                if (isBatchMode) {
                    // 批量创建逻辑
                    const { name, node_id } = submitData;
                    const namePattern = parsePlaceholderPattern(name);
                    const nodeIdPattern = parsePlaceholderPattern(node_id);

                    if (!namePattern.hasPlaceholder && !nodeIdPattern.hasPlaceholder) {
                        throw new Error('批量创建模式下，节点名称或节点ID必须包含占位符 {n}');
                    }

                    const names = generateBatchNames(name, batchCount);
                    const nodeIds = generateBatchNames(node_id, batchCount);

                    const createPromises = names.map((name, index) => {
                        const batchData = {
                            ...submitData,
                            name,
                            node_id: nodeIds[index],
                        };
                        return createNode(batchData);
                    });

                    await Promise.all(createPromises);
                    toast.success(`成功创建 ${batchCount} 个节点`);
                } else {
                    // 单个节点创建
                    try {
                        await createNode(submitData);
                        toast.success('节点创建成功');
                    } catch (error) {
                        if (error instanceof Error) {
                            toast.error(error.message);
                            return;
                        }
                        toast.error('创建节点失败');
                        return;
                    }
                }
            }

            router.refresh();
            router.push('/nodes');
        } catch (error) {
            console.error('保存节点失败:', error);
            if (error instanceof Error) {
                toast.error(error.message);
            } else {
                toast.error('保存节点失败');
            }
        } finally {
            setIsSubmitting(false);
        }
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

                {renderDataTypeSelect()}
                {renderInitialValueField()}

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

                {renderValueChangeTypeSelect()}

                {renderValueChangeConfig()}

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