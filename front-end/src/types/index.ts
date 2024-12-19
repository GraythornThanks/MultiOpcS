export type ServerStatus = 'stopped' | 'starting' | 'running' | 'error';

export type DataType = 
    | "UINT16"     // 16位无符号整数
    | "UINT32"     // 32位无符号整数
    | "UINT64"     // 64位无符号整数
    | "INT32"      // 32位有符号整数
    | "INT64"      // 64位有符号整数
    | "FLOAT"      // 单精度浮点数
    | "DOUBLE"     // 双精度浮点数
    | "BOOL"       // 布尔值
    | "CHAR"       // 字符
    | "STRING"     // 字符串
    | "DATETIME"   // 日期时间
    | "BYTESTRING" // 字节字符串
    | "NODEID"     // 节点ID
    | "STATUSCODE" // 状态码
    | "LOCALIZEDTEXT" // 本地化文本
    | "QUALIFIEDNAME" // 限定名称
    | "XMLELEMENT"    // XML元素
    | "VARIANT"       // 变体类型
    | "DATAVALUE";    // 数据值

export type AccessLevel = "READ" | "WRITE" | "READWRITE";

export type ValueChangeType = 'none' | 'linear' | 'discrete' | 'random' | 'conditional';

export interface ValueChangeConfig {
    min_value?: number;
    max_value?: number;
    update_interval?: number;
    step_size?: number;
    random_interval?: boolean;
    random_step?: boolean;
    reset_on_bounds?: boolean;
    values?: string[];
    trigger_node_id?: string;
    trigger_value?: string;
    change_value?: string;
}

export interface Node {
    id: number;
    name: string;
    node_id: string;
    data_type: DataType;
    access_level: AccessLevel;
    description?: string;
    initial_value?: string;
    value_change_type: ValueChangeType;
    value_change_config?: ValueChangeConfig;
    value_precision?: number;
    servers?: { id: number; name: string }[];
    created_at?: string;
    updated_at?: string;
}

export interface OPCUAServer {
    id: number;
    name: string;
    port: number;
    endpoint?: string;
    status: ServerStatus;
    last_started?: string;
    created_at: string;
    updated_at?: string;
    nodes: Node[];
}

export interface CreateNodeDto {
    name: string;
    node_id: string;
    data_type: DataType;
    access_level: AccessLevel;
    description?: string;
    initial_value?: string;
    value_change_type?: ValueChangeType;
    value_change_config?: ValueChangeConfig;
    value_precision?: number;
    serverIds?: number[];
}

export interface CreateServerDto {
    name: string;
    port: number;
    endpoint?: string;
    nodeIds?: number[];
}

export interface UpdateNodeDto {
    name?: string;
    node_id?: string;
    data_type?: DataType;
    access_level?: AccessLevel;
    description?: string;
    initial_value?: string;
    value_change_type?: ValueChangeType;
    value_change_config?: ValueChangeConfig;
    value_precision?: number;
    serverIds?: number[];
}

export interface UpdateServerDto {
    name?: string;
    port?: number;
    endpoint?: string;
    nodeIds?: number[];
}

export interface PaginatedResponse<T> {
    items: T[];
    total: number;
    page: number;
    size: number;
    pages: number;
}

export type PaginatedNodes = PaginatedResponse<Node>;

export interface ServerStatusData {
    id: number;
    status: ServerStatus;
    last_started: string | null;
}

export interface ServerStatusUpdate {
    type: 'server_status' | 'initial_status';
    data: ServerStatusData | ServerStatusData[];
}

export interface WebSocketMessage {
    type: string;
    data: any;
}

export interface WebSocketError {
    code: number;
    reason: string;
}
