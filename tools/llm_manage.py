"""
**************************************
*  @Author  ：   bijibo
*  @Time    ：   2025/8/28 14:46
*  @Project :   ai-test
*  @FileName:   llm_manage.py
*  @description:
**************************************
"""
from typing import List, Any, Optional, Callable, Union
from pydantic import BaseModel
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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
        self.client = ChatOpenAI(
            model=model_name,
            temperature=temperature,
            api_key=AIUIConfig.OPENAI_API_KEY,
            base_url=AIUIConfig.OPENAI_BASE_URL
        )
        self.model_name = model_name
        self.temperature = temperature
        self.logger = get_logger(name=__name__)

    def build_messages(
            self,
            sys_template: str = "",
            sys_vars=None,
            human_template: str = "",
            human_vars=None
    ):
        if human_vars is None:
            human_vars = {}
        if sys_vars is None:
            sys_vars = {}

        return ChatPromptTemplate.from_messages([
            ("system", sys_template),
            ("human", human_template),
        ]).partial(**{**sys_vars, **human_vars})

    def chat(
            self,
            message: ChatPromptTemplate,
            dataclazz: Optional[Any] = None
    ) -> Union[str, Any]:
        """
        调用大模型进行对话，可选解析为 Pydantic 模型
        :param message: 消息链
        :param dataclazz: 可选的 Pydantic 模型类
        :return: str 或 Pydantic 对象
        """
        try:
            # 是否需要结构化解析
            if dataclazz:
                output_parser = PydanticOutputParser(pydantic_object=dataclazz)
                format_instructions = output_parser.get_format_instructions()
                chain = message | self.client | output_parser
                return chain.invoke({"format_instructions": format_instructions})
            else:
                chain = message | self.client
                return chain.invoke({}).content
        except Exception as e:
            # 出错时给一个明确提示
            return f"[Chat Error] {str(e)}"


if __name__ == '__main__':
    class Summary(BaseModel):
        title: str
        keywords: List[str]


    llm = LLMManager()
    prompt = llm.build_messages(
        sys_template="你是一个总结助手",
        human_template="请帮我总结以下文本，并输出 JSON：{text}\n{format_instructions}",
        human_vars={"text": "LangChain 是一个用于构建基于大语言模型应用的框架"}
    )
    result = llm.chat(prompt, Summary)
    print(result.keywords)