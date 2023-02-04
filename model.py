from dataclasses import field
from pathlib import Path

import kayaku
from kayaku import config

kayaku.initialize({"{**}": "./config/{**}"})


@config("config")
class EricConfig:
    """Eric 配置"""

    name: str
    """ 机器人名称 """

    accounts: list[int]
    """ 机器人账号 """

    default_account: int
    """ 默认账号 """

    host: str
    """ mirai-api-http 服务器地址 """

    verify_key: str
    """ mirai-api-http 服务器验证密钥 """

    description: str = ""
    """ 机器人描述 """

    owners: list[int] = field(default_factory=list)
    """ 机器人所有者 """

    dev_groups: list[int] = field(default_factory=list)
    """ 机器人开发者群 """

    debug: bool = False
    """ 是否开启调试模式 """

    proxy: str = ""
    """
    代理地址

    示例：
        http://localhost:1080
    """

    log_rotate: int = 7
    """ 日志文件保留天数 """


@config("library.frequency_limit")
class FrequencyLimitConfig:
    """频率限制配置"""

    flush: int = 10
    """ 刷新间隔（秒） """

    user_max: int = 10
    """ 单用户最大请求权重，为 0 时不限制 """

    field_max: int = 0
    """ 单区域最大请求权重，为 0 时不限制 """

    global_max: int = 0
    """ 全局最大请求权重，为 0 时不限制 """


@config("library.function")
class FunctionConfig:
    """功能配置"""

    default: bool = False
    """ 是否默认启用所有模块 """

    allow_bot: bool = False
    """ 是否允许其他机器人调用 """

    allow_anonymous: bool = False
    """ 是否允许匿名使用 """

    prefix: list[str] = field(default_factory=lambda: [".", "/"])
    """ 命令前缀 """


@config("library.data_path")
class DataPathConfig:
    library: str = str(Path("data") / "library")
    """ 库数据目录 """

    module: str = str(Path("data") / "module")
    """ 模块数据目录 """

    shared: str = str(Path("data") / "shared")
    """ 共享数据目录 """

    temp: str = str(Path("data") / "temp")
    """ 临时文件目录 """


@config("library.path")
class PathConfig:
    """路径配置"""

    log: str = "log"
    """ 日志文件目录 """

    module: str = "module"
    """ 模块文件目录 """

    data: str = "data"
    """ 数据文件目录 """

    config: str = "config"
    """ 模块配置文件目录 """


@config("library.mysql")
class MySQLConfig:
    """MySQL 配置"""

    disable_pooling: bool = False
    """ 是否禁用连接池 """

    pool_size: int = 40
    """ 连接池大小 """

    max_overflow: int = 60
    """ 连接池最大溢出 """


@config("library.database")
class DatabaseConfig:
    """数据库配置"""

    link: str = "sqlite+aiosqlite:///data/data.db"
    """
    数据库链接，目前仅支持 SQLite 和 MySQL

    示例：
        MySQL:  mysql+aiomysql://user:password@localhost:3306/database
        SQLite: sqlite+aiosqlite:///data/data.db
    """

    @property
    def is_mysql(self) -> bool:
        return self.link.startswith("mysql+aiomysql://")


# create(EricConfig)
# create(FrequencyLimitConfig)
# create(FunctionConfig)
# create(DataPathConfig)
# create(PathConfig)
# create(MySQLConfig)
# create(DatabaseConfig)
