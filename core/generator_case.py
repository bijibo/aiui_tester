"""
**************************************
*  @Author  ：   毕纪波
*  @Time    ：   2025/8/14 10:02
*  @Project :   ai-test
*  @FileName:   generator_case.py
*  @description:测试用例生成器
                功能：
                1. 生成单个测试用例
                2. 生成多个测试用例
                3. 保存到 e2e 目录
                4. 支持自然语言转换和手动构建两种模式
**************************************
"""

import os
import re
import json
import time
from typing import List, Dict, Any, Optional, Union
from urllib.parse import urlparse
from dataclasses import dataclass

from accelerate.commands.config.update import description

from core.midscene_insight import MidsceneInsight, TaskContext, TaskSequence, Task
from core.generator_step import SingleInstructionMapper, TestScriptGenerator
from core.enums import TaskType, ActionType


@dataclass
class TestCaseConfig:
    """测试用例配置"""
    name: str  # 测试用例名称
    description: str  # 测试用例描述
    base_url: str  # 基础URL
    timeout: int = 30000  # 默认超时时间
    setup_actions: List[str] = None  # 设置操作
    teardown_actions: List[str] = None  # 清理操作

    def __post_init__(self):
        if self.setup_actions is None:
            self.setup_actions = []
        if self.teardown_actions is None:
            self.teardown_actions = []


