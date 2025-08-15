from enum import Enum


class TaskType(Enum):
    """任务类型枚举"""
    LOCATE = "locate"  # 元素定位任务
    ACTION = "action"  # 操作执行任务
    EXTRACT = "extract"  # 数据提取任务
    ASSERT = "assert"  # 断言验证任务
    WAIT = "wait"  # 等待任务


class ActionType(Enum):
    """操作类型枚举"""
    CLICK = "click"
    INPUT = "input"
    SCROLL = "scroll"
    HOVER = "hover"
    KEYBOARD = "keyboard"
    NAVIGATE = "navigate"
