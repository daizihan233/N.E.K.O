# -*- coding: utf-8 -*-
"""
Loguru 日志配置模块
适用于 N.E.K.O. 项目，提供统一的日志配置
"""

import os
import sys
from pathlib import Path
from datetime import datetime
import time
from loguru import logger

from config import APP_NAME


def setup_logging(app_name=None, service_name=None, log_level="INFO"):
    """
    设置 loguru 日志配置

    Args:
        app_name: 应用名称，用于创建日志目录，默认使用配置中的 APP_NAME
        service_name: 服务名称，用于区分不同服务的日志文件（如Main、Memory、Agent）
        log_level: 日志级别，默认 "INFO"
        
    Returns:
        tuple: (logger实例, 配置信息)
    """
    app_name = app_name or APP_NAME
    service_name = service_name or "unknown"
    
    # 获取日志目录
    log_dir = _get_log_directory(app_name)
    
    # 确保日志目录存在
    log_dir.mkdir(parents=True, exist_ok=True)
    
    # 日志文件名配置
    if service_name != "unknown":
        log_filename = f"{app_name}_{service_name}_{datetime.now().strftime('%Y%m%d')}.log"
        error_filename = f"{app_name}_{service_name}_error_{datetime.now().strftime('%Y%m%d')}.log"
    else:
        log_filename = f"{app_name}_{datetime.now().strftime('%Y%m%d')}.log"
        error_filename = f"{app_name}_error_{datetime.now().strftime('%Y%m%d')}.log"
    
    log_file = log_dir / log_filename
    error_file = log_dir / error_filename

    # 移除默认的控制台处理器
    logger.remove()

    # 添加控制台日志处理器（彩色输出）
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level=log_level,
        colorize=True
    )

    # 添加常规日志文件处理器
    logger.add(
        log_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
        level=log_level,
        rotation="10 MB",  # 当日志文件达到10MB时轮转
        retention="30 days",  # 保留30天的日志
        compression="zip"  # 压缩旧日志
    )

    # 添加错误日志文件处理器（只记录错误及以上级别）
    logger.add(
        error_file,
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} | {file}:{line} - {message}",
        level="ERROR",
        rotation="5 MB",  # 错误日志较小轮转值
        retention="90 days",  # 错误日志保留更长时间
        compression="zip"
    )

    # 记录日志配置信息
    service_info = f"{service_name}" if service_name != "unknown" else app_name
    logger.info(f"=== {service_info} 日志系统已初始化 ===")
    logger.info(f"日志目录: {log_dir}")
    logger.info(f"日志级别: {log_level}")
    logger.info("=" * 50)

    return logger, {"log_dir": log_dir, "log_file": log_file, "error_file": error_file}


def _get_log_directory(app_name):
    """
    获取合适的日志目录
    优先级：
    1. 用户文档目录/{APP_NAME}/logs（我的文档，默认首选）
    2. 应用程序所在目录/logs
    3. 用户数据目录（AppData等）
    4. 用户主目录
    5. 临时目录（最后的降级选项）
    """
    # 尝试1: 使用用户文档目录（我的文档，默认首选！）
    try:
        docs_dir = _get_documents_directory()
        log_dir = docs_dir / app_name / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)  # 尝试创建目录
        return log_dir
    except Exception as e:
        print(f"Warning: Failed to use Documents directory: {e}", file=sys.stderr)

    # 尝试2: 使用应用程序所在目录
    try:
        # 对于exe打包的应用，使用exe所在目录
        if getattr(sys, 'frozen', False):
            # 如果是打包后的exe
            app_dir = Path(sys.executable).parent
        else:
            # 如果是脚本运行，使用项目根目录
            app_dir = Path.cwd()
        log_dir = app_dir / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception as e:
        print(f"Warning: Failed to use application directory: {e}", file=sys.stderr)

    # 尝试3: 使用系统用户数据目录
    try:
        if sys.platform == "win32":
            # Windows: %APPDATA%\AppName\logs
            base_dir = os.getenv('APPDATA')
            if base_dir:
                log_dir = Path(base_dir) / app_name / "logs"
                log_dir.mkdir(parents=True, exist_ok=True)
                return log_dir
        elif sys.platform == "darwin":
            # macOS: ~/Library/Application Support/AppName/logs
            base_dir = Path.home() / "Library" / "Application Support"
            log_dir = base_dir / app_name / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir
        else:
            # Linux: ~/.local/share/AppName/logs
            xdg_data_home = os.getenv('XDG_DATA_HOME')
            if xdg_data_home:
                log_dir = Path(xdg_data_home) / app_name / "logs"
            else:
                log_dir = Path.home() / ".local" / "share" / app_name / "logs"
            log_dir.mkdir(parents=True, exist_ok=True)
            return log_dir
    except Exception as e:
        print(f"Warning: Failed to get system data directory: {e}", file=sys.stderr)

    # 尝试4: 使用用户主目录
    try:
        log_dir = Path.home() / f".{app_name}" / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception as e:
        print(f"Warning: Failed to use home directory: {e}", file=sys.stderr)

    # 尝试5: 使用临时目录（最后的降级选项）
    try:
        import tempfile
        log_dir = Path(tempfile.gettempdir()) / app_name / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        return log_dir
    except Exception as e:
        print(f"Warning: Failed to use temp directory: {e}", file=sys.stderr)

    # 如果所有方法都失败，返回当前目录
    print(f"Warning: All log directory attempts failed, using current directory", file=sys.stderr)
    log_dir = Path.cwd() / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir


