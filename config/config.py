"""
配置文件 - Midscene Insight Python 实现
"""

import os
from typing import Optional
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class MidConfig:
    """配置类"""
    
    # AI模型配置
    OPENAI_API_KEY: str = os.getenv('API_KEY', '')
    OPENAI_BASE_URL: Optional[str] = os.getenv('BASE_URL','')
    MODEL_NAME: str = os.getenv('MODEL_NAME', '')
    
    # 任务配置
    MAX_TASKS_PER_SEQUENCE: int = int(os.getenv('MAX_TASKS_PER_SEQUENCE', '20'))
    DEFAULT_TIMEOUT: int = int(os.getenv('DEFAULT_TIMEOUT', '60'))
    
    # 调试配置
    DEBUG: bool = os.getenv('DEBUG', 'False').lower() == 'true'
    LOG_LEVEL: str = os.getenv('LOG_LEVEL', 'INFO')
    
    @classmethod
    def validate(cls) -> bool:
        """验证配置是否有效"""
        if not cls.OPENAI_API_KEY:
            print("错误: 未设置 API_KEY")
            return False
        
        if cls.MAX_TASKS_PER_SEQUENCE <= 0:
            print("错误: MAX_TASKS_PER_SEQUENCE 必须大于 0")
            return False

        return True


# 预定义的提示词模板
SYSTEM_PROMPTS = """
你是一个UI自动化测试指令解析专家。你需要将用户的自然语言指令分解为具体的操作步骤。

任务类型说明（只能使用以下5种类型）：
- locate: 元素定位（找到页面元素）
- action: 操作执行（点击、输入、滚动、导航等所有操作）
- extract: 数据提取（获取页面信息）
- assert: 断言验证（验证页面状态）
- wait: 等待（等待页面加载或状态变化）

操作类型说明（仅用于action任务的action_type字段）：
- click: 点击操作
- input: 输入操作
- scroll: 滚动操作
- hover: 悬停操作
- keyboard: 键盘操作
- navigate: 导航操作（打开页面、跳转等）

重要规则：
1. 所有具体操作（包括导航）都使用 "action" 作为type
2. 导航操作使用 "action" + "navigate" 的组合
3. 不要使用 "navigate" 作为任务类型，只能作为操作类型

请将用户指令分解为JSON格式的任务列表，每个任务包含：
- type: 任务类型（必须是上述5种之一）
- description: 任务描述
- target: 目标元素或URL（如果适用）
- value: 输入值（如果适用）
- action_type: 操作类型（如果是action任务）
- parameters: 额外参数

示例输入："打开百度，输入邓紫棋，点击百度一下，校验是否有下一页"
示例输出：
[
  {
    "type": "action",
    "description": "打开百度首页",
    "target": "https://www.baidu.com",
    "action_type": "navigate"
  },
  {
    "type": "action",
    "description": "在搜索框中输入邓紫棋",
    "target": "搜索框",
    "value": "邓紫棋",
    "action_type": "input"
  },
  {
    "type": "action",
    "description": "点击百度一下按钮",
    "target": "百度一下按钮",
    "action_type": "click"
  },
  {
    "type": "assert",
    "description": "校验页面是否有下一页",
    "target": "下一页链接或按钮"
  }
]
"""

# 常用的元素选择器模式
ELEMENT_PATTERNS = {
    'button': ['按钮', 'button', '提交', '确认', '取消', '登录', '注册'],
    'input': ['输入框', 'input', '文本框', '搜索框', '用户名', '密码'],
    'link': ['链接', 'link', '超链接', '跳转'],
    'image': ['图片', 'image', '图像', '头像'],
    'dropdown': ['下拉框', 'select', '选择框', '下拉菜单'],
    'checkbox': ['复选框', 'checkbox', '勾选框'],
    'radio': ['单选框', 'radio', '选项'],
    'table': ['表格', 'table', '列表'],
    'form': ['表单', 'form', '填写']
}

# 常用操作的参数模板
ACTION_TEMPLATES = {
    'click': {
        'required': ['target'],
        'optional': ['wait_after', 'double_click', 'right_click']
    },
    'input': {
        'required': ['target', 'value'],
        'optional': ['clear_first', 'wait_after', 'press_enter']
    },
    'scroll': {
        'required': ['direction'],
        'optional': ['distance', 'target', 'wait_after']
    },
    'hover': {
        'required': ['target'],
        'optional': ['wait_after', 'duration']
    },
    'keyboard': {
        'required': ['keys'],
        'optional': ['target', 'wait_after']
    },
    'navigate': {
        'required': ['url'],
        'optional': ['wait_for_load', 'timeout']
    }
}
