# Python \+ MySQL 项目设计（V2\.0）

# Python \+ MySQL 项目设计文档 V2\.0（企业级完整版）

## 文档说明

本文档为**Python 对接 MySQL 企业级项目**的标准化设计规范，涵盖**项目架构、数据库设计、代码开发、生产环境适配**全维度要求，强制要求开发团队全员遵守。文档基于业务核心诉求（`fid` 主键、MD5 生成、`fec\_id`/`fproject\_id` 隔离、时间三字段）设计，补充生产环境必做的高可用、高安全、高可维护性规范，可直接作为团队开发、代码评审、联调测试的标准依据。

**文档适用范围**：项目所有开发人员、测试人员、运维人员
**核心技术栈**：Python 3\.8\+、SQLAlchemy 2\.0\+、MySQL 8\.0\+、pymysql
**设计原则**：分层解耦、安全优先、规范统一、适配生产

## 目录

1. 项目整体架构设计

2. 数据库设计规范（含最终表结构、索引、命名）

3. 核心代码开发规范（含ORM、工具类、业务层）

4. 生产环境适配规范（多环境、连接池、时区）

5. 团队开发强制红线

6. 异常处理与日志规范

7. 数据安全与权限隔离规范

# 一、项目整体架构设计

## 1\.1 架构设计原则

- **分层解耦**：严格按「配置层→基础层→模型层→工具层→业务层→入口层」划分，层间仅单向依赖，无跨层调用

- **无硬编码**：SQL、数据库账号、业务配置均不硬编码在代码中

- **ORM 优先**：全程使用 SQLAlchemy ORM 操作数据库，禁止业务代码写原生 SQL

- **可扩展**：支持后续对接 Web 框架（FastAPI/Flask）、分布式部署、多数据源

- **易维护**：统一命名、统一返回、统一异常，降低团队协作成本

## 1\.2 最终版项目目录结构

```Plaintext
project_name/
├── .env.dev                # 开发环境配置文件（git忽略）
├── .env.test               # 测试环境配置文件（git忽略）
├── .env.prod               # 生产环境配置文件（git忽略，运维单独管理）
├── config/                 # 配置层：统一加载环境变量、初始化资源
│   ├── __init__.py
│   ├── env_config.py       # 环境变量加载工具
│   └── db_config.py        # 数据库连接、会话初始化
├── db/                     # 数据库层：ORM 基类、数据模型
│   ├── __init__.py
│   ├── base.py             # 全局ORM基类（含软删除、自动过滤）
│   └── models/             # 数据模型：一张表对应一个模型文件
│       ├── __init__.py
│       └── file_info.py    # 文件信息表模型（核心示例）
├── utils/                  # 工具层：通用工具类，无业务逻辑
│   ├── __init__.py
│   ├── md5_fid_util.py     # MD5生成、fid主键生成工具
│   ├── log_util.py         # 全局日志配置工具
│   └── time_util.py        # 时间格式化、时区工具
├── service/                # 业务层：所有业务逻辑实现，仅依赖模型和工具
│   ├── __init__.py
│   └── file_service.py     # 文件相关业务逻辑（新增、删除、查询等）
├── main.py                 # 项目入口：测试、启动调用（Web项目可替换为main.py）
├── requirements.txt        # 项目依赖包（指定版本，避免兼容问题）
└── README.md               # 项目说明：环境搭建、启动命令、目录说明
```

## 1\.3 依赖包规范（requirements\.txt）

**指定固定版本，避免生产环境版本兼容问题**

```Plaintext
# 核心ORM框架
sqlalchemy==2.0.23
# MySQL驱动
pymysql==1.1.0
# 环境变量管理
python-dotenv==1.0.0
# 日志美化（可选，生产环境可移除）
colorlog==6.7.0
# 类型注解（提升代码可读性）
typing-extensions==4.8.0
```

# 二、数据库设计规范

## 2\.1 核心设计要求（强制）

1. 所有表**必须**包含：`fid`（主键）、`fec\_id`（企业ID）、`fproject\_id`（项目ID）

2. 所有表**必须**包含时间三字段：`create\_time`（创建）、`update\_time`（更新）、`delete\_time`（删除）

3. 所有表**必须**实现**软删除**：通过 `is\_deleted` 标记，禁止物理删除数据

4. 涉及文件/唯一标识的表**必须**包含 `md5` 字段（32位固定），用于校验/去重