def _get_documents_directory():
    """获取系统的用户文档目录（使用系统API）"""
    if sys.platform == "win32":
        # Windows: 使用系统API获取真正的"我的文档"路径
        try:
            import ctypes
            from ctypes import windll, wintypes

            # 使用SHGetFolderPath获取我的文档路径
            CSIDL_PERSONAL = 5  # My Documents
            SHGFP_TYPE_CURRENT = 0

            buf = ctypes.create_unicode_buffer(wintypes.MAX_PATH)
            windll.shell32.SHGetFolderPathW(None, CSIDL_PERSONAL, None, SHGFP_TYPE_CURRENT, buf)
            docs_dir = Path(buf.value)

            if docs_dir.exists():
                return docs_dir
        except Exception as e:
            print(f"Warning: Failed to get Documents path via API: {e}", file=sys.stderr)

        # 降级：尝试从注册表读取
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders"
            )
            docs_dir = Path(winreg.QueryValueEx(key, "Personal")[0])
            winreg.CloseKey(key)

            # 展开环境变量
            docs_dir = Path(os.path.expandvars(str(docs_dir)))
            if docs_dir.exists():
                return docs_dir
        except Exception as e:
            print(f"Warning: Failed to get Documents path from registry: {e}", file=sys.stderr)

        # 最后的降级
        docs_dir = Path.home() / "Documents"
        if not docs_dir.exists():
            docs_dir = Path.home() / "文档"
        return docs_dir

    elif sys.platform == "darwin":
        # macOS
        return Path.home() / "Documents"
    else:
        # Linux: 尝试使用XDG
        xdg_docs = os.getenv('XDG_DOCUMENTS_DIR')
        if xdg_docs:
            return Path(xdg_docs)
        return Path.home() / "Documents"


class ThrottledLogger:
    """
    带速率限制的日志记录器包装器

    用于业务逻辑中需要速率限制日志的场景

    使用示例:
        throttled = ThrottledLogger(logger, interval=15.0)
        throttled.info("mcp_check", "MCP availability check result: ready")  # 每15秒只记录一次
    """

    def __init__(self, logger, interval: float = 15.0):
        """
        初始化速率限制日志记录器

        Args:
            logger: 原始 logger 实例
            interval: 速率限制间隔（秒）
        """
        self._logger = logger
        self._interval = interval
        self._last_log_times = {}

    def _should_log(self, key: str) -> bool:
        """检查是否应该记录日志"""
        current_time = time.time()
        last_time = self._last_log_times.get(key, 0)
        if current_time - last_time >= self._interval:
            self._last_log_times[key] = current_time
            return True
        return False

    def _format_message(self, msg: str) -> str:
        """格式化消息，添加速率限制提示"""
        return f"{msg} (此日志每{int(self._interval)}秒显示一次)"

    def debug(self, key: str, msg: str, *args, **kwargs):
        """速率限制的 debug 日志"""
        if self._should_log(key):
            self._logger.debug(self._format_message(msg), *args, **kwargs)

    def info(self, key: str, msg: str, *args, **kwargs):
        """速率限制的 info 日志"""
        if self._should_log(key):
            self._logger.info(self._format_message(msg), *args, **kwargs)

    def warning(self, key: str, msg: str, *args, **kwargs):
        """速率限制的 warning 日志（始终记录）"""
        self._logger.warning(msg, *args, **kwargs)

    def error(self, key: str, msg: str, *args, **kwargs):
        """速率限制的 error 日志（始终记录）"""
        self._logger.error(msg, *args, **kwargs)

    def reset(self, key: str = None):
        """重置计时器"""
        if key:
            self._last_log_times.pop(key, None)
        else:
            self._last_log_times.clear()


# 导出主要接口
__all__ = ['setup_logging', 'ThrottledLogger']