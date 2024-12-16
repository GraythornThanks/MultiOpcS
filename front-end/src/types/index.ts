export type ServerStatus = "stopped" | "starting" | "running" | "error";

export type DataType = 
    // 数值类型
    | "Null"           // 空值
    | "Boolean"        // 布尔值
    | "SByte"         // 有符号8位整数
    | "Byte"          // 无符号8位整数
    | "Int16"         // 16位整数
    | "UInt16"        // 无符号16位整数
    | "Int32"         // 32位整数
    | "UInt32"        // 无符号32位整数
    | "Int64"         // 64位整数
    | "UInt64"        // 无符号64位整数
    | "Float"         // 32位浮点数
    | "Double"        // 64位浮点数
    
    // 字符串类型
    | "String"        // 字符串
    | "DateTime"      // 日期时间
    | "ByteString"    // 字节字符串
    
    // 复杂类型
    | "XmlElement"    // XML元素
    | "NodeId"        // 节点ID
    | "StatusCode"    // 状态码
    | "LocalizedText" // 本地化文本
    | "QualifiedName" // 限定名称
    | "Variant"       // 变体类型
    | "DataValue";    // 数据值

export type AccessLevel = "READ" | "WRITE" | "READWRITE";

export interface Node {
    id: number;
    name: string;
    node_id: string;
    data_type: string;
    access_level: string;
    description?: string;
    initial_value?: string;
    value_change_type: 'none' | 'linear' | 'discrete' | 'random' | 'conditional';
    value_change_config?: any;
    value_precision?: number;
    servers?: { id: number; name: string }[];
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
}

export interface CreateServerDto {
    name: string;
    port: number;
    endpoint?: string;
    nodeIds?: number[];
}

export interface UpdateNodeDto {
    name: string;
    node_id: string;
    data_type: string;
    access_level: string;
    description?: string;
    initial_value?: string;
    value_change_type: 'none' | 'linear' | 'discrete' | 'random' | 'conditional';
    value_change_config?: any;
    value_precision?: number;
    serverIds: number[];
}

export interface UpdateServerDto {
    name?: string;
    port?: number;
    endpoint?: string;
    nodeIds?: number[];
} 