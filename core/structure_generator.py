"""
**************************************
*  @Author  ：   bijibo
*  @Time    ：   2025/8/29 19:06
*  @Project :   ai-test
*  @FileName:   structure_generator.py
*  @description:通过大模型将自然语言转换成标准结构
**************************************
"""
from typing import List, Any

from tools.llm_manage import LLMManager


class StructureGenerator:
    def __init__(self):
        self.llm = LLMManager()

    def decompose_instruction(self, instruction: str) -> List[Any]:
        """
        将自然语言指令分解为基本操作步骤
        Args:
            instruction: 自然语言指令
        Returns:
            List[Dict]: 操作步骤列表
        """
        prompt = f"""
        你是一个UI自动化测试专家。请将以下用户指令分解为基本的操作步骤。

        要求：
        1. 每个步骤应该对应一个具体的Midscene API调用
        2. 步骤应该按照执行顺序排列
        3. 每个步骤包含操作类型和操作描述

        支持的操作类型：
        - navigate: 页面导航
        - click: 点击操作
        - input: 输入操作
        - scroll: 滚动操作
        - hover: 悬停操作
        - keyboard: 键盘操作
        - assert: 断言操作
        - extract: 数据提取
        - wait: 等待操作

        用户指令：{instruction}

        请以JSON数组格式返回，每个元素包含：
        - action_type: 操作类型
        - description: 操作描述
        - target: 目标元素（如果适用）
        - value: 输入值（如果适用）
        """

        messages = [
            {"role": "system", "content": "你是一个UI自动化测试专家。"},
            {"role": "user", "content": prompt}
        ]

        try:
            response = self.llm.chat(messages)
            print(response)
            # 解析返回的JSON
            # steps = response
            # return steps if isinstance(steps, list) else []
        except Exception as e:
            raise Exception(f"分解指令失败: {str(e)}")


if __name__ == '__main__':
    StructureGenerator().decompose_instruction("打开百度首页，输入“Python”，点击搜索按钮，等待搜索结果加载完成，获取搜索结果列表，并打印出来")
