// Server types
export interface OPCUAServer {
    id: number;
    name: string;
    endpoint: string;
    created_at: string;
    updated_at: string | null;
    nodes: Node[];
}

export interface CreateServerDto {
    name: string;
    endpoint: string;
    nodeIds?: number[];
}

export interface UpdateServerDto {
    name?: string;
    endpoint?: string;
    nodeIds?: number[];
}

// Node types
export interface Node {
    id: number;
    name: string;
    node_id: string;
    data_type: string;
    access_level: string;
    description?: string;
    created_at: string;
    updated_at: string | null;
    servers: OPCUAServer[];
}

export interface CreateNodeDto {
    name: string;
    node_id: string;
    data_type: string;
    access_level: string;
    description?: string;
}

export interface UpdateNodeDto {
    name?: string;
    node_id?: string;
    data_type?: string;
    access_level?: string;
    description?: string;
} 