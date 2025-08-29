"""
配置文件 - Midscene Insight Python 实现
"""

import os
from pathlib import Path
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()
# 根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class AIUIConfig:
    """配置类"""

    # AI模型配置
    OPENAI_API_KEY: str = os.getenv('API_KEY', '')
    OPENAI_BASE_URL: Optional[str] = os.getenv('BASE_URL', '')
    MODEL_NAME: str = os.getenv('MODEL_NAME', '')
    RETRY_TIMES: int = 3  # 最大重试次数
    RETRY_DELAY: float = 1.0  # 重试间隔时间(秒)

    # 调试配置
    LOG_ENABLED: bool = os.getenv('LOG_ENABLED', 'False')
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')

    @classmethod
    def validate(cls) -> bool:
        if not cls.OPENAI_API_KEY:
            print("错误: 未设置 API_KEY")
            return False

        if cls.MAX_TASKS_PER_SEQUENCE <= 0:
            print("错误: MAX_TASKS_PER_SEQUENCE 必须大于 0")
            return False

        return True