5. 所有字段**必须**明确长度，禁止使用 `TEXT`/`VARCHAR\(MAX\)` 等无限制类型

6. 所有表**必须**添加合理索引，避免慢查询（主键索引、联合索引、业务索引）

7. 统一使用**InnoDB 引擎**，支持事务和行级锁

8. 字符集统一为 **utf8mb4**，支持emoji、特殊字符，避免乱码

## 2\.2 数据库命名规范（强制）

|类型|命名规则|示例|
|---|---|---|
|数据库名|小写\+下划线，业务前缀|file\_manage\_db|
|表名|t\_\+业务模块\+\_\+表含义|t\_file\_info、t\_user|
|字段名|小写\+下划线，f开头（标识字段）|fid、fec\_id、fproject\_id|
|索引名|类型\_\+表名\+\_\+字段名|uk\_fid（唯一索引）、idx\_fec\_project（普通索引）|
|主键|统一命名为 fid|fid|

**索引类型缩写**：uk=唯一索引、idx=普通索引、pri=主键索引（默认）

## 2\.3 最终版核心表结构（t\_file\_info）

### 表基础信息

- 表名：t\_file\_info

- 引擎：InnoDB

- 字符集：utf8mb4

- 排序规则：utf8mb4\_general\_ci

- 备注：文件信息核心表，存储企业\-项目下的文件元数据

### 字段详情

|字段名|字段类型|长度|约束条件|默认值|备注|非空要求|
|---|---|---|---|---|---|---|
|fid|VARCHAR|64|PRIMARY KEY（主键）|无|全局唯一主键，MD5生成|是|
|fec\_id|VARCHAR|64|无|无|企业ID，数据隔离核心|是|
|fproject\_id|VARCHAR|64|无|无|项目ID，数据隔离核心|是|
|file\_md5|VARCHAR|32|无|无|文件真实MD5，32位固定|是|
|file\_name|VARCHAR|255|无|无|文件名（含后缀）|是|
|file\_path|VARCHAR|512|无|无|文件存储路径（绝对路径）|是|
|file\_size|BIGINT|\-|无|0|文件大小，单位：字节|否|
|file\_type|VARCHAR|32|无|空字符串|文件类型（如pdf、jpg）|否|
|create\_time|DATETIME|\-|无|CURRENT\_TIMESTAMP|创建时间，自动生成|是|
|update\_time|DATETIME|\-|无|CURRENT\_TIMESTAMP ON UPDATE CURRENT\_TIMESTAMP|更新时间，自动更新|是|
|delete\_time|DATETIME|\-|无|NULL|删除时间，软删除时赋值|否|
|is\_deleted|TINYINT|1|无|0|软删除标记：0=未删 1=已删|否|

### 必加索引（强制，避免慢查询）

```SQL
-- 主键索引（默认，无需手动创建）
-- 唯一索引：fid 全局唯一
CREATE UNIQUE INDEX uk_fid ON t_file_info(fid);
-- 联合索引：企业+项目，数据隔离核心查询条件（高频）
CREATE INDEX idx_fec_project ON t_file_info(fec_id, fproject_id);
-- 普通索引：文件MD5，用于文件去重、校验（高频）
CREATE INDEX idx_file_md5 ON t_file_info(file_md5);
-- 普通索引：创建时间，用于按时间筛选、分页（高频）
CREATE INDEX idx_create_time ON t_file_info(create_time);
```

### 表创建SQL（可直接执行）

```SQL
CREATE DATABASE IF NOT EXISTS file_manage_db DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
USE file_manage_db;

DROP TABLE IF EXISTS t_file_info;
CREATE TABLE t_file_info (
    fid VARCHAR(64) NOT NULL COMMENT '全局唯一主键',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    file_md5 VARCHAR(32) NOT NULL COMMENT '文件真实MD5值',
    file_name VARCHAR(255) NOT NULL COMMENT '文件名（含后缀）',
    file_path VARCHAR(512) NOT NULL COMMENT '文件存储绝对路径',
    file_size BIGINT DEFAULT 0 COMMENT '文件大小（字节）',
    file_type VARCHAR(32) DEFAULT '' COMMENT '文件类型',
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记：0=未删 1=已删',
    PRIMARY KEY (fid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='文件信息核心表';

-- 添加索引
CREATE UNIQUE INDEX uk_fid ON t_file_info(fid);
CREATE INDEX idx_fec_project ON t_file_info(fec_id, fproject_id);
CREATE INDEX idx_file_md5 ON t_file_info(file_md5);
CREATE INDEX idx_create_time ON t_file_info(create_time);
```

