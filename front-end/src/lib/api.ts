import { CreateNodeDto, CreateServerDto, Node, OPCUAServer, UpdateNodeDto, UpdateServerDto, PaginatedNodes } from '@/types';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

const DEFAULT_TIMEOUT = 30000; // 增加到30秒

const defaultHeaders = {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
};

async function fetchWithTimeout(url: string, options: RequestInit = {}, timeout = DEFAULT_TIMEOUT): Promise<Response> {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);

    try {
        const response = await fetch(url, {
            ...options,
            headers: {
                ...defaultHeaders,
                ...options.headers,
            },
            signal: controller.signal,
        });
        clearTimeout(id);
        return response;
    } catch (error) {
        clearTimeout(id);
        if (error instanceof Error) {
            if (error.name === 'AbortError') {
                throw new Error('请求超时，请检查网络连接或稍后重试');
            }
        }
        throw error;
    }
}

// Server API functions
export async function getServers(): Promise<OPCUAServer[]> {
    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/servers/`);
        if (!response.ok) {
            throw new Error('获取服务器列表失败');
        }
        return response.json();
    } catch (error) {
        console.error('获取服务器列表失败:', error);
        return [];
    }
}

export async function getServer(id: number): Promise<OPCUAServer | null> {
    try {
        const response = await fetchWithTimeout(
            `${API_BASE_URL}/servers/${id}`,
            {},
            30000 // 30秒超时
        );

        if (!response.ok) {
            if (response.status === 404) {
                console.log(`服务器 ${id} 不存在`);
                return null;
            }

            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || '获取服务器详情失败';
            console.error('获取服务器详情失败:', {
                status: response.status,
                statusText: response.statusText,
                error: errorMessage
            });
            throw new Error(errorMessage);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        if (error instanceof Error) {
            console.error('获取服务器详情失败:', error.message);
            throw new Error(`获取服务器详情失败: ${error.message}`);
        }
        console.error('获取服务器详情失败:', error);
        throw new Error('获取服务器详情失败: 未知错误');
    }
}

export async function createServer(data: CreateServerDto): Promise<OPCUAServer> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/servers/`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        throw new Error('创建服务器失败');
    }
    return response.json();
}

export async function updateServer(id: number, data: UpdateServerDto): Promise<OPCUAServer> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/servers/${id}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
    });
    if (!response.ok) {
        throw new Error('更新服务器失败');
    }
    return response.json();
}

export async function deleteServer(id: number): Promise<void> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/servers/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        throw new Error('删除服务器失败');
    }
}

// Node API functions
export async function getNodes(page: number = 1, pageSize: number = 10): Promise<PaginatedNodes> {
    try {
        const skip = (page - 1) * pageSize;
        const response = await fetchWithTimeout(
            `${API_BASE_URL}/nodes/?skip=${skip}&limit=${pageSize}`,
            {},
            60000  // 为节点列表特别设置60秒超时
        );
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error('获取节点列表失败:', {
                status: response.status,
                statusText: response.statusText,
                error: errorData
            });
            throw new Error('获取节点列表失败');
        }
        
        const data = await response.json();
        console.log('API 返回数据:', data);
        
        // 确保返回的数据符合分页格式
        if (!data.items || typeof data.total !== 'number') {
            console.error('API 返回的数据格式不正确:', data);
            return {
                items: [],
                total: 0,
                page: 1,
                size: pageSize,
                pages: 1
            };
        }
        
        return {
            items: data.items,
            total: data.total,
            page: data.page || page,
            size: data.size || pageSize,
            pages: data.pages || Math.ceil(data.total / pageSize)
        };
    } catch (error) {
        console.error('获取节点列表失败:', error);
        return {
            items: [],
            total: 0,
            page: 1,
            size: pageSize,
            pages: 1
        };
    }
}

