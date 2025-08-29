"""
**************************************
*  @Author  ：   bijibo
*  @Time    ：   2025/8/28 14:46
*  @Project :   ai-test
*  @FileName:   llm_manage.py
*  @description:
**************************************
"""
import time
from typing import List, Any, Optional, Callable

from openai import OpenAI

from config.config import AIUIConfig
from tools.logger_util import get_logger


class LLMManager:
    """LLM管理器"""

    def __init__(self, model_name: str = AIUIConfig.MODEL_NAME, temperature: float = 0.0):
        """
        初始化AI模型管理器
        Args:
            api_key: OpenAI API密钥
            base_url: 自定义API端点（可选，用于代理或其他兼容服务）
            model_name: 要使用的AI模型名称
            temperature:联想参数
        """
        self.client = OpenAI(
            api_key=AIUIConfig.OPENAI_API_KEY,
            base_url=AIUIConfig.OPENAI_BASE_URL
        )
        self.model_name = model_name
        self.temperature = temperature
        self.logger = get_logger(name=__name__)

    def chat(self, messages: List[Any], **kwargs) -> str:
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
                temperature=self.temperature,
                **kwargs
            )
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"AI模型调用失败: {str(e)}")
            raise Exception(f"AI模型调用失败: {str(e)}")

    def chat_with_retry(self,
                        messages: List[Any],
                        validation_func: Optional[Callable[[str], bool]] = None,
                        **kwargs) -> str | None:
        """
        带重试机制的对话方法，可根据自定义验证函数决定是否重试
        Args:
            messages: 对话消息列表，包含role和content
            validation_func: 验证返回结果是否满足要求的函数，返回True表示满足要求无需重试
                            函数签名: func(response: str) -> bool
            **kwargs: 额外的API参数（如temperature、max_tokens等）
        Returns:
            str: AI模型生成的回复内容
        Raises:
            Exception: 当达到最大重试次数或API调用失败时抛出异常
        """
        retry_times = AIUIConfig.RETRY_TIMES
        for attempt in range(retry_times + 1):
            try:
                response = self.client.chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    **kwargs
                )
                content = response.choices[0].message.content
                if validation_func is None:
                    return content
                if validation_func(content):
                    return content
                else:
                    self.logger.warning(f"AI模型第{attempt + 1}次返回不满足要求: {content}")
                    if attempt < retry_times:
                        time.sleep(AIUIConfig.RETRY_DELAY)
                        continue
                    else:
                        self.logger.warning(f"AI模型多次返回结果均不满足要求: {content}")
            except Exception as e:
                self.logger.error(f"AI模型调用失败: {str(e)}")
                raise Exception(f"AI模型调用失败: {str(e)}")
        return None


if __name__ == '__main__':
    pass
    # 示例:
    # def validate_json_response(response):
    #     """验证返回内容是否为有效的JSON格式"""
    #     try:
    #         json.loads(response)
    #         return True
    #     except json.JSONDecodeError:
    #         return False
    #
    #
    # messages = [{"role": "user", "content": "请以JSON格式返回{'name': '张三', 'age': 25}"}]
    # response = llm_manager.chat_with_retry(
    #     messages,
    #     validation_func=validate_json_response
    # )