## 2\.4 其他表扩展规范

若项目新增其他表（如用户表、项目表），**必须遵循以下模板**，仅替换业务字段：

```SQL
CREATE TABLE t_xxx_info (
    fid VARCHAR(64) NOT NULL COMMENT '全局唯一主键',
    fec_id VARCHAR(64) NOT NULL COMMENT '企业ID',
    fproject_id VARCHAR(64) NOT NULL COMMENT '项目ID',
    -- 以下为业务自定义字段
    xxx_field1 VARCHAR(64) NOT NULL COMMENT '业务字段1',
    xxx_field2 INT DEFAULT 0 COMMENT '业务字段2',
    -- 时间+软删除字段（固定，不可修改）
    create_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    update_time DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    delete_time DATETIME DEFAULT NULL COMMENT '删除时间',
    is_deleted TINYINT(1) DEFAULT 0 COMMENT '软删除标记：0=未删 1=已删',
    PRIMARY KEY (fid)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='XXX业务表';
-- 必加：企业+项目联合索引
CREATE INDEX idx_fec_project ON t_xxx_info(fec_id, fproject_id);
```

# 三、核心代码开发规范

## 3\.1 配置层开发规范

### 3\.1\.1 环境变量加载（config/env\_config\.py）

**强制**：所有配置通过 `\.env` 文件加载，禁止硬编码在代码中，支持多环境切换。

```Python
import os
from dotenv import load_dotenv
from typing import Dict, Optional

# 加载环境变量：优先从系统环境变量获取ENV，默认dev
ENV: str = os.getenv("ENV", "dev")
load_dotenv(f".env.{ENV}", override=True)

def get_env(key: str, default: Optional[str] = None) -> str:
    """
    获取环境变量，无值则抛出异常（必传）或返回默认值（可选）
    :param key: 环境变量键
    :param default: 默认值
    :return: 环境变量值
    """
    value: Optional[str] = os.getenv(key, default)
    if value is None:
        raise ValueError(f"环境变量 {key} 未配置，请检查 .env.{ENV} 文件")
    return value

# 数据库配置（统一导出，其他模块仅可导入此字典，禁止直接调用get_env）
DB_CONFIG: Dict[str, str] = {
    "host": get_env("DB_HOST"),
    "port": get_env("DB_PORT"),
    "user": get_env("DB_USER"),
    "password": get_env("DB_PASSWORD"),
    "database": get_env("DB_DATABASE"),
}

# 时区配置（强制：中国上海）
TZ_CONFIG: str = get_env("TZ", "Asia/Shanghai")
```

### 3\.1\.2 数据库连接配置（config/db\_config\.py）

**强制**：配置连接池、心跳检测、超时时间，避免生产环境连接泄漏、高并发崩溃。

```Python
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from config.env_config import DB_CONFIG
from utils.log_util import logger

# 构建MySQL连接URL
DB_URL: str = (
    f"mysql+pymysql://{DB_CONFIG['user']}:{DB_CONFIG['password']}@"
    f"{DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}?charset=utf8mb4"
)

# 创建数据库引擎：配置连接池（生产环境核心）
engine = create_engine(
    url=DB_URL,
    pool_size=10,          # 核心连接池大小：根据服务器配置调整（建议10-20）
    max_overflow=20,       # 最大溢出连接数：高并发时临时创建的连接数
    pool_recycle=3600,     # 连接回收时间：1小时，避免MySQL断开无效连接
    pool_pre_ping=True,    # 心跳检测：执行SQL前检查连接有效性，自动重连
    connect_args={
        "connect_timeout": 5,  # 连接超时时间：5秒，避免阻塞
        "charset": "utf8mb4"
    },
    echo=False,            # 生产环境关闭SQL打印，开发环境可设为True
)

# 创建会话工厂：禁止自动提交、自动刷新，由业务层手动控制
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False  # 提交后不失效对象，方便后续使用
)

def get_db() -> Session:
    """
    获取数据库会话：自动创建、自动关闭，避免连接泄漏
    :return: SQLAlchemy Session
    """
    db = SessionLocal()
    try:
        yield db
        logger.info("数据库会话创建成功")
    except Exception as e:
        db.rollback()
        logger.error(f"数据库会话异常：{str(e)}", exc_info=True)
        raise
    finally:
        db.close()
        logger.info("数据库会话已关闭")
```

