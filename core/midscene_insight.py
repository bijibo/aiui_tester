"""
**************************************
*  @Author  ：   毕纪波
*  @Time    ：   2025/8/8 14:56
*  @Project :   ai-test
*  @FileName:   midscene_insight.py
*  @description:自然语言指令分解和任务序列生成模块
**************************************
"""

import json
import re
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from openai import OpenAI
from config.config import MidConfig, SYSTEM_PROMPTS
from core.enums import TaskType, ActionType


@dataclass
class TaskContext:
    """
    任务上下文类 - 存储任务执行时的环境信息
    """
    page_url: Optional[str] = None  # 当前页面URL
    page_title: Optional[str] = None  # 当前页面标题
    previous_actions: List[str] = None  # 之前的操作历史
    current_state: Dict[str, Any] = None  # 当前状态信息

    def __post_init__(self):
        if self.previous_actions is None:
            self.previous_actions = []
        if self.current_state is None:
            self.current_state = {}


@dataclass
class Task:
    """
    任务基类
    """
    id: str  # 任务唯一标识符
    type: TaskType  # 任务类型枚举
    description: str  # 任务描述
    target: Optional[str] = None  # 操作目标
    value: Optional[str] = None  # 操作值
    action_type: Optional[ActionType] = None  # 具体操作类型
    parameters: Dict[str, Any] = None  # 额外参数
    priority: int = 0  # 优先级
    dependencies: List[str] = None  # 依赖任务列表

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}
        if self.dependencies is None:
            self.dependencies = []

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        Returns:
            Dict[str, Any]: 包含所有任务信息的字典
        """
        result = asdict(self)
        # 处理枚举类型 - 转换为字符串值以便JSON序列化
        if self.type:
            result['type'] = self.type.value
        if self.action_type:
            result['action_type'] = self.action_type.value
        return result


@dataclass
class TaskSequence:
    """
    任务序列类 - 支持序列化和反序列化
    """
    id: str  # 序列唯一标识符
    description: str  # 序列描述
    tasks: List[Task]  # 任务列表
    context: TaskContext  # 执行上下文
    metadata: Dict[str, Any] = None  # 元数据信息

    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> Dict[str, Any]:
        """
        转换为字典格式
        Returns:
            Dict[str, Any]: 包含完整序列信息的字典
        """
        return {
            'id': self.id,
            'description': self.description,
            'tasks': [task.to_dict() for task in self.tasks],  # 转换所有任务
            'context': asdict(self.context),  # 转换上下文
            'metadata': self.metadata  # 元数据
        }


class AIModelManager:
    """
    AI模型管理器
    """

    def __init__(self):
        """
        初始化AI模型管理器
        Args:
            api_key: OpenAI API密钥
            base_url: 自定义API端点（可选，用于代理或其他兼容服务）
            model_name: 要使用的AI模型名称
        """
        self.client = OpenAI(
            api_key=MidConfig.OPENAI_API_KEY,
            base_url=MidConfig.OPENAI_BASE_URL
        )
        self.model_name = MidConfig.MODEL_NAME

    def chat_completion(self, messages: List[Any], **kwargs) -> str:
        """
        对话方法
        Args:
            messages: 对话消息列表，包含role和content
            **kwargs: 额外的API参数（如temperature、max_tokens等）
        Returns:
            str: AI模型生成的回复内容
        Raises:
            Exception: 当API调用失败时抛出异常
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"AI模型调用失败: {str(e)}")