class TestCaseGenerator:
    """测试用例生成器主类"""

    def __init__(self, output_dir: str = r"..\e2e"):
        self.insight = MidsceneInsight()
        self.mapper = SingleInstructionMapper()
        self.script_generator = TestScriptGenerator()
        self.output_dir = output_dir

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def generate_single_case_from_natural_language(self,
                                                   natural_language: str,
                                                   config: TestCaseConfig) -> Dict[str, Any]:
        """
        从自然语言生成单个测试用例
        Args:
            natural_language: 自然语言描述
            config: 测试用例配置
        Returns:
            Dict: 包含生成结果的字典
        """
        print(f"🔄 从自然语言生成测试用例: {natural_language}")

        try:
            # 创建上下文
            context = TaskContext(
                page_url=config.base_url,
                page_title=config.name,
                previous_actions=[]
            )

            # 使用AI解析自然语言
            sequence = self.insight.parse_instruction(natural_language, context)

            # 生成测试脚本
            script = self._generate_test_script(sequence, config)

            # 保存到文件
            filename = self._generate_filename(config.name)
            filepath = self._save_script(script, filename)

            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'script': script,
                'task_count': len(sequence.tasks),
                'natural_language': natural_language,
                'config': config
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'natural_language': natural_language,
                'config': config
            }

    def generate_single_case_from_steps(self,
                                        steps: List[Dict[str, Any]],
                                        config: TestCaseConfig) -> Dict[str, Any]:
        """
        从步骤列表生成单个测试用例
        Args:
            steps: 步骤列表，格式: [{'method': 'aiInput', 'args': [...], 'kwargs': {...}}]
            config: 测试用例配置
        Returns:
            Dict: 包含生成结果的字典
        """
        print(f"🔄 从步骤列表生成测试用例: {config.name}")

        try:
            # 创建上下文
            context = TaskContext(
                page_url=config.base_url,
                page_title=config.name,
                previous_actions=[]
            )

            # 从步骤创建任务序列
            sequence = self.insight.create_task_sequence_from_calls(steps, context)
            sequence.description = config.description

            # 生成测试脚本
            script = self._generate_test_script(sequence, config)

            # 保存到文件
            filename = self._generate_filename(config.name)
            filepath = self._save_script(script, filename)

            return {
                'success': True,
                'filename': filename,
                'filepath': filepath,
                'script': script,
                'task_count': len(sequence.tasks),
                'steps': steps,
                'config': config
            }

        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'steps': steps,
                'config': config
            }

    def generate_multiple_cases(self,
                                cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        生成多个测试用例
        Args:
            cases: 测试用例列表，每个元素包含 type、data、config
                  type: 'natural_language' 或 'steps'
                  data: 自然语言字符串或步骤列表
                  config: TestCaseConfig 对象
        Returns:
            Dict: 包含所有生成结果的字典
        """
        print(f"🔄 生成多个测试用例，共 {len(cases)} 个")

        results = []
        successful_count = 0
        failed_count = 0

        for i, case in enumerate(cases, 1):
            print(f"\n--- 处理第 {i}/{len(cases)} 个用例 ---")

            case_type = case.get('type')
            case_data = case.get('data')
            case_config = case.get('config')

            if case_type == 'natural_language':
                result = self.generate_single_case_from_natural_language(case_data, case_config)
            elif case_type == 'steps':
                result = self.generate_single_case_from_steps(case_data, case_config)
            else:
                result = {
                    'success': False,
                    'error': f"不支持的用例类型: {case_type}",
                    'config': case_config
                }

            results.append(result)

            if result['success']:
                successful_count += 1
                print(f"✅ 成功生成: {result['filename']}")
            else:
                failed_count += 1
                print(f"❌ 生成失败: {result['error']}")

        # 生成汇总脚本
        summary_script = self._generate_summary_script(results)
        summary_filename = f"test_suite_{int(time.time())}.spec.ts"
        summary_filepath = self._save_script(summary_script, summary_filename)

        return {
            'total_cases': len(cases),
            'successful_count': successful_count,
            'failed_count': failed_count,
            'results': results,
            'summary_script': summary_script,
            'summary_filename': summary_filename,
            'summary_filepath': summary_filepath
        }

    def _generate_test_script(self, sequence: TaskSequence, config: TestCaseConfig) -> str:
        """生成完整的测试脚本"""

        script_lines = [
            'import { expect } from "@playwright/test";',
            'import { test } from "./fixture";',
            '',
            'test.beforeEach(async ({ page }) => {',
            f'  await page.goto("{config.base_url}");',
            '  await page.waitForLoadState("networkidle");',
            '  console.log(\'OPENAI_API_KEY:\', process.env.OPENAI_API_KEY);'
        ]

        # 添加设置操作
        for action in config.setup_actions:
            script_lines.append(f'  {action}')

        script_lines.extend([
            '});',
            ''
        ])

        # 添加清理操作（如果有）
        if config.teardown_actions:
            script_lines.extend([
                'test.afterEach(async ({ page }) => {',
            ])
            for action in config.teardown_actions:
                script_lines.append(f'  {action}')
            script_lines.extend([
                '});',
                ''
            ])

        # 测试函数开始
        script_lines.extend([
            f'test("{config.name}", async ({{',
            '  ai,',
            '  aiQuery,',
            '  aiAssert,',
            '  aiInput,',
            '  aiTap,',
            '  aiScroll,',
            '  aiWaitFor,',
            '  aiHover,',
            '  aiKeyboardPress,',
            '  page',
            '}) => {',
            f'  // {config.description}',
        ])

        # 添加任务代码
        for i, task in enumerate(sequence.tasks):
            if i > 0:
                script_lines.append('')

            # 添加注释
            script_lines.append(f'  // {task.description}')

            # 生成任务代码
            if task.action_type == ActionType.NAVIGATE:
                # 导航任务使用page.goto
                script_lines.append(f'  await page.goto("{task.target}");')
                script_lines.append('  await page.waitForLoadState("networkidle");')
            else:
                # 其他任务使用生成器
                task_code = self.script_generator.task_to_code(task)
                script_lines.append(task_code)

        script_lines.append('});')

        return '\n'.join(script_lines)

    def _generate_summary_script(self, results: List[Dict[str, Any]]) -> str:
        """生成汇总测试脚本"""

        script_lines = [
            'import { expect } from "@playwright/test";',
            'import { test } from "./fixture";',
            '',
            '// 自动生成的测试套件',
            f'// 生成时间: {time.strftime("%Y-%m-%d %H:%M:%S")}',
            f'// 包含 {len([r for r in results if r["success"]])} 个测试用例',
            ''
        ]

        # 为每个成功的结果添加测试
        for i, result in enumerate(results, 1):
            if result['success']:
                config = result['config']
                script_lines.extend([
                    f'test("{config.name}", async ({{ page, ai, aiQuery, aiAssert, aiInput, aiTap, aiScroll, aiWaitFor }}) => {{',
                    f'  // {config.description}',
                    f'  await page.goto("{config.base_url}");',
                    '  await page.waitForLoadState("networkidle");',
                    '',
                    '  // TODO: 在这里添加具体的测试步骤',
                    '  // 参考对应的单独测试文件',
                    '',
                    '});',
                    ''
                ])

        return '\n'.join(script_lines)

    def _generate_filename(self, test_name: str) -> str:
        """生成文件名"""
        # 清理文件名中的特殊字符
        safe_name = re.sub(r'[^\w\u4e00-\u9fff\-]', '_', test_name)
        safe_name = re.sub(r'_+', '_', safe_name)  # 合并多个下划线
        safe_name = safe_name.strip('_')  # 去除首尾下划线

        # 添加时间戳确保唯一性
        timestamp = int(time.time())
        return f"{safe_name}_{timestamp}.spec.ts"

    def _save_script(self, script: str, filename: str) -> str:
        """保存脚本到文件"""
        filepath = os.path.join(self.output_dir, filename)

        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(script)
            return filepath
        except Exception as e:
            raise Exception(f"保存文件失败: {str(e)}")

    def list_generated_files(self) -> List[str]:
        """列出已生成的文件"""
        if not os.path.exists(self.output_dir):
            return []

        files = []
        for filename in os.listdir(self.output_dir):
            if filename.endswith('.spec.ts'):
                files.append(os.path.join(self.output_dir, filename))

        return sorted(files)

    def clean_output_directory(self) -> int:
        """清理输出目录"""
        files = self.list_generated_files()
        count = 0

        for filepath in files:
            try:
                os.remove(filepath)
                count += 1
            except Exception as e:
                print(f"删除文件失败 {filepath}: {str(e)}")

        return count


# def demo_natural_language_generation():
#     """演示自然语言生成测试用例"""
#     print("🚀 演示自然语言生成测试用例")
#     print("=" * 60)
#
#     # 初始化生成器（需要真实的API Key）
#     api_key = os.getenv('OPENAI_API_KEY', 'test-key')
#     generator = TestCaseGenerator()
#
#     # 你提供的自然语言
#     natural_language = "打开百度，搜索python，点击百度一下"
#
#     # 创建测试配置
#     config = TestCaseConfig(
#         name="百度搜索Python测试",
#         description="使用自然语言生成的百度搜索Python功能测试",
#         base_url="https://www.baidu.com",
#         setup_actions=[
#             "console.log('开始百度搜索Python测试');",
#             "console.log('OPENAI_API_KEY:', process.env.OPENAI_API_KEY);"
#         ]
#     )
#
#     print(f"📝 自然语言输入: {natural_language}")
#     print(f"🎯 测试名称: {config.name}")
#     print(f"🌐 基础URL: {config.base_url}")
#
#     try:
#         # 生成测试用例
#         print(f"\n🔄 正在生成测试用例...")
#         result = generator.generate_single_case_from_natural_language(natural_language, config)
#
#         if result['success']:
#             print(f"\n✅ 成功生成测试用例!")
#             print(f"📄 文件名: {result['filename']}")
#             print(f"📂 文件路径: {result['filepath']}")
#             print(f"🔢 任务数量: {result['task_count']}")
#             print(f"📝 原始描述: {result['natural_language']}")
#
#             # 显示生成的脚本内容
#             print(f"\n📜 生成的测试脚本:")
#             print("=" * 50)
#             print(result['script'])
#             print("=" * 50)
#
#             # 验证文件是否存在
#             if os.path.exists(result['filepath']):
#                 file_size = os.path.getsize(result['filepath'])
#                 print(f"\n📊 文件信息:")
#                 print(f"  文件大小: {file_size} bytes")
#                 print(f"  文件位置: {result['filepath']}")
#                 print(f"  可直接在 Playwright 项目中使用")
#
#         else:
#             print(f"\n❌ 生成失败: {result['error']}")
#             print(f"💡 可能的原因:")
#             print(f"  1. 需要有效的 OPENAI_API_KEY 环境变量")
#             print(f"  2. 网络连接问题")
#             print(f"  3. API 配额不足")
#
#     except Exception as e:
#         print(f"\n❌ 生成过程中出现异常: {str(e)}")
#         print(f"💡 解决建议:")
#         print(f"  1. 设置环境变量: export OPENAI_API_KEY='your-api-key'")
#         print(f"  2. 检查网络连接")
#         print(f"  3. 确认 API Key 有效性")
#
#
# def demo_steps_generation():
#     """演示步骤生成测试用例（作为对比）"""
#     print(f"\n🔧 演示步骤生成测试用例（作为对比）")
#     print("=" * 60)
#
#     generator = TestCaseGenerator()
#
#     # 手动定义相同功能的步骤
#     steps = [
#         {'method': 'aiInput', 'args': ['搜索框', 'python'], 'kwargs': {}},
#         {'method': 'aiTap', 'args': ['百度一下按钮'], 'kwargs': {}},
#         {'method': 'aiWaitFor', 'args': ['搜索结果加载完成'], 'kwargs': {'options': {'timeoutMs': 10000}}},
#         {'method': 'aiAssert', 'args': ['显示Python相关搜索结果'], 'kwargs': {}}
#     ]
#
#     config = TestCaseConfig(
#         name="百度搜索Python步骤测试",
#         description="使用预定义步骤的百度搜索Python功能测试",
#         base_url="https://www.baidu.com"
#     )
#
#     print(f"📝 预定义步骤数量: {len(steps)}")
#     print(f"🎯 测试名称: {config.name}")
#
#     result = generator.generate_single_case_from_steps(steps, config)
#
#     if result['success']:
#         print(f"\n✅ 成功生成步骤测试用例!")
#         print(f"📄 文件名: {result['filename']}")
#         print(f"🔢 任务数量: {result['task_count']}")
#     else:
#         print(f"\n❌ 生成失败: {result['error']}")
#
#
# def main():
#     """主函数 - 演示自然语言生成测试用例"""
#     print("🎯 generator_case 自然语言生成演示")
#     print("=" * 80)
#
#     # 确保输出目录存在
#     os.makedirs("e2e", exist_ok=True)
#
#     # 演示自然语言生成
#     demo_natural_language_generation()
#
#     # 演示步骤生成（作为对比）
#     demo_steps_generation()
#
#     # 显示生成的文件列表
#     print(f"\n📂 查看生成的文件:")
#     print("-" * 40)
#
#     generator = TestCaseGenerator()
#     files = generator.list_generated_files()
#
#     if files:
#         for i, filepath in enumerate(files, 1):
#             filename = os.path.basename(filepath)
#             file_size = os.path.getsize(filepath) if os.path.exists(filepath) else 0
#             print(f"  {i}. {filename} ({file_size} bytes)")
#     else:
#         print("  (暂无生成的文件)")
#
#     print(f"\n🎉 演示完成!")
#     print(f"💡 使用说明:")
#     print(f"  1. 设置环境变量: export OPENAI_API_KEY='your-api-key'")
#     print(f"  2. 生成的文件保存在 'e2e' 目录")
#     print(f"  3. 可直接在 Playwright 项目中使用")
#     print(f"  4. 自然语言: '打开百度，搜索python，点击百度一下'")
#
#
# if __name__ == "__main__":
#     main()