### 3\.1\.3 \.env 文件配置模板（\.env\.dev/\.env\.test/\.env\.prod）

**所有环境字段一致，仅值不同**，生产环境 `\.env\.prod` 由运维单独管理，禁止提交到代码仓库。

```Plaintext
# 数据库配置
DB_HOST=127.0.0.1
DB_PORT=3306
DB_USER=root
DB_PASSWORD=your_db_password
DB_DATABASE=file_manage_db
# 时区配置
TZ=Asia/Shanghai
# 日志级别：dev=DEBUG, test=INFO, prod=WARNING
LOG_LEVEL=DEBUG
```

## 3\.2 数据库层开发规范

### 3\.2\.1 全局ORM基类（db/base\.py）

**强制**：所有模型必须继承此类，实现**全局软删除自动过滤、统一字段规范**，避免开发重复编写。

```Python
from sqlalchemy import Column, DateTime, TinyInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Query
import datetime
from config.env_config import TZ_CONFIG

# 设置时区
datetime.datetime.now = lambda: datetime.datetime.now(datetime.timezone.utc).astimezone(datetime.timezone(datetime.timedelta(hours=8)))

# 基础基类：所有模型继承
Base = declarative_base()

# 业务基类：包含软删除、时间字段，所有业务模型继承此类
class BaseModel(Base):
    __abstract__ = True  # 抽象类，不生成实际表

    # 软删除+时间字段（所有表固定，不可修改）
    create_time = Column(DateTime, nullable=False, default=datetime.datetime.now, comment="创建时间")
    update_time = Column(DateTime, nullable=False, default=datetime.datetime.now, onupdate=datetime.datetime.now, comment="更新时间")
    delete_time = Column(DateTime, nullable=True, comment="删除时间")
    is_deleted = Column(TinyInteger(1), default=0, comment="软删除标记：0=未删 1=已删")

    @classmethod
    def query(cls) -> Query:
        """
        重写query方法：自动过滤已删除数据，开发无需手动写 is_deleted=0
        :return: 过滤后的Query对象
        """
        from config.db_config import engine
        from sqlalchemy.orm import Session
        db = Session(bind=engine)
        return db.query(cls).filter(cls.is_deleted == 0)
```

### 3\.2\.2 核心模型开发（db/models/file\_info\.py）

**强制**：一张表对应一个模型文件，字段与数据库完全一致，注释完整，禁止多余字段。

```Python
from sqlalchemy import Column, String, BigInteger
from db.base import BaseModel

class FileInfo(BaseModel):
    """
    文件信息表模型
    对应数据库表：t_file_info
    """
    __tablename__ = "t_file_info"
    __table_args__ = {"comment": "文件信息核心表"}

    # 主键+隔离字段（强制）
    fid = Column(String(64), primary_key=True, comment="全局唯一主键")
    fec_id = Column(String(64), nullable=False, comment="企业ID")
    fproject_id = Column(String(64), nullable=False, comment="项目ID")
    # 业务字段
    file_md5 = Column(String(32), nullable=False, comment="文件真实MD5值")
    file_name = Column(String(255), nullable=False, comment="文件名（含后缀）")
    file_path = Column(String(512), nullable=False, comment="文件存储绝对路径")
    file_size = Column(BigInteger, default=0, comment="文件大小（字节）")
    file_type = Column(String(32), default="", comment="文件类型")
```

### 3\.2\.3 模型导出（db/models/**init**\.py）

**统一导出所有模型**，方便业务层导入，避免跨文件复杂引用。

```Python
from db.models.file_info import FileInfo

__all__ = ["FileInfo"]
```

## 3\.3 工具层开发规范

### 3\.3\.1 MD5 \&amp; FID 生成工具（utils/md5\_fid\_util\.py）

**强制**：fid 全局唯一（基于UUID\+MD5），file\_md5 支持**真实文件计算**和**随机生成**，避免重复。

