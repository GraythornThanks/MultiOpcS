from enum import Enum

class ServerStatus(str, Enum):
    STOPPED = "stopped"    # 服务器已停止
    STARTING = "starting"  # 服务器正在启动
    RUNNING = "running"    # 服务器正在运行
    ERROR = "error"       # 服务器出错

class DataType(str, Enum):
    # 基本数值类型
    UINT16 = "UINT16"     # 16位无符号整数
    UINT32 = "UINT32"     # 32位无符号整数
    UINT64 = "UINT64"     # 64位无符号整数
    INT32 = "INT32"       # 32位有符号整数
    INT64 = "INT64"       # 64位有符号整数
    FLOAT = "FLOAT"       # 单精度浮点数
    DOUBLE = "DOUBLE"     # 双精度浮点数
    BOOL = "BOOL"         # 布尔值
    CHAR = "CHAR"         # 字符
    
    # 字符串和时间类型
    STRING = "STRING"          # 字符串
    DATETIME = "DATETIME"      # 日期时间
    BYTESTRING = "BYTESTRING"  # 字节字符串
    
    # OPC UA特定类型
    NODEID = "NODEID"              # 节点ID
    STATUSCODE = "STATUSCODE"      # 状态码
    LOCALIZEDTEXT = "LOCALIZEDTEXT" # 本地化文本
    QUALIFIEDNAME = "QUALIFIEDNAME" # 限定名称
    XMLELEMENT = "XMLELEMENT"      # XML元素
    VARIANT = "VARIANT"            # 变体类型
    DATAVALUE = "DATAVALUE"        # 数据值

class AccessLevel(str, Enum):
    READ = "READ"         # 只读
    WRITE = "WRITE"       # 只写
    READWRITE = "READWRITE"  # 读写

class ValueChangeType(str, Enum):
    NONE = "none"           # 不自动变化
    LINEAR = "linear"       # 线性变化
    DISCRETE = "discrete"   # 离散值变化
    RANDOM = "random"       # 随机变化
    CONDITIONAL = "conditional"  # 条件变化