export async function getNode(id: number): Promise<Node | null> {
    try {
        const response = await fetchWithTimeout(
            `${API_BASE_URL}/nodes/${id}`,
            {},
            30000 // 30秒超时
        );

        if (!response.ok) {
            if (response.status === 404) {
                console.log(`节点 ${id} 不存在`);
                return null;
            }

            const errorData = await response.json().catch(() => ({}));
            const errorMessage = errorData.detail || '获取节点详情失败';
            console.error('获取节点详情失败:', {
                status: response.status,
                statusText: response.statusText,
                error: errorMessage
            });
            throw new Error(errorMessage);
        }

        const data = await response.json();
        return data;
    } catch (error) {
        if (error instanceof Error) {
            console.error('获取节点详情失败:', error.message);
            throw new Error(`获取节点详情失败: ${error.message}`);
        }
        console.error('获取节点详情失败:', error);
        throw new Error('获取节点详情失败: 未知错误');
    }
}

export async function createNode(data: any): Promise<Node> {
    try {
        console.log('创建节点请求数据:', data);
        const response = await fetchWithTimeout(`${API_BASE_URL}/nodes/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('服务器响应错误:', {
                status: response.status,
                statusText: response.statusText,
                errorData
            });
            
            // 处理验证错误
            if (response.status === 422 && errorData.detail) {
                if (Array.isArray(errorData.detail)) {
                    // 如果是数组形式的错误信息，转换为更友好的格式
                    const errorMessages = errorData.detail.map((error: any) => {
                        const field = error.loc[error.loc.length - 1];
                        return `${field}: ${error.msg}`;
                    });
                    throw new Error(errorMessages.join('\n'));
                } else if (typeof errorData.detail === 'string') {
                    throw new Error(errorData.detail);
                }
            }
            
            throw new Error(errorData.message || '创建节点失败');
        }

        return await response.json();
    } catch (error) {
        console.error('创建节点失败:', error);
        throw error;
    }
}

export async function updateNode(id: number, data: UpdateNodeDto): Promise<Node> {
    try {
        const response = await fetchWithTimeout(`${API_BASE_URL}/nodes/${id}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const errorData = await response.json();
            
            // 处理验证错误
            if (response.status === 422 && errorData.detail) {
                if (Array.isArray(errorData.detail)) {
                    const errorMessages = errorData.detail.map((error: any) => {
                        const field = error.loc[error.loc.length - 1];
                        return `${field}: ${error.msg}`;
                    });
                    throw new Error(errorMessages.join('\n'));
                } else if (typeof errorData.detail === 'string') {
                    throw new Error(errorData.detail);
                }
            }
            
            throw new Error(errorData.message || '更新节点失败');
        }

        return await response.json();
    } catch (error) {
        console.error('更新节点失败:', error);
        throw error;
    }
}

export async function deleteNode(id: number): Promise<void> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/nodes/${id}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        throw new Error('删除节点失败');
    }
}

// Server-Node Association APIs
export async function addNodeToServer(serverId: number, nodeId: number): Promise<OPCUAServer> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/servers/${serverId}/nodes/${nodeId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
    });
    if (!response.ok) {
        throw new Error('添加节点到服务器失败');
    }
    return response.json();
}

export async function removeNodeFromServer(serverId: number, nodeId: number): Promise<OPCUAServer> {
    const response = await fetchWithTimeout(`${API_BASE_URL}/servers/${serverId}/nodes/${nodeId}`, {
        method: 'DELETE',
    });
    if (!response.ok) {
        throw new Error('从服务器移除节点失败');
    }
    return response.json();
}

export async function startServer(id: number) {
    const response = await fetch(`${API_BASE_URL}/servers/${id}/start`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error('启动服务器失败');
    }
    return response.json();
}

export async function stopServer(id: number) {
    const response = await fetch(`${API_BASE_URL}/servers/${id}/stop`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error('停止服务器失败');
    }
    return response.json();
}

export async function restartServer(id: number) {
    const response = await fetch(`${API_BASE_URL}/servers/${id}/restart`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error('重启服务器失败');
    }
    return response.json();
} 