```Python
import hashlib
import uuid
from typing import Optional
import os
from utils.log_util import logger

def generate_random_md5() -> str:
    """
    生成随机32位MD5值（用于非文件场景的唯一标识）
    :return: 32位小写MD5字符串
    """
    random_str = str(uuid.uuid4()) + str(os.urandom(16))
    md5_obj = hashlib.md5(random_str.encode("utf-8"))
    return md5_obj.hexdigest()

def calculate_file_md5(file_path: str) -> Optional[str]:
    """
    计算文件真实MD5值（用于文件校验、去重，核心）
    :param file_path: 文件绝对路径
    :return: 32位小写MD5字符串，文件不存在返回None
    """
    if not os.path.exists(file_path):
        logger.error(f"文件不存在，无法计算MD5：{file_path}")
        return None
    try:
        md5_obj = hashlib.md5()
        with open(file_path, "rb") as f:
            while chunk := f.read(4096):
                md5_obj.update(chunk)
        return md5_obj.hexdigest()
    except Exception as e:
        logger.error(f"计算文件MD5失败：{str(e)}", exc_info=True)
        return None

def generate_fid() -> str:
    """
    生成全局唯一主键fid（64位：32位UUID+MD5 + 32位随机MD5）
    保证全球唯一，避免分布式部署时重复
    :return: 64位小写字符串
    """
    uuid_md5 = generate_random_md5()
    random_md5 = generate_random_md5()
    return uuid_md5 + random_md5
```

### 3\.3\.2 全局日志配置（utils/log\_util\.py）

**强制**：所有模块使用统一日志工具，禁止单独配置print/日志，支持多环境日志级别。

```Python
import logging
import colorlog
from config.env_config import ENV, get_env

# 获取日志级别：dev=DEBUG, test=INFO, prod=WARNING
LOG_LEVEL = get_env("LOG_LEVEL", "DEBUG")
level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# 配置日志格式
logger = logging.getLogger("project_name")
logger.setLevel(level_map[LOG_LEVEL])
logger.handlers.clear()  # 清除默认处理器，避免重复打印

# 控制台处理器（开发/测试环境）
console_handler = logging.StreamHandler()
console_handler.setLevel(level_map[LOG_LEVEL])

# 日志格式：生产环境简化，开发环境美化
if ENV == "prod":
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )
else:
    formatter = colorlog.ColoredFormatter(
        "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        log_colors={
            "DEBUG": "cyan",
            "INFO": "green",
            "WARNING": "yellow",
            "ERROR": "red",
            "CRITICAL": "bold_red"
        }
    )

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# 生产环境可添加文件处理器（按天分割日志）
if ENV == "prod":
    from logging.handlers import TimedRotatingFileHandler
    file_handler = TimedRotatingFileHandler(
        filename="logs/project.log",
        when="midnight",
        interval=1,
        backupCount=30,
        encoding="utf-8"
    )
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level_map[LOG_LEVEL])
    logger.addHandler(file_handler)

__all__ = ["logger"]
```

## 3\.4 业务层开发规范

### 3\.4\.1 核心要求（强制）

1. 所有业务逻辑**仅允许在service层实现**，禁止在入口层/模型层写业务逻辑

2. 所有数据库操作**必须加事务**，保证原子性（新增/更新/删除）

3. 所有查询**必须带上 fec\_id \+ fproject\_id**，实现数据隔离，禁止跨企业/项目查询

4. 统一返回格式，禁止直接返回模型对象，避免数据泄露

5. 所有异常必须捕获并记录日志，禁止裸奔

### 3\.4\.2 核心业务实现（service/file\_service\.py）

