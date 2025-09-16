"""
**************************************
*  @Author  ：   bijibo
*  @Time    ：   2025/8/28 14:51
*  @Project :   ai-test
*  @FileName:   logger_util.py
*  @description:
**************************************
"""
import logging
import logging.handlers
import json
import sys
from datetime import datetime
from time import sleep
from typing import Any, Optional, Union
from pathlib import Path
from enum import Enum
from config import config


class LogLevel(Enum):
    DEBUG = logging.DEBUG
    INFO = logging.INFO
    WARNING = logging.WARNING
    ERROR = logging.ERROR


class ColoredFormatter(logging.Formatter):
    """控制台输出彩色日志格式化"""
    COLORS = {
        'DEBUG': '\033[36m',  # 青色
        'INFO': '\033[32m',  # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',  # 红色
        'CRITICAL': '\033[35m',  # 紫色
        'RESET': '\033[0m'  # 重置
    }

    def __init__(self):
        super().__init__()
        self.fmt = '%(asctime)s [%(levelname)s] %(name)s: %(message)s'
        self.formatter = logging.Formatter(self.fmt)

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录并添加颜色"""
        # 添加颜色
        level_color = self.COLORS.get(record.levelname, '')
        reset_color = self.COLORS['RESET']

        # 创建带颜色的格式
        colored_fmt = f"{level_color}{self.fmt}{reset_color}"
        formatter = logging.Formatter(colored_fmt)

        return formatter.format(record)


class AIUITestLogger:
    """日志管理器"""

    def __init__(self,
                 name: str = "ai-test",
                 ):
        self.config: config.AIUIConfig = config.AIUIConfig()
        self.logger = logging.getLogger(name)
        # 将字符串日志级别转换为对应的日志级别常量
        log_level = getattr(logging, self.config.LOG_LEVEL.upper(), logging.INFO)
        self.logger.setLevel(log_level)
        self._setup_handlers()

    def _setup_handlers(self):
        log_dir = config.BASE_DIR / "logs"
        log_dir.mkdir(exist_ok=True)

        # 添加控制台处理器
        if self.config.LOG_ENABLED == "True":
            console_handler = logging.StreamHandler(sys.stdout)
            # 将字符串日志级别转换为对应的日志级别常量
            log_level = getattr(logging, self.config.LOG_LEVEL.upper(), logging.INFO)
            console_handler.setLevel(log_level)
            console_handler.setFormatter(ColoredFormatter())
            self.logger.addHandler(console_handler)

        # 添加普通日志文件处理器
        log_file = log_dir / f"log_{datetime.now().strftime('%Y-%m-%d')}.log"
        file_handler = logging.handlers.RotatingFileHandler(
            filename=log_file,
            mode="a",
            maxBytes=1024 * 1024 * 100,  # 100M
            encoding="utf-8"
        )
        file_handler.setFormatter(logging.Formatter('%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s'))
        log_level = getattr(logging, self.config.LOG_LEVEL.upper(), logging.INFO)
        file_handler.setLevel(log_level)
        self.logger.addHandler(file_handler)

    def get_logger(self) -> logging.Logger:
        return self.logger

    def debug(self, message: str, **kwargs):
        """记录DEBUG级别日志"""
        self.logger.debug(message, extra=kwargs)

    def info(self, message: str, **kwargs):
        """记录INFO级别日志"""
        self.logger.info(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        """记录WARNING级别日志"""
        self.logger.warning(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        """记录ERROR级别日志"""
        self.logger.error(message, extra=kwargs)


class LoggerContextManager:
    """日志器上下文管理器"""

    def __init__(self, logger: AIUITestLogger, context: str, **kwargs):
        """
        Args:
            logger: 日志器实例
            context: 上下文描述
            **kwargs: 额外的上下文信息
        """
        self.logger = logger
        self.context = context
        self.context_data = kwargs
        self.start_time = None

    def __enter__(self):
        self.start_time = datetime.now()
        self.logger.info(f"开始: {self.context}",
                         event_type="context_start",
                         context=self.context,
                         **self.context_data)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()

        if exc_type:
            self.logger.error(f"异常结束: {self.context}, 耗时: {duration:.3f}s",
                              event_type="context_error",
                              context=self.context,
                              duration=duration,
                              exception_type=exc_type.__name__ if exc_type else None,
                              **self.context_data)
        else:
            self.logger.info(f"正常结束: {self.context}, 耗时: {duration:.3f}s",
                             event_type="context_end",
                             context=self.context,
                             duration=duration,
                             **self.context_data)


class ProgressBar:
    """进度条类，用于在控制台显示进度信息"""

    def __init__(self, total: int, width: int = 50, complete_char: str = '█', incomplete_char: str = '░'):
        """
        初始化进度条

        Args:
            total: 总任务数
            width: 进度条宽度（字符数）
            complete_char: 已完成部分的字符
            incomplete_char: 未完成部分的字符
        """
        self.total = total
        self.width = width
        self.complete_char = complete_char
        self.incomplete_char = incomplete_char
        self.current = 0

    def update(self, current: int = None, increment: int = 1):
        """
        更新进度条

        Args:
            current: 当前进度值，如果提供则直接设置为该值
            increment: 增量值，当current未提供时使用
        """
        if current is not None:
            self.current = current
        else:
            self.current += increment

        # 确保当前值不超过总数
        self.current = min(self.current, self.total)

    def render(self) -> str:
        """
        渲染进度条字符串

        Returns:
            str: 进度条字符串
        """
        if self.total == 0:
            percentage = 100
            completed_width = self.width
        else:
            percentage = int((self.current / self.total) * 100)
            completed_width = int((self.current / self.total) * self.width)

        remaining_width = self.width - completed_width

        bar = (self.complete_char * completed_width +
               self.incomplete_char * remaining_width)

        return f"[{bar}] {percentage:3d}% ({self.current}/{self.total})"

    def display(self, prefix: str = "", suffix: str = ""):
        """
        在控制台显示进度条

        Args:
            prefix: 进度条前缀文本
            suffix: 进度条后缀文本
        """
        progress_str = self.render()
        sys.stdout.write(f"\r{prefix}{progress_str}{suffix}")
        sys.stdout.flush()

    def finish(self, message: str = "完成"):
        """
        完成进度条显示

        Args:
            message: 完成时显示的消息
        """
        self.current = self.total
        self.display(suffix=f" {message}\n")


def get_logger(name: str = None) -> AIUITestLogger:
    """
    :param name:日志器名称
    :return:
    """
    return AIUITestLogger(name=name)


def log_context(logger: AIUITestLogger, context: str, **kwargs) -> LoggerContextManager:
    """
    创建日志上下文管理器
    :param logger: 日志器实例
    :param context: 上下文描述
    :param kwargs: 额外的上下文信息
    :return:
    """
    return LoggerContextManager(logger=logger, context=context, **kwargs)


if __name__ == '__main__':
    logger = get_logger(name=__name__)
    for i in range(10):
        sleep(2)
        logger.info(str(i))
        logger.debug(str(i))
        logger.warning(str(i))
        logger.error(str(i))
