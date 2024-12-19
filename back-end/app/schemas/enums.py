from enum import Enum

class ServerStatus(str, Enum):
    STOPPED = "stopped"    # 服务器已停止
    STARTING = "starting"  # 服务器正在启动
    RUNNING = "running"    # 服务器正在运行
    ERROR = "error"       # 服务器出错

class DataType(str, Enum):
    UINT16 = "UINT16"
    UINT32 = "UINT32"
    UINT64 = "UINT64"
    INT32 = "INT32"
    INT64 = "INT64"
    FLOAT = "FLOAT"
    DOUBLE = "DOUBLE"
    STRING = "STRING"
    BYTESTRING = "BYTESTRING"
    CHAR = "CHAR"
    BOOL = "BOOL"
    DATETIME = "DATETIME"

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