class InstructionParser:
    """
    解析自然语言指令并转换为结构化任务
    Attributes:
        ai_manager: AI模型管理器实例
        action_patterns: 操作类型的正则表达式模式字典
    """

    def __init__(self, ai_manager: AIModelManager):
        self.ai_manager = ai_manager
        # 定义操作类型的识别模式
        self.action_patterns = {
            ActionType.INPUT: [r'输入|填写|填入|键入', r'input|type|fill'],
            ActionType.CLICK: [r'点击|单击|按|选择', r'click|tap|press|select'],
            ActionType.SCROLL: [r'滚动|翻页|下拉|上拉', r'scroll|swipe'],
            ActionType.HOVER: [r'悬停|鼠标悬停|移动到', r'hover|mouseover'],
            ActionType.KEYBOARD: [r'按键|快捷键|键盘', r'keyboard|key|shortcut'],
            ActionType.NAVIGATE: [r'导航|跳转|访问|打开', r'navigate|goto|visit|open']
        }

        # 添加特殊任务类型的识别模式
        self.task_type_patterns = {
            TaskType.WAIT: [
                r'等待.*?加载', r'等待.*?完成', r'等待.*?出现', r'等待.*?消失',
                r'等.*?加载', r'等.*?完成', r'等.*?出现', r'等.*?消失',
                r'wait.*?load', r'wait.*?complete', r'wait.*?appear', r'wait.*?disappear'
            ],
            TaskType.ASSERT: [
                r'验证|校验|检查|确认|断言', r'确保|保证',
                r'verify|validate|check|assert|ensure'
            ],
            TaskType.EXTRACT: [
                r'获取|提取|读取|查看|抓取', r'提取.*?信息', r'获取.*?数据',
                r'extract|get|fetch|retrieve|obtain'
            ]
        }

    def extract_action_type(self, instruction: str) -> Optional[ActionType]:
        """
        从指令中提取操作类型(包括ACTION类型和其他任务类型)
        Args:
            instruction: 自然语言指令
        Returns:
            Optional[ActionType]: 识别到的操作类型，如果无法识别则返回None
        """
        instruction_lower = instruction.lower()

        # 检查ACTION类型的操作模式
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                if re.search(pattern, instruction_lower):
                    return action_type

        # 如果没有匹配到ACTION类型，检查其他任务类型
        for task_type, patterns in self.task_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, instruction_lower):
                    # 非ACTION类型，返回一个特殊标识
                    return task_type.value

        return None

    def extract_task_type(self, instruction: str) -> Optional[TaskType]:
        """
        从指令中提取任务类型
        Args:
            instruction: 自然语言指令
        Returns:
            Optional[TaskType]: 识别到的任务类型
        """
        instruction_lower = instruction.lower()

        # 检查ACTION类型
        for action_type, patterns in self.action_patterns.items():
            for pattern in patterns:
                if re.search(pattern, instruction_lower):
                    return TaskType.ACTION

        # 检查其他任务类型
        for task_type, patterns in self.task_type_patterns.items():
            for pattern in patterns:
                if re.search(pattern, instruction_lower):
                    return task_type

        return None

    def parse_compound_instruction(self, instruction: str, context: TaskContext) -> List[Dict[str, Any]]:
        """
        解析复合指令 - 使用AI模型将复杂的自然语言指令分解为任务列表
        Args:
            instruction: 复合自然语言指令
            context: 任务执行上下文，提供页面信息和历史操作
        Returns:
            List[Dict[str, Any]]: 解析后的任务数据列表
        Raises:
            Exception: 当AI解析失败或返回格式无效时抛出异常
        """
        system_prompt = SYSTEM_PROMPTS
        user_prompt = f"""
                        请分解以下指令："{instruction}"
                        
                        上下文信息：
                        - 页面URL: {context.page_url or '未知'}
                        - 页面标题: {context.page_title or '未知'}
                        - 之前的操作: {', '.join(context.previous_actions) if context.previous_actions else '无'}
                        
                        请返回JSON格式的任务列表。
                        """
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ]

        try:
            response = self.ai_manager.chat_completion(messages, temperature=0.0)  # 降低大模型的欺诈率

            # 尝试从响应中提取JSON数组
            json_match = re.search(r'\[.*\]', response, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
            else:
                # 如果没有找到JSON数组，尝试解析整个响应
                return json.loads(response)
        except json.JSONDecodeError as e:
            raise Exception(f"AI返回的JSON格式无效: {str(e)}")
        except Exception as e:
            raise Exception(f"指令解析失败: {str(e)}")


class TaskGenerator:
    """
    将AI解析的任务数据转换为结构化的Task对象
    管理任务ID的生成和任务对象的创建过程
    """

    def __init__(self, parser: InstructionParser):
        self.parser = parser
        self.task_counter = 0  # 任务ID计数器

    def generate_task_id(self) -> str:
        """
        生成唯一的任务ID
        Returns:
            str: 格式为 "task_XXXX" 的任务ID
        """
        self.task_counter += 1
        return f"task_{self.task_counter:04d}"

    def create_task_from_dict(self, task_data: Dict[str, Any]) -> Task:
        """
        从字典数据创建任务对象
        将AI解析返回的字典数据转换为结构化的Task对象
        处理类型转换和默认值设置，包括错误的类型映射修正
        Args:
            task_data: 包含任务信息的字典
        Returns:
            Task: 创建的任务对象
        """
        task_id = self.generate_task_id()

        # 获取原始类型值
        raw_type = task_data.get('type', 'action')
        raw_action_type = task_data.get('action_type')

        # 修正类型映射 - 处理AI可能返回的错误类型
        task_type, action_type = self._normalize_task_types(raw_type, raw_action_type)

        # 创建Task对象
        return Task(
            id=task_id,
            type=task_type,
            description=task_data.get('description', ''),
            target=task_data.get('target'),
            value=task_data.get('value'),
            action_type=action_type,
            parameters=task_data.get('parameters', {}),
            priority=task_data.get('priority', 0),
            dependencies=task_data.get('dependencies', [])
        )

    def _normalize_task_types(self, raw_type: str, raw_action_type: str = None) -> tuple:
        """
        处理AI模型可能返回的不正确的类型映射，将其修正为正确的枚举值

        Args:
            raw_type: 原始任务类型字符串
            raw_action_type: 原始操作类型字符串

        Returns:
            tuple: (TaskType, ActionType) 修正后的类型元组
        """
        # ActionType的所有有效值
        valid_action_types = {e.value for e in ActionType}

        # 如果raw_type实际上是一个ActionType，需要修正
        if raw_type in valid_action_types:
            # 这种情况下，任务类型应该是ACTION，操作类型是raw_type
            task_type = TaskType.ACTION
            action_type = ActionType(raw_type)
        else:
            # 正常情况，解析任务类型
            try:
                task_type = TaskType(raw_type)
            except ValueError:
                # 如果无法识别，默认为ACTION
                task_type = TaskType.ACTION

            # 解析操作类型
            action_type = None
            if raw_action_type:
                try:
                    action_type = ActionType(raw_action_type)
                except ValueError:
                    # 如果操作类型无效，设为None
                    action_type = None

        return task_type, action_type

    def generate_tasks(self, instruction: str, context: TaskContext) -> List[Task]:
        """
        结合指令解析器和任务创建功能，将自然语言转换为任务对象列表
        Args:
            instruction: 自然语言指令
            context: 任务执行上下文
        Returns:
            List[Task]: 生成的任务对象列表
        """
        # 使用解析器解析指令，获取任务数据列表
        task_data_list = self.parser.parse_compound_instruction(instruction, context)
        # 将每个任务数据转换为Task对象
        tasks = []
        for task_data in task_data_list:
            task = self.create_task_from_dict(task_data)
            tasks.append(task)

        return tasks


class SingleInstructionMapper:
    """
    提供与@midscene框架兼容的API方法，将单一的AI指令直接转换为Task对象
    Attributes:
        task_counter: 任务ID计数器
    """

    def __init__(self):
        self.task_counter = 0  # 任务ID计数器

    def generate_task_id(self) -> str:
        """
        生成唯一的任务ID
        Returns:
            str: 格式为 "task_XXXX" 的任务ID
        """
        self.task_counter += 1
        return f"task_{self.task_counter:04d}"

    def ai_input(self, target: str, value: str, **kwargs) -> Task:
        """
        Args:
            target: 输入目标元素（如"搜索框"、"用户名输入框"）
            value: 要输入的值
            **kwargs: 额外的参数配置
        Returns:
            Task: 输入操作任务对象
        """
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=f"在{target}中输入{value}",
            target=target,
            value=value,
            action_type=ActionType.INPUT,
            parameters=kwargs
        )

    def ai_tap(self, target: str, **kwargs) -> Task:
        """
        Args:
            target: 点击目标元素（如"登录按钮"、"搜索按钮"）
            **kwargs: 额外的参数配置
        Returns:
            Task: 点击操作任务对象
        """
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=f"点击{target}",
            target=target,
            action_type=ActionType.CLICK,
            parameters=kwargs
        )

    def ai_scroll(self, options: Dict[str, Any], target: Optional[str] = None, **kwargs) -> Task:
        """
        Args:
            options: 滚动选项配置（direction: 方向, scrollType: 滚动类型）
            target: 滚动目标区域（可选）
            **kwargs: 额外的参数配置
        Returns:
            Task: 滚动操作任务对象
        """
        direction = options.get('direction', 'down')
        scroll_type = options.get('scrollType', 'once')

        # 构建描述信息
        description = f"向{direction}滚动"
        if target:
            description += f"到{target}"
        if scroll_type != 'once':
            description += f"({scroll_type})"

        # 合并参数
        parameters = {**options, **kwargs}

        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=description,
            target=target,
            action_type=ActionType.SCROLL,
            parameters=parameters
        )

    def ai_assert(self, assertion: str, **kwargs) -> Task:
        """
        Args:
            assertion: 要验证的断言条件
            **kwargs: 额外的参数配置（如timeout等）

        Returns:
            Task: 断言验证任务对象
        """
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ASSERT,
            description=f"验证{assertion}",
            target=assertion,
            parameters=kwargs
        )

    def ai_query(self, query: str, return_type: Optional[str] = None, **kwargs) -> Task:
        """
        Args:
            query: 数据查询描述
            return_type: 返回数据的类型注解
            **kwargs: 额外的参数配置
        Returns:
            Task: 数据提取任务对象
        """
        parameters = kwargs.copy()
        if return_type:
            parameters['return_type'] = return_type

        return Task(
            id=self.generate_task_id(),
            type=TaskType.EXTRACT,
            description=f"提取数据: {query}",
            target=query,
            parameters=parameters
        )

    def ai_wait_for(self, condition: str, options: Optional[Dict[str, Any]] = None, **kwargs) -> Task:
        """
        映射 aiWaitFor 指令 - 创建等待条件任务

        Args:
            condition: 等待条件描述
            options: 等待选项配置（如timeoutMs等）
            **kwargs: 额外的参数配置

        Returns:
            Task: 等待条件任务对象
        """
        parameters = kwargs.copy()
        if options:
            parameters.update(options)

        return Task(
            id=self.generate_task_id(),
            type=TaskType.WAIT,
            description=f"等待{condition}",
            target=condition,
            parameters=parameters
        )

    def ai_hover(self, target: str, **kwargs) -> Task:
        """
        映射 aiHover 指令 - 创建鼠标悬停任务

        Args:
            target: 悬停目标元素
            **kwargs: 额外的参数配置

        Returns:
            Task: 鼠标悬停任务对象
        """
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=f"鼠标悬停在{target}",
            target=target,
            action_type=ActionType.HOVER,
            parameters=kwargs
        )

    def ai_keyboard_press(self, keys: str, target: Optional[str] = None, **kwargs) -> Task:
        """
        映射 aiKeyboardPress 指令 - 创建键盘操作任务

        Args:
            keys: 要按下的键或组合键（如"Enter"、"Ctrl+C"）
            target: 键盘操作的目标元素（可选）
            **kwargs: 额外的参数配置

        Returns:
            Task: 键盘操作任务对象
        """
        description = f"按键{keys}"
        if target:
            description += f"在{target}"

        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=description,
            target=target,
            value=keys,
            action_type=ActionType.KEYBOARD,
            parameters=kwargs
        )

    def page_goto(self, url: str, **kwargs) -> Task:
        """
        映射 page.goto 指令 - 创建页面导航任务

        Args:
            url: 要导航到的URL地址
            **kwargs: 额外的参数配置

        Returns:
            Task: 页面导航任务对象
        """
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=f"导航到{url}",
            target=url,
            action_type=ActionType.NAVIGATE,
            parameters=kwargs
        )