```Python
from sqlalchemy.orm import Session
from db.models import FileInfo
from utils.md5_fid_util import generate_fid, calculate_file_md5, generate_random_md5
from utils.log_util import logger
from typing import Dict, Optional, List
import datetime

class FileService:
    """文件业务服务类：所有文件相关业务逻辑"""
    def __init__(self, db: Session):
        self.db = db

    def _success_response(self, data: Optional[Dict] = None) -> Dict:
        """统一成功返回格式"""
        return {
            "code": 200,
            "message": "操作成功",
            "data": data or {}
        }

    def _error_response(self, message: str) -> Dict:
        """统一失败返回格式"""
        return {
            "code": 500,
            "message": message,
            "data": {}
        }

    def create_file(self, fec_id: str, fproject_id: str, file_name: str, file_path: str, file_size: int = 0) -> Dict:
        """
        新增文件记录（核心业务）
        :param fec_id: 企业ID
        :param fproject_id: 项目ID
        :param file_name: 文件名（含后缀）
        :param file_path: 文件绝对路径
        :param file_size: 文件大小（字节）
        :return: 统一返回格式
        """
        try:
            # 1. 开启事务
            self.db.begin()
            # 2. 生成主键fid
            fid = generate_fid()
            # 3. 计算文件真实MD5（文件不存在则生成随机MD5）
            file_md5 = calculate_file_md5(file_path) or generate_random_md5()
            # 4. 提取文件类型
            file_type = file_name.split(".")[-1] if "." in file_name else ""
            # 5. 构建模型对象
            file_obj = FileInfo(
                fid=fid,
                fec_id=fec_id,
                fproject_id=fproject_id,
                file_md5=file_md5,
                file_name=file_name,
                file_path=file_path,
                file_size=file_size,
                file_type=file_type
            )
            # 6. 入库
            self.db.add(file_obj)
            self.db.commit()
            self.db.refresh(file_obj)
            # 7. 构造返回数据（仅返回必要字段，禁止返回全量）
            return_data = {
                "fid": file_obj.fid,
                "fec_id": file_obj.fec_id,
                "fproject_id": file_obj.fproject_id,
                "file_name": file_obj.file_name,
                "file_md5": file_obj.file_md5,
                "create_time": file_obj.create_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            logger.info(f"新增文件记录成功：fid={fid}, fec_id={fec_id}, fproject_id={fproject_id}")
            return self._success_response(return_data)
        except Exception as e:
            # 事务回滚
            self.db.rollback()
            error_msg = f"新增文件记录失败：{str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._error_response(error_msg)

    def delete_file(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """
        软删除文件记录（强制：禁止物理删除）
        :param fec_id: 企业ID（数据隔离）
        :param fproject_id: 项目ID（数据隔离）
        :param fid: 文件主键
        :return: 统一返回格式
        """
        try:
            self.db.begin()
            # 必须带企业+项目过滤，避免删错其他企业数据
            file_obj = self.db.query(FileInfo).filter(
                FileInfo.fid == fid,
                FileInfo.fec_id == fec_id,
                FileInfo.fproject_id == fproject_id,
                FileInfo.is_deleted == 0
            ).first()
            if not file_obj:
                return self._error_response(f"文件记录不存在：fid={fid}")
            # 软删除：更新标记和删除时间
            file_obj.is_deleted = 1
            file_obj.delete_time = datetime.datetime.now()
            self.db.commit()
            logger.info(f"软删除文件记录成功：fid={fid}, fec_id={fec_id}")
            return self._success_response({"fid": fid})
        except Exception as e:
            self.db.rollback()
            error_msg = f"删除文件记录失败：{str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._error_response(error_msg)

    def get_file_by_fid(self, fec_id: str, fproject_id: str, fid: str) -> Dict:
        """
        根据fid查询文件记录（带数据隔离）
        :param fec_id: 企业ID
        :param fproject_id: 项目ID
        :param fid: 文件主键
        :return: 统一返回格式
        """
        try:
            # BaseModel.query 已自动过滤is_deleted=0
            file_obj = FileInfo.query.filter(
                FileInfo.fid == fid,
                FileInfo.fec_id == fec_id,
                FileInfo.fproject_id == fproject_id
            ).first()
            if not file_obj:
                return self._error_response(f"文件记录不存在：fid={fid}")
            return_data = {
                "fid": file_obj.fid,
                "fec_id": file_obj.fec_id,
                "fproject_id": file_obj.fproject_id,
                "file_name": file_obj.file_name,
                "file_path": file_obj.file_path,
                "file_md5": file_obj.file_md5,
                "file_size": file_obj.file_size,
                "file_type": file_obj.file_type,
                "create_time": file_obj.create_time.strftime("%Y-%m-%d %H:%M:%S"),
                "update_time": file_obj.update_time.strftime("%Y-%m-%d %H:%M:%S")
            }
            return self._success_response(return_data)
        except Exception as e:
            error_msg = f"查询文件记录失败：{str(e)}"
            logger.error(error_msg, exc_info=True)
            return self._error_response(error_msg)
```

## 3\.5 项目入口层开发规范（main\.py）

**入口层仅做初始化和调用，禁止写业务逻辑**，Web项目可替换为FastAPI/Flask的路由层。

