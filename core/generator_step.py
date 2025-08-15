"""
**************************************
*  @Author  ：   毕纪波
*  @Time    ：   2025/8/9 10:02
*  @Project :   ai-test
*  @FileName:   generator_step.py
*  @description:单一指令映射和测试脚本生成功能
**************************************
"""

import json
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional

from core.enums import TaskType, ActionType


@dataclass
class Task:
    """任务对象"""
    id: str
    type: TaskType
    description: str
    target: Optional[str] = None
    value: Optional[str] = None
    action_type: Optional[ActionType] = None
    parameters: Dict[str, Any] = None

    def __post_init__(self):
        if self.parameters is None:
            self.parameters = {}

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        result = asdict(self)
        if self.type:
            result['type'] = self.type.value
        if self.action_type:
            result['action_type'] = self.action_type.value
        return result


class SingleInstructionMapper:
    """单一指令映射器"""
    def __init__(self):
        self.task_counter = 0

    def generate_task_id(self) -> str:
        """生成任务ID"""
        self.task_counter += 1
        return f"task_{self.task_counter:04d}"

    def ai_input(self, target: str, value: str, **kwargs) -> Task:
        """映射 aiInput 指令"""
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
        """映射 aiTap 指令"""
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=f"点击{target}",
            target=target,
            action_type=ActionType.CLICK,
            parameters=kwargs
        )

    def ai_scroll(self, options: Dict[str, Any], target: Optional[str] = None, **kwargs) -> Task:
        """映射 aiScroll 指令"""
        direction = options.get('direction', 'down')
        scroll_type = options.get('scrollType', 'once')

        description = f"向{direction}滚动"
        if target:
            description += f"到{target}"
        if scroll_type != 'once':
            description += f"({scroll_type})"

        parameters = {**options, **kwargs}

        return Task(
            id=self.generate_task_id(),
            type=TaskType.ACTION,
            description=description,
            target=target,
            action_type=ActionType.SCROLL,
            parameters=parameters
        )

    def ai_query(self, query: str, return_type: Optional[str] = None, **kwargs) -> Task:
        """映射 aiQuery 指令"""
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

    def ai_assert(self, assertion: str, **kwargs) -> Task:
        """映射 aiAssert 指令"""
        return Task(
            id=self.generate_task_id(),
            type=TaskType.ASSERT,
            description=f"验证{assertion}",
            target=assertion,
            parameters=kwargs
        )

    def ai_wait_for(self, condition: str, options: Optional[Dict[str, Any]] = None, **kwargs) -> Task:
        """映射 aiWaitFor 指令"""
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


class TestScriptGenerator:
    """测试脚本生成器"""
    def task_to_code(self, task: Task) -> str:
        """将任务转换为代码"""
        if task.type == TaskType.ACTION:
            return self._action_task_to_code(task)
        elif task.type == TaskType.EXTRACT:
            return self._extract_task_to_code(task)
        elif task.type == TaskType.ASSERT:
            return self._assert_task_to_code(task)
        elif task.type == TaskType.WAIT:
            return self._wait_task_to_code(task)
        else:
            return f"  // TODO: 处理任务类型 {task.type.value}: {task.description}"

    @staticmethod
    def _action_task_to_code(task: Task) -> str:
        """将操作任务转换为代码"""
        if task.action_type == ActionType.INPUT:
            return f"  await aiInput('{task.value}','{task.target}');"
        elif task.action_type == ActionType.CLICK:
            return f"  await aiTap('{task.target}');"
        elif task.action_type == ActionType.SCROLL:
            options = task.parameters.copy()
            if 'direction' in options and 'scrollType' in options:
                options_str = json.dumps({
                    'direction': options['direction'],
                    'scrollType': options['scrollType']
                })
                if task.target:
                    return f"  await aiScroll({options_str}, '{task.target}');"
                else:
                    return f"  await aiScroll({options_str});"
            else:
                return f"  await aiScroll({{ direction: 'down', scrollType: 'once' }});"
        else:
            return f"  // TODO: 处理操作类型 {task.action_type.value}: {task.description}"

    def _extract_task_to_code(self, task: Task) -> str:
        """将提取任务转换为代码"""
        return_type = task.parameters.get('return_type', 'any')
        var_name = self._generate_variable_name(task.description)

        code_lines = [
            f"  const {var_name} = await aiQuery<{return_type}>(",
            f"    '{task.target}'",
            "  );",
            f"  console.log('{task.description}:', {var_name});"
        ]

        return "\n".join(code_lines)

    @staticmethod
    def _assert_task_to_code(task: Task) -> str:
        """将断言任务转换为代码"""
        timeout_ms = task.parameters.get('timeoutMs', 10000)

        if 'timeoutMs' in task.parameters:
            return f"  await aiAssert('{task.target}', {{ timeoutMs: {timeout_ms} }});"
        else:
            return f"  await aiAssert('{task.target}');"

    @staticmethod
    def _wait_task_to_code(task: Task) -> str:
        """将等待任务转换为代码"""
        timeout_ms = task.parameters.get('timeoutMs', 10000)
        return f"  await aiWaitFor('{task.target}', {{ timeoutMs: {timeout_ms} }});"

    @staticmethod
    def _generate_variable_name(description: str) -> str:
        """从描述生成变量名"""
        if "商品" in description or "产品" in description:
            return "items"
        elif "用户" in description or "账户" in description:
            return "userInfo"
        elif "数据" in description:
            return "data"
        else:
            return "extractedData"