class MidsceneInsight:
    """
    Midscene Insight 主类,集成了所有功能模块：
        - AI模型管理和调用
        - 自然语言指令解析
        - 任务生成和序列管理
        - 单一指令映射
        - 任务验证和优化
    提供统一的API接口，支持两种使用模式：
        1. 自然语言解析模式：使用AI解析复杂指令
        2. 单一指令映射模式：直接映射@midscene兼容的API调用
    Attributes:
        ai_manager: AI模型管理器
        parser: 指令解析器
        task_generator: 任务生成器
        single_mapper: 单一指令映射器
        sequence_counter: 序列ID计数器
    """

    def __init__(self):
        """
        初始化 MidsceneInsight 实例
        """
        # 初始化各个组件
        self.ai_manager = AIModelManager()
        self.parser = InstructionParser(self.ai_manager)
        self.task_generator = TaskGenerator(self.parser)
        self.single_mapper = SingleInstructionMapper()
        self.sequence_counter = 0  # 序列ID计数器

    def generate_sequence_id(self) -> str:
        """
        生成唯一的序列ID
        Returns:
            str: 格式为 "sequence_XXXX" 的序列ID
        """
        self.sequence_counter += 1
        return f"sequence_{self.sequence_counter:04d}"

    def parse_instruction(self, instruction: str, context: Optional[TaskContext] = None) -> TaskSequence:
        """
        使用AI模型将复杂的自然语言指令分解为结构化的任务序列
        Args:
            instruction: 自然语言指令（如"打开百度，搜索Python，点击第一个结果"）
            context: 任务执行上下文，提供页面信息和历史操作
        Returns:
            TaskSequence: 包含所有解析任务的序列对象
        Example:
            >>> insight = MidsceneInsight(api_key="your-key")
            >>> context = TaskContext(page_url="https://www.baidu.com")
            >>> sequence = insight.parse_instruction("输入Python，点击搜索", context)
            >>> print(f"生成了 {len(sequence.tasks)} 个任务")
        """
        if context is None:
            context = TaskContext()

        # 使用任务生成器解析指令并生成任务列表
        tasks = self.task_generator.generate_tasks(instruction, context)

        # 创建任务序列对象
        sequence = TaskSequence(
            id=self.generate_sequence_id(),
            description=instruction,
            tasks=tasks,
            context=context,
            metadata={
                'created_at': None,  # 可以添加时间戳
                'model_name': self.ai_manager.model_name,
                'task_count': len(tasks),
                'source': 'ai_parsing'  # 标记数据来源
            }
        )

        return sequence

    def create_single_task(self, method: str, *args, **kwargs) -> Task:
        """
        创建单一任务 - 直接映射@midscene兼容的API调用
        Args:
            method: 方法名（支持的方法见method_map）
            *args: 位置参数，具体参数取决于方法类型
            **kwargs: 关键字参数，用于额外配置
        Returns:
            Task: 创建的任务对象
        Raises:
            ValueError: 当方法名不支持时抛出异常
        Example:
            >>> insight = MidsceneInsight(api_key="your-key")
            >>> task = insight.create_single_task('aiInput', '搜索框', 'Python')
            >>> print(task.description)  # "在搜索框中输入Python"
        """
        # 方法映射表 - 将字符串方法名映射到具体的映射器方法
        method_map = {
            'aiInput': self.single_mapper.ai_input,
            'aiTap': self.single_mapper.ai_tap,
            'aiScroll': self.single_mapper.ai_scroll,
            'aiAssert': self.single_mapper.ai_assert,
            'aiQuery': self.single_mapper.ai_query,
            'aiWaitFor': self.single_mapper.ai_wait_for,
            'aiHover': self.single_mapper.ai_hover,
            'aiKeyboardPress': self.single_mapper.ai_keyboard_press,
            'pageGoto': self.single_mapper.page_goto,
        }

        # 检查方法是否支持
        if method not in method_map:
            supported_methods = ', '.join(method_map.keys())
            raise ValueError(f"不支持的方法: {method}。支持的方法: {supported_methods}")

        # 调用对应的映射器方法
        return method_map[method](*args, **kwargs)

    def create_task_sequence_from_calls(self, calls: List[Dict[str, Any]],
                                        context: Optional[TaskContext] = None) -> TaskSequence:
        """
        从方法调用列表创建任务序列 - 批量创建任务的便捷方法，每个调用都会转换为对应的Task对象
        Args:
            calls: 方法调用列表，每个元素包含method、args、kwargs
            context: 任务执行上下文
        Returns:
            TaskSequence: 包含所有任务的序列对象
        Example:
            >>> calls = [
            ...     {'method': 'aiInput', 'args': ['搜索框', 'Python'], 'kwargs': {}},
            ...     {'method': 'aiTap', 'args': ['搜索按钮'], 'kwargs': {}},
            ...     {'method': 'aiWaitFor', 'args': ['搜索结果加载'], 'kwargs': {'options': {'timeoutMs': 5000}}}
            ... ]
            >>> sequence = insight.create_task_sequence_from_calls(calls)
            >>> print(f"创建了包含 {len(sequence.tasks)} 个任务的序列")
        """
        if context is None:
            context = TaskContext()

        tasks = []
        # 遍历所有方法调用，创建对应的任务对象
        for call in calls:
            method = call.get('method')
            args = call.get('args', [])
            kwargs = call.get('kwargs', {})

            # 使用单一任务创建方法
            task = self.create_single_task(method, *args, **kwargs)
            tasks.append(task)

        # 创建任务序列对象
        sequence = TaskSequence(
            id=self.generate_sequence_id(),
            description=f"包含{len(tasks)}个任务的序列",
            tasks=tasks,
            context=context,
            metadata={
                'created_at': None,
                'task_count': len(tasks),
                'source': 'single_calls'  # 标记数据来源
            }
        )

        return sequence

    def optimize_task_sequence(self, sequence: TaskSequence) -> TaskSequence:
        """
        优化任务序列 - 对任务序列进行优化处理
        Args:
            sequence: 要优化的任务序列
        Returns:
            TaskSequence: 优化后的任务序列
        Note:
            可以添加的优化逻辑包括：
            1. 合并相似任务（如连续的输入操作）
            2. 调整任务顺序（优化执行效率）
            3. 添加依赖关系（确保执行顺序）
            4. 优化等待时间（根据操作类型调整超时）
            5. 添加错误恢复任务
        """
        # TODO: 实现具体的优化逻辑
        return sequence

    def validate_task_sequence(self, sequence: TaskSequence) -> bool:
        """
        验证任务序列的有效性 - 检查任务序列是否符合执行要求，对任务序列进行完整性和有效性检查，确保所有任务都有必要的信息
        Args:
            sequence: 要验证的任务序列
        Returns:
            bool: 验证结果，True表示有效，False表示无效

        """
        # 检查基本任务有效性
        for task in sequence.tasks:
            # 检查任务描述
            if not task.description:
                return False
            # 检查ACTION任务是否有target
            if task.type == TaskType.ACTION and not task.target:
                return False

        # TODO: 可以添加更多验证规则
        # - 检查任务ID唯一性
        # - 验证依赖关系的有效性
        # - 检查参数格式的正确性

        return True