```Python
from config.db_config import get_db
from service.file_service import FileService
from db.base import Base
from config.db_config import engine
from utils.log_util import logger

# 首次运行初始化数据库：创建所有表（仅执行一次，生产环境由运维执行SQL）
def init_db():
    Base.metadata.create_all(bind=engine)
    logger.info("数据库表初始化成功")

if __name__ == "__main__":
    # 初始化数据库（首次运行取消注释）
    # init_db()
    # 获取数据库会话
    db = next(get_db())
    # 初始化业务服务
    file_service = FileService(db)

    # 测试新增文件
    create_res = file_service.create_file(
        fec_id="enterprise_1001",
        fproject_id="project_2001",
        file_name="测试文件.pdf",
        file_path="/data/file/测试文件.pdf",
        file_size=102400
    )
    print("新增文件结果：", create_res)

    # 测试查询文件
    if create_res["code"] == 200:
        fid = create_res["data"]["fid"]
        get_res = file_service.get_file_by_fid(
            fec_id="enterprise_1001",
            fproject_id="project_2001",
            fid=fid
        )
        print("查询文件结果：", get_res)

    # 测试删除文件
    # if create_res["code"] == 200:
    #     fid = create_res["data"]["fid"]
    #     delete_res = file_service.delete_file(
    #         fec_id="enterprise_1001",
    #         fproject_id="project_2001",
    #         fid=fid
    #     )
    #     print("删除文件结果：", delete_res)
```

# 四、生产环境适配规范

## 4\.1 多环境部署规范（强制）

1. 开发环境（dev）：本地开发，数据库为本地/测试库，日志级别DEBUG，开启SQL打印

2. 测试环境（test）：测试人员使用，数据库为测试库，日志级别INFO，关闭SQL打印

3. 生产环境（prod）：线上运行，数据库为生产库，日志级别WARNING，关闭所有调试信息

4. 环境切换：通过**系统环境变量 ENV** 控制，如 `export ENV=prod \&amp;\&amp; python main\.py`

5. 生产环境**禁止**在代码中执行 `init\_db\(\)`，表创建由运维通过SQL脚本执行，避免误删数据

## 4\.2 数据库生产环境配置（运维配合）

1. MySQL 配置 `default\-time\-zone = \&\#39;\+8:00\&\#39;`，统一时区为中国上海

2. 开启MySQL慢查询日志，阈值设置为1秒，定期排查慢查询

3. 为项目创建**独立MySQL账号**，仅赋予对应数据库的增删改查权限，禁止使用root账号

4. 配置MySQL主从复制，实现数据备份，避免数据丢失

5. 定期优化表结构，清理无效索引，避免索引膨胀

## 4\.3 Python 生产环境部署规范

1. 使用**虚拟环境**（venv/conda），隔离项目依赖，避免系统环境冲突

2. 使用**Gunicorn/uWSGI** 作为WSGI服务器，替代直接运行python main\.py，支持多进程、守护进程

3. 配置**进程守护**（如supervisor），保证项目挂掉后自动重启

4. 日志按天分割，保留30天，定期清理，避免磁盘占满

5. 禁止在生产环境打印调试信息，禁止暴露数据库账号、密码等敏感信息

## 4\.4 连接池与并发规范

1. 生产环境根据服务器CPU/内存配置调整连接池大小（`pool\_size=10\-20`，`max\_overflow=20\-30`）

2. 禁止长时间持有数据库会话，查询/操作完成后立即释放

3. 高并发场景（如文件批量上传）使用**异步ORM（SQLAlchemy AsyncIO）**，避免阻塞

# 五、团队开发强制红线

**以下规则为强制要求，代码评审发现违反直接打回，禁止合入代码仓库**

1. ❌ 禁止在业务代码中硬编码SQL、数据库账号、密码、业务配置

2. ❌ 禁止物理删除数据，所有删除操作必须为软删除

3. ❌ 禁止查询时省略 `fec\_id`/`fproject\_id`，必须实现数据隔离

4. ❌ 禁止跨层调用（如业务层直接调用配置层、入口层写业务逻辑）

5. ❌ 禁止模型字段与数据库表字段不一致，禁止多余/缺失字段

6. ❌ 禁止使用 `TEXT`/`VARCHAR\(MAX\)` 等无限制字段类型，所有字符串必须明确长度

7. ❌ 禁止裸奔异常，所有异常必须捕获、记录日志并返回统一错误信息

