"""
**************************************
*  @Author  ：   bijibo
*  @Time    ：   2025/8/29 19:06
*  @Project :   ai-test
*  @FileName:   structure_generator.py
*  @description:通过大模型将自然语言转换成标准结构
**************************************
"""
from dataclasses import dataclass, asdict
import re
from typing import List, Any

from langchain.chains.question_answering.map_reduce_prompt import messages

from config import prompts
from tools.llm_manage import LLMManager
from tools.logger_util import get_logger

"""
如果使用图片作为提示词:
await agent.aiHover(
  {
    image: 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...' // 省略的 base64 字符串
  }
);
#
await agent.aiTap(locate='页面顶部的登录按钮',options= { "deepThink": true ,"xpath":"XXXXX","cacheable":true}); #点击某个元素,用自然语言描述的元素定位，或使用图片作为提示词
await agent.aiHover(locate='页面顶部的登录按钮',options= { "deepThink": true ,"xpath":"XXXXX","cacheable":true});#鼠标悬停某个元素上, 用自然语言描述的元素定位，或使用图片作为提示词
await agent.aiInput(text='Hello World', locate='搜索框',options= { "deepThink": true ,"xpath":"XXXXX","cacheable":true,autoDismissKeyboard:true(如果为 true，则键盘会在输入文本后自动关闭，仅在 Android 中有效。默认值为 true)});#在某个元素中输入文本,用自然语言描述的元素定位，或使用图片作为提示词
await agent.aiKeyboardPress('Enter', '搜索框',options= { "deepThink": true ,"xpath":"XXXXX","cacheable":true}); #按下键盘上的某个键,用自然语言描述的元素定位，，或使用图片作为提示词
await agent.aiScroll(
  scrollParam={ direction: 'up', distance: 100, scrollType: 'once' }, # direction: 'up' | 'down' | 'left' | 'right' - 滚动方向 ;distance: number - 滚动距离，单位为像素;scrollType: 'once' | 'untilBottom' | 'untilTop' | 'untilRight' | 'untilLeft' - 滚动类型
  locate='表单区域',
  ,options= { "deepThink": true ,"xpath":"XXXXX","cacheable":true});
);
const dataA = await agent.aiQuery(dataDemand={
  time: '左上角展示的日期和时间，string',
  userInfo: '用户信息，{name: string}',
  tableFields: '表格的字段名，string[]',
  tableDataRecord: '表格中的数据记录，{id: string, [fieldName]: string}[]',
},
options={
"domIncluded"= boolean | 'visible-only', #是否向模型发送精简后的 DOM 信息，一般用于提取 UI 中不可见的属性，比如图片的链接。如果设置为 'visible-only'，则只发送可见的元素。默认值为 false。
"screenshotIncluded"=true #是否向模型发送截图。默认值为 true
}
);
await agent.aiAssert(assertion='"Sauce Labs Onesie" 的价格是 7.99',
                     errorMsg="价格校验失败" #当断言失败时附加的可选错误提示信息。
                     options={
                        domIncluded= 
                        screenshotIncluded=true
                     }
                     );

"""


@dataclass
class Task:


class StructureGenerator:
    def __init__(self):
        self.llm = LLMManager()
        self.logger = get_logger(name=__name__)

    def parse_language(self, natural_language: str) -> str:
        """
        将自然语言转化为指令集
        :param natural_language:
        :return:
        """
        system_prompt = prompts.PARSE_LANGUAGE_PROMPT
        user_prompt = f"请分解以下指令：{natural_language}"

        messages = self.llm.set_prompt(system_prompt, user_prompt)
        self.logger.info(f"将自然语言转化为指令集: <{natural_language}> ")

        def validation_func(content: str) -> bool:
            if len(content) < 2:
                return False
            return content[0] == '[' and content[-1] == ']'

        order_str = self.llm.chat_with_retry(
            messages=messages,
            re_info=("repl", r'.*?</think>'),
            validation_func=validation_func,
        )

        self.logger.info(f"转化成功：{order_str}")
        return order_str

    def set_task_type(self, order_str: str):
        system_prompt = prompts.PARSE_LANGUAGE_PROMPT
        user_prompt = f"请分解以下指令：{natural_language}"
        messages = self.llm.set_prompt(system_prompt, user_prompt)


if __name__ == '__main__':
    structure_generator = StructureGenerator()
    structure_generator.parse_language("打开百度首页，输入“python”关键字，点击搜索按钮，查看搜索结果。")