8. ❌ 禁止直接返回模型对象给前端/调用方，必须构造返回数据，隐藏敏感字段

9. ❌ 禁止在生产环境开启SQL打印、DEBUG日志，禁止暴露调试信息

10. ❌ 禁止多个表对应一个模型文件，必须一张表一个模型文件

11. ❌ 禁止使用root账号连接生产数据库，必须使用独立权限账号

12. ❌ 禁止在代码中执行表创建/删除操作，生产环境由运维执行SQL

# 六、异常处理与日志规范

## 6\.1 异常处理规范（强制）

1. **分层捕获**：工具层捕获工具类异常，业务层捕获业务逻辑/数据库异常，入口层捕获全局异常

2. **具体捕获**：禁止使用 `except Exception` 捕获所有异常，需针对性捕获（如 `SQLAlchemyError`、`FileNotFoundError`）

3. **事务回滚**：所有数据库写操作（新增/更新/删除）的异常必须触发事务回滚

4. **统一返回**：所有异常必须返回统一错误格式（code=500\+错误信息），禁止直接抛出异常到调用方

5. **错误信息**：错误信息需清晰、具体，禁止返回无意义信息（如“操作失败”），需包含具体原因（如“文件不存在：/data/test\.pdf”）

## 6\.2 日志规范（强制）

1. **统一工具**：所有模块必须使用 `utils\.log\_util\.logger`，禁止单独配置logging/print

2. **日志级别**：按场景使用对应级别，禁止所有日志都用INFO/DEBUG

    - DEBUG：开发环境调试信息，如“数据库会话创建成功”

    - INFO：正常业务操作信息，如“新增文件记录成功：fid=xxx”

    - WARNING：非致命异常，如“文件MD5计算失败，使用随机MD5”

    - ERROR：致命异常，如“新增文件记录失败：数据库连接超时”

    - CRITICAL：严重异常，如“生产环境数据库连接失败”

3. **日志内容**：必须包含**关键标识**（如fid、fec\_id、fproject\_id）、**具体原因**、**堆栈信息**（error级别）

4. **日志落地**：生产环境日志必须落地到文件，按天分割，保留30天，支持日志检索

5. **敏感信息**：禁止在日志中打印密码、token、用户手机号等敏感信息

# 七、数据安全与权限隔离规范

## 7\.1 数据隔离核心要求（强制）

1. **维度隔离**：所有表、所有查询、所有操作必须按「企业（fec\_id）\+ 项目（fproject\_id）」隔离，禁止跨企业/项目访问数据

2. **代码强制**：业务层所有方法必须将 `fec\_id`/`fproject\_id` 作为入参，且作为查询/操作的第一过滤条件

3. **权限校验**：后续对接用户系统后，需在入口层校验用户的企业/项目权限，仅允许访问用户所属的企业/项目数据

## 7\.2 数据安全规范

1. **密码加密**：若项目涉及用户密码，必须使用**bcrypt/scrypt**加密，禁止明文存储

2. **MD5 用途**：file\_md5 仅用于文件校验/去重，禁止用于密码加密（MD5不可逆但可彩虹表破解）

3. **敏感字段**：禁止返回/打印文件路径、数据库密码、服务器地址等敏感信息

4. **SQL 注入防护**：全程使用ORM，禁止拼接原生SQL，若必须使用原生SQL，需使用参数化查询

5. **文件路径防护**：禁止直接使用用户传入的文件路径，需做路径校验，避免路径遍历攻击（如`\.\./`）

## 7\.3 备份与恢复规范

1. 生产环境数据库**每天全量备份**，每小时增量备份，备份文件保留7天

2. 备份文件存储在独立服务器，避免与生产服务器同机，防止磁盘损坏导致数据丢失

3. 定期进行备份恢复测试，确保备份文件可用

4. 重要业务数据（如文件MD5、fid）需做异地备份

# 八、文档附则

1. 本文档为项目开发**唯一标准**，所有开发人员必须严格遵守

2. 后续项目迭代、新增表/功能，必须遵循本文档的规范

3. 若需修改本文档，需经团队技术负责人、架构师审核通过后，发布新版本

4. 本文档自发布之日起生效，原有开发规范与本文档冲突的，以本文档为准

**编制人**：技术团队
**编制日期**：2026年4月
**版本**：V2\.0（企业级完整版）

> （注：文档部分内容可能由 AI 生成）
